import asyncio
import psycopg
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer
import os

# 1. Initialize Local Embedding Model 
# 'all-MiniLM-L6-v2' is extremely fast and light on RAM
# 'bge-small-en-v1.5' is slightly better for professional skill matching
model = SentenceTransformer('BAAI/bge-small-en-v1.5')

DB_URL = "postgresql://dev_user:dev_password@localhost:5432/task_db"

workers_data = [
    {"name": "Alice Chen", "skills": "Expert in AWS VPC, Terraform, and Cloud Security"},
    {"name": "Bob Smith", "skills": "Professional Chef specializing in Italian and French cuisine"},
    {"name": "Carlos Gomez", "skills": "Landscaping, garden design, and irrigation systems"},
    {"name": "Diana Prince", "skills": "Full-stack developer, React, Svelte, and FastAPI expert"},
    {"name": "Elena Rossi", "skills": "Deep cleaning, organizing, and residential maintenance"},
    {"name": "Frank Wright", "skills": "Architecture photography and drone videography"},
    {"name": "Grace Lee", "skills": "Bilingual translator (English/Mandarin) for legal documents"},
    {"name": "Henry Ford", "skills": "Automotive repair and electric vehicle specialist"},
    {"name": "Ivy Watts", "skills": "Electrical engineering and smart home automation"},
    {"name": "Jack Frost", "skills": "HVAC repair and commercial refrigerator maintenance"}
]

async def seed():
    # Note: Local models usually output 384 dimensions, not 1536. 
    # Make sure your Postgres column matches!
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    
    print("🌱 Starting Local Seeding ...")
    
    for worker in workers_data:
        # Generate embedding LOCALLY on your CPU/GPU
        embedding = model.encode(worker["skills"]).tolist()
        
        conn.execute(
            "INSERT INTO workers (name, bio, skills_embedding, status) VALUES (%s, %s, %s, %s)",
            (worker["name"], worker["skills"], embedding, "available")
        )
        print(f"✅ Locally Indexed: {worker['name']}")

    print("🚀 Local Vault is ready. Total API Cost: $0.00")

if __name__ == "__main__":
    asyncio.run(seed())