import os
from dotenv import load_dotenv

from vanna import Agent, AgentConfig
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.integrations.openai import OpenAILlmService

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "clinic.db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")

_agent: Agent | None = None


class DefaultUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        email = request_context.get_cookie("vanna_email") or "admin@clinic.local"
        return User(
            id=email,
            username=email,
            email=email,
            group_memberships=["admin", "user"],
        )


def build_agent() -> Agent:
    llm = OpenAILlmService(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    db_tool = RunSqlTool(
        sql_runner=SqliteRunner(database_path=DB_PATH)
    )

    agent_memory = DemoAgentMemory(max_items=1000)

    tools = ToolRegistry()
    tools.register_local_tool(db_tool, access_groups=["admin", "user"])
    tools.register_local_tool(VisualizeDataTool(), access_groups=["admin", "user"])
    tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=["admin"])
    tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=["admin", "user"])

    user_resolver = DefaultUserResolver()

    agent = Agent(
        llm_service=llm,
        tool_registry=tools,
        user_resolver=user_resolver,
        agent_memory=agent_memory,
        config=AgentConfig(),
    )

    return agent


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent
