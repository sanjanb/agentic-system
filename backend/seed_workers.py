import asyncio
import psycopg
from pgvector.psycopg import register_vector
from openai import OpenAI
import os

# 1. Setup OpenAI & Connection
client = OpenAI(api_key="your_openai_api_key_here")
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
    conn = psycopg.connect(DB_URL, autocommit=True)
    register_vector(conn)
    
    print("🌱 Starting to seed workers...")
    
    for worker in workers_data:
        # Generate embedding for the skills
        response = client.embeddings.create(
            input=worker["skills"],
            model="text-embedding-3-small"
        )
        embedding = response.data[0].embedding
        
        # Insert into Local Vault
        conn.execute(
            "INSERT INTO workers (name, bio, skills_embedding, status) VALUES (%s, %s, %s, %s)",
            (worker["name"], worker["skills"], embedding, "available")
        )
        print(f"✅ Added {worker['name']}")

    print("🚀 Seeding complete! Your Local Vault is ready for dispatch.")

if __name__ == "__main__":
    asyncio.run(seed())