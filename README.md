# Clinic NL2SQL — AI-Powered Natural Language to SQL

An AI agent that answers natural language questions about a clinic management database using **Vanna 2.0** + **Groq (LLaMA 3)** + **FastAPI**.

## LLM Provider

**Groq** — free tier, OpenAI-compatible API, no local setup needed.  
Model: `llama3-70b-8192`  
Sign up: https://console.groq.com

## Architecture

```
User question
     │
     ▼
FastAPI /chat
     │
     ├─ Input validation (length, empty check)
     ├─ Rate limiting (20 req/min per IP)
     ├─ LRU cache check (100 entries)
     │
     ▼
Vanna 2.0 Agent
  ├─ LLM Service (Groq / llama3-70b)
  ├─ DemoAgentMemory (15 seeded Q&A pairs)
  └─ ToolRegistry
       ├─ RunSqlTool (SqliteRunner → clinic.db)
       ├─ VisualizeDataTool (Plotly charts)
       ├─ SaveQuestionToolArgsTool
       └─ SearchSavedCorrectToolUsesTool
     │
     ▼
SQL Validation (SELECT-only, no dangerous keywords)
     │
     ▼
SQLite execution → results + optional Plotly chart
```

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd nl2sql
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Create the database

```bash
python setup_database.py
# Output: clinic.db + summary line
```

### 4. Seed agent memory

```bash
python seed_memory.py
# Seeds 15 Q&A pairs into DemoAgentMemory
```

### 5. Start the API server

```bash
uvicorn main:app --port 8000 --reload
```

Visit http://localhost:8000/docs for the interactive Swagger UI.

## API Reference

### POST /chat

Ask a natural language question about the clinic data.

**Request:**
```json
{ "question": "Show me the top 5 patients by total spending" }
```

**Response:**
```json
{
  "message": "Found 5 result(s).",
  "sql_query": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [["Aarav", "Sharma", 4500.0], ["Priya", "Verma", 3200.0]],
  "row_count": 5,
  "chart": { "data": [...], "layout": {...} },
  "chart_type": "bar",
  "cached": false
}
```

### GET /health

```json
{ "status": "ok", "database": "connected", "agent_memory_items": 15 }
```

## Example curl commands

```bash
# Health check
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many patients do we have?"}'

# Revenue by doctor
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Show revenue by doctor"}'
```

## Bonus Features

- **Chart generation** — 2-column results automatically get a Plotly bar chart
- **Input validation** — empty/too-long questions rejected with clear errors
- **Query caching** — LRU cache (100 entries) avoids redundant LLM calls
- **Rate limiting** — 20 requests/minute per IP (sliding window)
- **Structured logging** — all steps logged with timestamps and levels
- **SQL validation** — SELECT-only, blocks dangerous keywords and system tables
