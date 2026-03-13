## **concise flow**

- **User query (UI):** User types a natural query on the `/query` page or sends a task via the chat UI.
- **LLM orchestration (frontend):** The Vercel AI SDK (in +server.ts) runs the LLM and exposes a tool `searchLocalVault` that must be called to fetch candidates.
- **Tool call → Vault (proxy):** The frontend tool calls the server proxy or directly the local vault URL (env `LOCAL_VAULT_URL`) which forwards to the FastAPI vault.
- **Embedding + retrieval (backend):** FastAPI (main.py) uses the startup‑cached SentenceTransformer model to:
    - Encode the incoming natural language query to an embedding.
    - Run a hybrid SQL search against Postgres+pgvector: first filter (e.g., `WHERE status='available'`) then order by vector similarity (`ORDER BY skills_embedding <=> <query>::vector`) and return top N results.
- **Return candidates:** Backend returns top matches with similarity scores (we convert distance → score_percent).
- **LLM generates grounded response:** The LLM receives the concrete candidate list and generates a summary/suggestion based only on those results (reduces hallucination).
- **User confirms:** UI shows candidate cards; when user clicks Confirm, the frontend posts to `/api/dispatch` (server proxy) → backend `/tasks/dispatch`.
- **Atomic assignment:** `POST /tasks/dispatch` (and `POST /tasks/claim`) perform atomic DB transactions to create the task, set `worker_id`, and mark the worker `busy`—this prevents race conditions.
- **Worker update & reindex:** When a worker profile is changed via `POST /workers/update`, the backend updates the text immediately and enqueues a background task to recompute the embedding using the same local model and write it back to `skills_embedding`. So updates get re‑embedded automatically.

---

```mermaid
sequenceDiagram
    autonumber
    participant U as User (UI)
    participant V as Vercel (Frontend + LLM)
    participant T as Cloudflare Tunnel
    participant F as FastAPI (Local Backend)
    participant D as Docker (Postgres/pgvector)

    Note over U, D: --- RAG QUERY FLOW ---
    U->>V: Types natural language query
    V->>V: AI SDK runs LLM (GPT-4o-Mini)
    V->>V: LLM decides to use 'searchLocalVault'
    V->>T: Tool Call: searchLocalVault(query)
    T->>F: Forward Search Request
    F->>F: Local BGE-Small model encodes query
    F->>D: SQL: ORDER BY vector <=> query_vec
    D-->>F: Return Top N Candidates
    F-->>V: Return JSON Candidates + Scores
    V->>V: LLM summarizes results (Grounded Response)
    V-->>U: Display Candidate Cards

    Note over U, D: --- ATOMIC DISPATCH FLOW ---
    U->>V: Clicks "Confirm Assignment"
    V->>T: POST /tasks/dispatch
    T->>F: Forward Dispatch Request
    F->>D: BEGIN TRANSACTION
    F->>D: Mark task as assigned
    D-->>F: COMMIT (Success/Fail)
    F-->>U: Show Success Toast

    Note over U, D: --- WORKER SYNC & REINDEX FLOW ---
    U->>V: Updates Worker Profile Data
    V->>T: POST /workers/update
    T->>F: Forward Profile Data
    F->>D: Update Bio (Immediate Text Change)
    F->>F: Enqueue Background Task
    F-->>U: 200 OK (UI updates immediately)
    F->>F: Background: Generate New Embedding
    F->>D: UPDATE skills_embedding WHERE id = worker_id
    Note right of D: Vault is now Re-Indexed

```

### **How to read this diagram:**

1. **The RAG Loop (1-10):** Notice how the LLM doesn't just guess. It pauses, asks the local backend for data, and only speaks once it has the "Ground Truth" from your Docker Vault.
2. **The Tunnel (T):** This acts as the secure gatekeeper. Every request from the cloud must pass through here to reach your local machine.
3. **Atomic Dispatch (11-15):** The "Begin Transaction" step in Docker is what prevents two users from hiring the same worker at the exact same millisecond.
4. **Async Re-indexing (16-22):** This is the "Auto-Sync" part. We update the text immediately so the user sees their change, but we calculate the math (embedding) in the background so the server doesn't lag.

**Key components / files**

- Backend: main.py (startup cached model, `/workers/query`, `/workers/update`, `/tasks/match`, `/tasks/dispatch`, `/tasks/claim`), seed_workers.py (initial embeddings)
- DB: Postgres + `pgvector` extension, `skills_embedding vector(384)` column
- Frontend: `/query` page and `/update-worker` page, +server.ts and +server.ts proxy routes, chat handler +server.ts
- Env: `LOCAL_VAULT_URL` points to your FastAPI vault (tunnel or localhost)

**Why this design helps**

- Privacy: PII and embedding store stay local (no sending full profiles to cloud).
- Cost: embeddings are computed locally (no per-request paid embeddings).
- Freshness & safety: we filter by `status='available'` before similarity to avoid suggesting busy workers; atomic DB transactions avoid race conditions.
- Explainability: LLM summarizes actual returned records rather than inventing them.

## Cost
### **1. Estimated Monthly Cost Breakdown (Projections)**

If you host this as a unified system (FastAPI + Postgres in Docker) on a Virtual Private Server (VPS), here is what you are looking at:

| Component | Minimum Req. | Estimated Cost (Monthly) | Reason |
| --- | --- | --- | --- |
| **Compute (VPS)** | 2 vCPU / 4GB RAM | **$20 – $40** | The BGE-Small model and Postgres need at least 4GB to run smoothly without crashing. |
| **Storage** | 20GB SSD | **$2 – $5** | Vector data is small, but the Docker images and OS take up space. |
| **Bandwidth** | 1TB Transfer | **$0 – $5** | Standard web traffic; usually included in VPS plans. |
| **LLM Tokens** | (Vercel/OpenAI) | **$5 – $15** | Depends on how many "Chat" queries you run. |
| **Total** |  | **$27 – $65 / month** |  |

### **2. Recommended Hosting Providers**

For a RAG system using Docker and `pgvector`, you want a provider that gives you "Raw" control over the machine:

* **DigitalOcean (Basic Droplet):** Roughly **$24/mo** for 2 vCPU and 4GB RAM. Very reliable and easy to set up with Docker.
* **Hetzner (Cloud):** The "Budget King." You can get 4GB RAM for around **$6 – $10/mo**. Best performance-to-price ratio for 2026.
* **AWS (Lightsail or EC2):** Roughly **$40/mo**. More expensive, but scales better if you plan to add millions of workers.


### **3. Cost Optimization Strategies**

Because your RAG system is **local-first**, you can save money that others spend on "Vector-as-a-Service" (like Pinecone):

1. **Avoid Managed Databases:** Do not use AWS RDS or Managed Postgres. They start at $60/mo. Stick to **Postgres inside Docker** on your VPS to save ~$50/mo.
2. **Model Quantization:** Use a "Quantized" version of your embedding model. This reduces the RAM requirement, potentially letting you drop down to a $12/mo server.
3. **The "Idle" Strategy:** If this is for internal use (Internship/Dev), you can use a "Spot Instance" which is 70% cheaper but can be turned off by the provider at any time.

