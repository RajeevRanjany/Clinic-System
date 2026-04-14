import logging
import re
import sqlite3
import time
import hashlib
from collections import defaultdict, OrderedDict
from contextlib import asynccontextmanager
from typing import Any

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("nl2sql")

DB_PATH = "clinic.db"
MAX_QUESTION_LEN = 500
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW = 60
CACHE_SIZE = 100

BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|EXECUTE|xp_|sp_|GRANT|REVOKE|SHUTDOWN)\b",
    re.IGNORECASE,
)
SYSTEM_TABLES = re.compile(r"\bsqlite_master\b|\bsqlite_temp_master\b", re.IGNORECASE)


def validate_sql(sql: str) -> tuple[bool, str]:
    stripped = sql.strip().lstrip(";").strip()

    if not stripped.upper().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."

    if BLOCKED_KEYWORDS.search(stripped):
        match = BLOCKED_KEYWORDS.search(stripped)
        return False, f"Blocked keyword detected: '{match.group()}'"

    if SYSTEM_TABLES.search(stripped):
        return False, "Access to system tables is not allowed."

    return True, ""


class LRUCache:
    def __init__(self, capacity: int):
        self._cache: OrderedDict = OrderedDict()
        self._capacity = capacity

    def get(self, key: str):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Any):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self._capacity:
            self._cache.popitem(last=False)


query_cache = LRUCache(CACHE_SIZE)


def cache_key(question: str) -> str:
    return hashlib.md5(question.strip().lower().encode()).hexdigest()


_rate_store: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    timestamps = [t for t in _rate_store[ip] if t > window_start]
    _rate_store[ip] = timestamps
    if len(timestamps) >= RATE_LIMIT_REQUESTS:
        return True
    _rate_store[ip].append(now)
    return False


def run_sql_direct(sql: str) -> tuple[list[str], list[list]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(sql)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        rows = [list(row) for row in cur.fetchall()]
        return columns, rows
    finally:
        conn.close()


def db_connected() -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False


def count_memory_items() -> int:
    try:
        from vanna_setup import get_agent
        agent = get_agent()
        mem = agent.agent_memory
        if hasattr(mem, "_items"):
            return len(mem._items)
        return -1
    except Exception:
        return -1


def maybe_generate_chart(columns: list[str], rows: list[list]) -> tuple[dict | None, str | None]:
    if len(columns) != 2 or not rows:
        return None, None

    try:
        df = pd.DataFrame(rows, columns=columns)
        numeric_col = columns[1]
        label_col = columns[0]

        if not pd.api.types.is_numeric_dtype(df[numeric_col]):
            df[numeric_col] = pd.to_numeric(df[numeric_col], errors="coerce")
            df = df.dropna(subset=[numeric_col])

        if df.empty:
            return None, None

        fig = px.bar(df, x=label_col, y=numeric_col, title=f"{numeric_col} by {label_col}")
        return fig.to_dict(), "bar"
    except Exception as e:
        log.warning(f"Chart generation failed: {e}")
        return None, None


async def nl_to_sql(question: str) -> str:
    return await _direct_sql_from_llm(question)


async def _direct_sql_from_llm(question: str) -> str:
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    schema = _get_schema_context()
    prompt = f"""You are a SQL expert. Given the following SQLite database schema:

{schema}

Generate ONLY a valid SQLite SELECT query for this question. Return ONLY the SQL query, nothing else, no explanation, no markdown.

Question: {question}
SQL:"""

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    sql = response.choices[0].message.content.strip()
    # Clean any accidental markdown
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).replace("```", "").strip()
    return sql


def _get_schema_context() -> str:
    return """
patients(id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
doctors(id, name, specialization, department, phone)
appointments(id, patient_id, doctor_id, appointment_date, status, notes)
treatments(id, appointment_id, treatment_name, cost, duration_minutes)
invoices(id, patient_id, invoice_date, total_amount, paid_amount, status)
"""


def _extract_sql(text: str) -> str:
    # Remove markdown code blocks
    text = re.sub(r"```(?:sql)?", "", text, flags=re.IGNORECASE).replace("```", "").strip()

    # Try to find a clean SELECT statement — stop at newline or semicolon to avoid grabbing garbage
    # First try single-line SELECT
    match = re.search(r"(SELECT\b[^\n]+)", text, re.IGNORECASE)
    if match:
        sql = match.group(1).strip().rstrip(";").strip()
        # Make sure it doesn't contain obvious non-SQL garbage
        if len(sql) < 1000 and "\n" not in sql:
            return sql

    # Fallback: multi-line SELECT up to semicolon or double newline
    match = re.search(r"(SELECT\b.*?)(?:;|\n\n|$)", text, re.IGNORECASE | re.DOTALL)
    if match:
        sql = match.group(1).strip().rstrip(";").strip()
        if len(sql) < 1000:
            return sql

    return ""


class ChatRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) > MAX_QUESTION_LEN:
            raise ValueError(f"Question too long (max {MAX_QUESTION_LEN} chars).")
        return v


class ChatResponse(BaseModel):
    message: str
    sql_query: str | None = None
    columns: list[str] = []
    rows: list[list] = []
    row_count: int = 0
    chart: dict | None = None
    chart_type: str | None = None
    cached: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting NL2SQL clinic API...")
    try:
        from vanna_setup import get_agent
        get_agent()
        log.info("Vanna agent initialized.")
    except Exception as e:
        log.error(f"Agent init failed: {e}")
    yield
    log.info("Shutting down.")


app = FastAPI(
    title="Clinic NL2SQL API",
    description="Natural Language to SQL for clinic management data.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest):
    client_ip = request.client.host if request.client else "unknown"
    log.info(f"[/chat] ip={client_ip} question={body.question!r}")

    if is_rate_limited(client_ip):
        log.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    ck = cache_key(body.question)
    cached = query_cache.get(ck)
    if cached:
        log.info(f"Cache hit for question: {body.question!r}")
        cached["cached"] = True
        return ChatResponse(**cached)

    try:
        sql = await nl_to_sql(body.question)
        log.info(f"Generated SQL: {sql}")
    except Exception as e:
        log.error(f"SQL generation error: {e}")
        return ChatResponse(message=f"Sorry, I couldn't generate a SQL query: {e}")

    valid, err = validate_sql(sql)
    if not valid:
        log.warning(f"SQL validation failed: {err} | SQL: {sql}")
        return ChatResponse(
            message=f"The generated query was rejected for safety reasons: {err}",
            sql_query=sql,
        )

    try:
        columns, rows = run_sql_direct(sql)
    except Exception as e:
        log.error(f"Query execution error: {e}")
        return ChatResponse(
            message=f"Database error while executing the query: {e}",
            sql_query=sql,
        )

    if not rows:
        result = ChatResponse(
            message="No data found for your query.",
            sql_query=sql,
            columns=columns,
            rows=[],
            row_count=0,
        )
        query_cache.set(ck, result.model_dump())
        return result

    chart, chart_type = maybe_generate_chart(columns, rows)

    result = ChatResponse(
        message=f"Found {len(rows)} result(s).",
        sql_query=sql,
        columns=columns,
        rows=rows,
        row_count=len(rows),
        chart=chart,
        chart_type=chart_type,
        cached=False,
    )

    query_cache.set(ck, result.model_dump())
    log.info(f"[/chat] returned {len(rows)} rows, chart={chart_type}")
    return result


@app.get("/health")
def health():
    connected = db_connected()
    mem_items = count_memory_items()
    return {
        "status": "ok",
        "database": "connected" if connected else "disconnected",
        "agent_memory_items": mem_items,
    }
