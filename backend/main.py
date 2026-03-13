import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
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


class WorkerUpdateRequest(BaseModel):
    worker_id: int
    name: str
    bio: str


def _to_vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"


def _worker_embedding_text(name: str, bio: str) -> str:
    return f"{name.strip()}\n{bio.strip()}"


def _sync_worker_embedding(model, worker_id: int, name: str, bio: str) -> None:
    if model is None:
        logger.warning("Skipping embedding sync for worker=%s: model unavailable", worker_id)
        return

    text = _worker_embedding_text(name, bio)
    embedding = model.encode(text).tolist()
    emb_literal = _to_vector_literal(embedding)

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workers
                    SET skills_embedding = %s::vector
                    WHERE id = %s
                    """,
                    (emb_literal, worker_id),
                )
        logger.info("Embedding synced for worker=%s", worker_id)
    finally:
        conn.close()


@app.post("/tasks/match")
def match_task(req: MatchRequest, request: Request):
    """Embed incoming task description and return top available workers."""
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=500, detail="Embedding model not available.")

    task_vec = model.encode(req.description).tolist()

    emb_literal = _to_vector_literal(task_vec)

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


@app.get("/workers")
def list_workers():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, COALESCE(bio, ''), status
                FROM workers
                ORDER BY id ASC
                """
            )
            rows = cur.fetchall()

        return [
            {"id": r[0], "name": r[1], "bio": r[2], "status": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


@app.post("/workers/update")
def update_worker(req: WorkerUpdateRequest, bg: BackgroundTasks, request: Request):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE workers
                    SET name = %s, bio = %s
                    WHERE id = %s
                    RETURNING id
                    """,
                    (req.name.strip(), req.bio.strip(), req.worker_id),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Worker not found.")

        bg.add_task(
            _sync_worker_embedding,
            request.app.state.model,
            req.worker_id,
            req.name,
            req.bio,
        )

        return {
            "status": "syncing",
            "message": "Worker profile updated. Embedding recomputation started.",
            "worker_id": req.worker_id,
        }
    finally:
        conn.close()


@app.get("/workers/query")
def query_workers(q: str, request: Request, limit: int = 5, available_only: bool = True):
    model = request.app.state.model
    if model is None:
        raise HTTPException(status_code=500, detail="Embedding model not available.")

    clean_query = q.strip()
    if not clean_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    safe_limit = max(1, min(limit, 20))
    query_vec = model.encode(clean_query).tolist()
    emb_literal = _to_vector_literal(query_vec)

    conn = get_conn()
    try:
        availability_filter = "WHERE status = 'available'" if available_only else ""
        sql = f"""
            SELECT id,
                   name,
                   COALESCE(bio, ''),
                   status,
                   (1 - (skills_embedding <=> %s::vector)) AS score
            FROM workers
            {availability_filter}
            ORDER BY skills_embedding <=> %s::vector
            LIMIT %s
        """

        with conn.cursor() as cur:
            cur.execute(sql, (emb_literal, emb_literal, safe_limit))
            rows = cur.fetchall()

        payload = []
        for worker_id, name, bio, status, score in rows:
            normalized = 0.0 if score is None else max(0.0, min(float(score), 1.0))
            payload.append(
                {
                    "id": worker_id,
                    "name": name,
                    "bio": bio,
                    "status": status,
                    "score": round(normalized, 4),
                    "score_percent": round(normalized * 100, 2),
                }
            )

        return payload
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
