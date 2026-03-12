import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Startup lifespan — model is loaded ONCE and reused across all requests
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading embedding model (BAAI/bge-small-en-v1.5)…")
    try:
        from sentence_transformers import SentenceTransformer
        app.state.model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        logger.info("Embedding model ready.")
    except Exception as exc:
        logger.error("Failed to load embedding model: %s", exc)
        app.state.model = None
    yield
    logger.info("Shutting down.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class MatchRequest(BaseModel):
    description: str


class AssignmentRequest(BaseModel):
    task_id: int
    worker_id: int


class DispatchRequest(BaseModel):
    description: str
    worker_id: int


@app.post("/tasks/match")
def match_task(req: MatchRequest, request: Request):
    """Embed incoming task description and return top available workers."""
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=500, detail="Embedding model not available.")

    task_vec = model.encode(req.description).tolist()

    from psycopg.types.json import Jsonb
    emb_literal = '[' + ','.join(str(x) for x in task_vec) + ']'

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, bio
            FROM workers
            WHERE status = 'available'
            ORDER BY skills_embedding <=> %s::vector
            LIMIT 3
            """,
            (emb_literal,),
        )
        rows = cur.fetchall()

    conn.close()
    return [{"id": r[0], "name": r[1], "bio": r[2]} for r in rows]


@app.post("/search-users")
def search_users(embedding: list[float]):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, name, bio FROM users ORDER BY profile_embedding <=> %s LIMIT 3",
            (embedding,),
        )
        rows = cur.fetchall()

    conn.close()
    return [{"id": r[0], "name": r[1], "bio": r[2]} for r in rows]


@app.post("/tasks/claim")
def claim_task(req: AssignmentRequest):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE tasks
                    SET worker_id = %s, status = 'assigned'
                    WHERE id = %s AND status = 'open'
                    RETURNING id
                    """,
                    (req.worker_id, req.task_id),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=409, detail="Task already taken or closed.")

                cur.execute(
                    """
                    UPDATE workers SET status = 'busy'
                    WHERE id = %s AND status = 'available'
                    RETURNING id
                    """,
                    (req.worker_id,),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=409, detail="Worker is no longer available.")

        return {"status": "success", "message": f"Task {req.task_id} assigned to Worker {req.worker_id}"}
    finally:
        conn.close()


@app.post("/tasks/dispatch")
def dispatch_task(req: DispatchRequest):
    """Create a new task from a description and atomically assign a worker in one transaction."""
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Create the task
                cur.execute(
                    "INSERT INTO tasks (description, status) VALUES (%s, 'open') RETURNING id",
                    (req.description,),
                )
                task_id = cur.fetchone()[0]

                # 2. Atomically assign the worker
                cur.execute(
                    """
                    UPDATE tasks SET worker_id = %s, status = 'assigned'
                    WHERE id = %s AND status = 'open'
                    RETURNING id
                    """,
                    (req.worker_id, task_id),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=409, detail="Failed to claim task.")

                # 3. Mark the worker as busy
                cur.execute(
                    """
                    UPDATE workers SET status = 'busy'
                    WHERE id = %s AND status = 'available'
                    RETURNING id
                    """,
                    (req.worker_id,),
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=409, detail="Worker is no longer available.")

        logger.info("Dispatched: task=%s worker=%s", task_id, req.worker_id)
        return {"status": "success", "task_id": task_id, "worker_id": req.worker_id}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
