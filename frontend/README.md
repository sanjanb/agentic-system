# Frontend — SvelteKit Dispatch Command Center

Vercel-hosted chat UI that uses the **Vercel AI SDK** to reason over task requests, query the local vault for available workers, and confirm atomic assignments.

## Prerequisites

| Tool                  | Version |
| --------------------- | ------- |
| Node.js               | 18+     |
| npm                   | 9+      |
| Vercel CLI (optional) | latest  |

The backend must be running and the Cloudflare tunnel must be active before the frontend can call the vault.

## One-time setup

```powershell
# 1. Enter frontend folder
cd frontend

# 2. Install dependencies
npm install

# 3. Copy env file and fill in values
copy .env.example .env.local
# Edit .env.local:
#   PUBLIC_LOCAL_VAULT_URL=https://<your-tunnel>.trycloudflare.com
#   OPENAI_API_KEY=sk-...
```

## Running locally

```powershell
npm run dev
# Open http://localhost:5173
```

## Deploying to Vercel

```powershell
# First time
npx vercel

# Set environment variables on Vercel dashboard (or via CLI):
vercel env add PUBLIC_LOCAL_VAULT_URL
vercel env add OPENAI_API_KEY

# Re-deploy after env changes
vercel --prod
```

> **Important:** Every time you restart the Cloudflare tunnel a new URL is generated. Update `PUBLIC_LOCAL_VAULT_URL` in Vercel and redeploy, or use a named tunnel for a stable URL.

## How the AI tools work

| Tool                    | What it does                                                                      |
| ----------------------- | --------------------------------------------------------------------------------- |
| `fetchAvailableWorkers` | Calls `POST /tasks/match` on the vault; returns ranked candidates                 |
| `confirmAssignment`     | Calls `POST /tasks/claim`; atomically locks worker; returns 409 on race condition |

The AI is given these tools via the Vercel AI SDK in `src/routes/api/chat/+server.ts`. The LLM (gpt-4o-mini) reasons over the task description, calls the tools, and renders a Candidate Card before asking for confirmation.

## File Overview

```
frontend/
├── src/
│   └── routes/
│       ├── +page.svelte          # Chat UI with candidate cards
│       └── api/chat/
│           └── +server.ts        # AI SDK stream handler + tool definitions
├── .env.example
├── .env.local                    # Your local secrets (git-ignored)
└── package.json
```
