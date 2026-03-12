import sys
import os
from pathlib import Path

# Ensure backend package dir is on sys.path so `import app` works when cwd is project root
BASE_DIR = str(Path(__file__).parent.resolve())
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic import BaseModel
from database import get_conn
import psycopg
from pgvector.psycopg import register_vector

app = FastAPI()


class AssignmentRequest(BaseModel):
    task_id: int
    worker_id: int


class MatchRequest(BaseModel):
    description: str


@app.post("/tasks/match")
def match_task(req: MatchRequest):
    """Embed incoming task and return top available workers (hybrid search).

    This assumes a local SentenceTransformer model is available for embeddings.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        raise HTTPException(status_code=500, detail="SentenceTransformer not available")

    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    task_vec = model.encode(req.description).tolist()

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, bio
            FROM workers
            WHERE status = 'available'
            ORDER BY skills_embedding <=> %s
            LIMIT 3
            """,
            (task_vec,),
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
                    SET assigned_worker_id = %s, status = 'assigned'
                    WHERE id = %s AND status = 'open'
                    RETURNING id
                    """,
                    (req.worker_id, req.task_id),
                )
                task_updated = cur.fetchone()

                if not task_updated:
                    raise HTTPException(status_code=409, detail="Task already taken or closed.")

                cur.execute(
                    """
                    UPDATE workers
                    SET status = 'busy'
                    WHERE id = %s AND status = 'available'
                    RETURNING id
                    """,
                    (req.worker_id,),
                )
                worker_updated = cur.fetchone()

                if not worker_updated:
                    raise HTTPException(status_code=409, detail="Worker is no longer available.")

        return {"status": "success", "message": f"Task {req.task_id} assigned to Worker {req.worker_id}"}

    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
