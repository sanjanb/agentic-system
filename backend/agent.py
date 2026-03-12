# backend/agent.py
from pydantic_ai import Agent, RunContext
from database import get_conn

dispatch_agent = Agent(
    'openai:gpt-4o-mini',
    system_prompt="Assign the best available worker based on skills and proximity."
)

@dispatch_agent.tool
async def search_available_workers(ctx: RunContext[None], task_embedding: list[float]):
    """Finds top 3 workers who are currently 'available'."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, name, skills FROM workers "
            "WHERE status = 'available' "
            "ORDER BY skills_embedding <=> %s LIMIT 3",
            (task_embedding,)
        ).fetchall()