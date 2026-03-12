<script lang="ts">
  import { Chat } from '@ai-sdk/svelte';
  import { DefaultChatTransport } from 'ai';

  const chat = new Chat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  });

  // Simulated match scores for top-3 ranked results (vector similarity → rank)
  const MATCH_SCORES = [98, 85, 72];

  // Human-readable labels for tool call status badges
  const TOOL_LABELS: Record<string, string> = {
    searchLocalVault: 'Searching local vault…',
  };

  let inputValue = $state('');
  let taskDescription = $state('');

  // Per-worker confirmation state
  let confirmStates = $state<Record<number, 'loading' | 'success' | 'conflict'>>({});

  const isLoading = $derived(
    chat.status === 'submitted' || chat.status === 'streaming'
  );
  const anyConfirmed = $derived(Object.values(confirmStates).includes('success'));

  // Keep taskDescription in sync with the latest user message
  $effect(() => {
    const userMsgs = chat.messages.filter((m) => m.role === 'user');
    if (userMsgs.length > 0) {
      const last = userMsgs[userMsgs.length - 1];
      const textPart = last.parts.find((p) => p.type === 'text');
      if (textPart && 'text' in textPart) taskDescription = textPart.text;
    }
  });

  async function handleSubmit(e: Event) {
    e.preventDefault();
    const text = inputValue.trim();
    if (!text) return;
    inputValue = '';
    await chat.sendMessage({ text });
  }

  async function confirmAssignment(workerId: number) {
    confirmStates[workerId] = 'loading';
    try {
      const res = await fetch('/api/dispatch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: taskDescription, worker_id: workerId }),
      });
      confirmStates[workerId] = res.ok ? 'success' : 'conflict';
    } catch {
      confirmStates[workerId] = 'conflict';
    }
  }
</script>

