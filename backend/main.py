from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from database import get_conn

app = FastAPI()


class MatchRequest(BaseModel):
    description: str


class AssignmentRequest(BaseModel):
    task_id: int
    worker_id: int


@app.post("/tasks/match")
def match_task(req: MatchRequest):
    """Embed incoming task and return top available workers (hybrid search).

    This assumes a local SentenceTransformer model is available for embeddings.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        raise HTTPException(status_code=500, detail="SentenceTransformer not available")

    # Model is loaded once per request — for production, cache this at module level
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
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
