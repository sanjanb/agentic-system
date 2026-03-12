# backend/main.py
from fastapi import FastAPI
from pgvector.psycopg import register_vector
import psycopg

app = FastAPI()

@app.post("/search-users")
async def search_users(embedding: list[float]):
    # Local PG connection
    conn = psycopg.connect("postgresql://localhost/task_db", autocommit=True)
    register_vector(conn)
    
    # Semantic search directly in local hardware
    results = conn.execute(
        "SELECT id, name, bio FROM users ORDER BY profile_embedding <=> %s LIMIT 3",
        (embedding,)
    ).fetchall()
    
    return [{"id": r[0], "name": r[1], "bio": r[2]} for r in results]