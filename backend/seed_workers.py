import asyncio
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

# 1. Initialize Local Embedding Model (Runs on your hardware, $0 cost)
# bge-small-en-v1.5 is the current "gold standard" for small/fast retrieval
model = SentenceTransformer('BAAI/bge-small-en-v1.5')

DB_URL = "postgresql://dev_user:dev_password@localhost:5432/task_db"

workers_data = [
    {"name": "Alice Chen", "skills": "Expert in AWS VPC, Terraform, and Cloud Security"},
    {"name": "Bob Smith", "skills": "Professional Chef specializing in Italian and French cuisine"},
    {"name": "Carlos Gomez", "skills": "Landscaping, garden design, and irrigation systems"},
    {"name": "Diana Prince", "skills": "Full-stack developer, React, Svelte, and FastAPI expert"}
]

async def seed():
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    
    print("🌱 Generating Local Embeddings (Zero Cost)...")
    
    for worker in workers_data:
        # Generate embedding locally
        embedding = model.encode(worker["skills"]).tolist()
        
        conn.execute(
            "INSERT INTO workers (name, bio, skills_embedding, status) VALUES (%s, %s, %s, %s)",
            (worker["name"], worker["skills"], embedding, "available")
        )
        print(f"✅ Indexed: {worker['name']}")

    print("🚀 Seeding Complete. Data is now searchable locally.")

if __name__ == "__main__":
    asyncio.run(seed())