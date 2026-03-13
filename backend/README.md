# Backend — FastAPI Vault Server

Local API server that owns the **source of truth**: worker profiles, availability state, skill embeddings, and atomic task assignment.

## Prerequisites

| Tool                             | Version | Notes                                           |
| -------------------------------- | ------- | ----------------------------------------------- |
| Python                           | 3.11+   |                                                 |
| [uv](https://docs.astral.sh/uv/) | latest  | fast Python env manager                         |
| Docker Desktop                   | latest  | runs the Postgres/pgvector container            |
| cloudflared.exe                  | latest  | ships as `backend/cloudflared.exe` in this repo |

## One-time setup

```powershell
# 1. Enter backend folder
cd backend

# 2. Create virtual environment and install dependencies
uv venv
uv pip install fastapi uvicorn psycopg[binary] sentence-transformers pydantic

# 3. Copy env file and fill in values
copy .env.example .env
# Edit .env — the default DATABASE_URL works with docker-compose defaults

# 4. Start Postgres + pgvector container
docker compose up -d

# 5. Create schema (first time only)
docker exec -i local-vault-vdb psql -U dev_user -d task_db -c "
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS workers (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  bio TEXT,
  location TEXT,
  status TEXT DEFAULT 'available',
  skills_embedding vector(384)
);
CREATE TABLE IF NOT EXISTS tasks (
  id SERIAL PRIMARY KEY,
  description TEXT,
  worker_id INT REFERENCES workers(id),
  status TEXT DEFAULT 'open',
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
"

# 6. Seed sample workers (generates embeddings locally)
.venv\Scripts\python.exe seed_workers.py
```

## Running the API server

```powershell
# From backend/
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

On startup you will see:

```
Loading embedding model (BAAI/bge-small-en-v1.5)…
Embedding model ready.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The model is loaded **once** at startup and reused for all requests.

## Running the Cloudflare Tunnel

Open a **separate terminal** and keep it running alongside the API:

```powershell
# From backend/
.\cloudflared.exe tunnel --url http://localhost:8000
```

Copy the `https://*.trycloudflare.com` URL from the output and set it as `PUBLIC_LOCAL_VAULT_URL` in the frontend.

## Quick smoke test

```powershell
.venv\Scripts\python.exe test_bridge.py
# Expected: Status 200 and a JSON list of ranked workers
```

## API Endpoints

| Method | Path              | Description                                                          |
| ------ | ----------------- | -------------------------------------------------------------------- |
| `POST` | `/tasks/match`    | Embed description, return top available workers by similarity        |
| `POST` | `/tasks/claim`    | Atomically assign a worker to a task (returns 409 on race condition) |
| `POST` | `/tasks/dispatch` | Create and assign task atomically                                    |
| `GET`  | `/workers`        | List workers for admin/update UI                                     |
| `POST` | `/workers/update` | Update worker text and trigger embedding regeneration                |
| `GET`  | `/workers/query`  | Natural-language retrieval against worker embeddings                 |
| `POST` | `/search-users`   | Raw vector search (no availability filter)                           |

## File Overview

```
backend/
├── main.py          # FastAPI app + lifespan model cache + endpoints
├── database.py      # get_conn() helper and claim_task_atomically()
├── seed_workers.py  # Generate embeddings + insert sample workers
├── test_bridge.py   # HTTP smoke test for /tasks/match
├── cloudflared.exe  # Cloudflare tunnel binary (Windows)
├── docker-compose.yml
├── .env.example
└── .venv/           # Created by `uv venv`
```