<main class="container">
  <header>
    <h1>🏥 Dispatch Command Center</h1>
    <p class="subtitle">AI-powered task-worker matching — Private &amp; Secure</p>
  </header>

  <div class="chat-log">
    {#each chat.messages as message}
      <div class="message {message.role}">

        {#if message.role === 'user'}
          <!-- ── Client message ── -->
          <div class="bubble user-bubble">
            <span class="role-label">Client</span>
            {#each message.parts as part}
              {#if part.type === 'text'}<p>{part.text}</p>{/if}
            {/each}
          </div>

        {:else}
          <!-- ── Agent: tool call status badges + candidate cards + text ── -->
          {#each message.parts as part}
            {#if part.type === 'dynamic-tool'}
              {#if part.state === 'input-streaming' || part.state === 'input-available'}
                <div class="badge thinking">
                  ⚙️ {TOOL_LABELS[part.toolName] ?? `Calling ${part.toolName}…`}
                </div>
              {:else if part.state === 'output-available' && part.toolName === 'searchLocalVault'}
                <div class="badge done">✅ Analyzing candidate availability…</div>
                <div class="card-list">
                  {#each (part.output as Array<{id: number; name: string; bio: string}>) as candidate, i}
                    <div class="card">
                      <div class="card-header">
                        <span class="rank">#{i + 1}</span>
                        <span class="worker-name">{candidate.name}</span>
                        <span class="score">{MATCH_SCORES[i] ?? 60}% match</span>
                      </div>
                      <p class="bio">{candidate.bio}</p>
                      <div class="card-footer">
                        {#if confirmStates[candidate.id] === 'success'}
                          <span class="state-success">✅ Assigned successfully!</span>
                        {:else if confirmStates[candidate.id] === 'conflict'}
                          <span class="state-conflict">⚠️ No longer available</span>
                        {:else}
                          <button
                            class="confirm-btn"
                            disabled={confirmStates[candidate.id] === 'loading' || anyConfirmed}
                            onclick={() => confirmAssignment(candidate.id)}
                          >
                            {confirmStates[candidate.id] === 'loading' ? 'Confirming…' : 'Confirm Assignment'}
                          </button>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            {:else if part.type === 'text' && part.text}
              <div class="bubble agent-bubble">
                <span class="role-label">Agent</span>
                <p>{part.text}</p>
              </div>
            {/if}
          {/each}
        {/if}

      </div>
    {/each}

    {#if isLoading}
      <div class="badge thinking">⚙️ Agent is thinking…</div>
    {/if}
  </div>

  <form onsubmit={handleSubmit} class="input-row">
    <input
      class="task-input"
      bind:value={inputValue}
      placeholder="e.g. 'Find a plumber for a commercial kitchen emergency…'"
      disabled={isLoading}
    />
    <button class="dispatch-btn" type="submit" disabled={isLoading}>
      {isLoading ? 'Dispatching…' : '🚀 Dispatch Agent'}
    </button>
  </form>
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f1117;
    color: #e0e0e0;
  }

  .container {
    max-width: 860px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }

  header { margin-bottom: 1.5rem; }
  h1 { font-size: 1.6rem; margin: 0 0 0.25rem; }
  .subtitle { color: #555; font-size: 0.85rem; margin: 0; }

  /* ── Chat log ── */
  .chat-log {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    overflow-y: auto;
    padding: 1rem;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    margin-bottom: 1rem;
    min-height: 420px;
  }

  .message { display: flex; flex-direction: column; gap: 0.4rem; }

  /* ── Chat bubbles ── */
  .bubble { padding: 0.75rem 1rem; border-radius: 8px; max-width: 85%; }
  .user-bubble  { background: #1c4a8a; align-self: flex-end; }
  .agent-bubble { background: #1e2d1e; align-self: flex-start; }
  .role-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.55; }
  .bubble p { margin: 0.25rem 0 0; line-height: 1.55; }

  /* ── Status badges ── */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.78rem;
    width: fit-content;
  }
  .thinking {
    background: #2d2a1e;
    color: #d4a017;
    border: 1px solid #5a4a00;
    animation: pulse 1.4s ease-in-out infinite;
  }
  .done { background: #1a2e1a; color: #4caf50; border: 1px solid #2a5c2a; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }

  /* ── Candidate Cards ── */
  .card-list { display: flex; flex-direction: column; gap: 0.6rem; margin-top: 0.5rem; }

  .card {
    background: #1c2333;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 0.85rem 1rem;
  }

  .card-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.45rem;
  }

  .rank {
    background: #0d3a6e;
    color: #58a6ff;
    font-size: 0.68rem;
    font-weight: 700;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
  }

  .worker-name { font-weight: 600; font-size: 0.95rem; }

  .score {
    margin-left: auto;
    font-size: 0.75rem;
    color: #4caf50;
    font-weight: 600;
  }

  .bio {
    font-size: 0.82rem;
    color: #8b949e;
    margin: 0 0 0.65rem;
    line-height: 1.45;
  }

  .card-footer { display: flex; justify-content: flex-end; }

  .confirm-btn {
    background: #238636;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 0.42rem 1.1rem;
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.18s;
  }
  .confirm-btn:hover:not(:disabled) { background: #2ea043; }
  .confirm-btn:disabled { opacity: 0.45; cursor: not-allowed; }

  .state-success { color: #4caf50; font-size: 0.85rem; font-weight: 600; }
  .state-conflict { color: #f57c00; font-size: 0.85rem; font-weight: 600; }

  /* ── Input row ── */
  .input-row { display: flex; gap: 0.6rem; }

  .task-input {
    flex: 1;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    border: 1px solid #30363d;
    background: #161b22;
    color: #e0e0e0;
    font-size: 0.9rem;
  }
  .task-input:focus { outline: none; border-color: #58a6ff; }
  .task-input::placeholder { color: #444; }

  .dispatch-btn {
    padding: 0.75rem 1.4rem;
    border-radius: 8px;
    border: none;
    background: #1c4a8a;
    color: #fff;
    font-size: 0.9rem;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.18s;
  }
  .dispatch-btn:hover:not(:disabled) { background: #2158a8; }
  .dispatch-btn:disabled { opacity: 0.45; cursor: not-allowed; }
</style>