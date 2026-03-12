# backend/main.py
from fastapi import FastAPI
from pgvector.psycopg import register_vector
import psycopg

app = FastAPI()
model = SentenceTransformer('BAAI/bge-small-en-v1.5')

@app.post("/tasks/match")
async def match_task(description: str):
    # 1. Embed incoming task locally (Free!)
    task_vec = model.encode(description).tolist()
    
    # 2. Hybrid Search: Available Workers + Semantic Match
    with get_conn() as conn:
        results = conn.execute("""
            SELECT id, name, bio 
            FROM workers 
            WHERE status = 'available' 
            ORDER BY skills_embedding <=> %s 
            LIMIT 3
        """, (task_vec,)).fetchall()
        
    return [{"id": r[0], "name": r[1], "bio": r[2]} for r in results]

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