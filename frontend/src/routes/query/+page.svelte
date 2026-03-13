<script lang="ts">
  type SearchResult = {
    id: number;
    name: string;
    bio: string;
    status: string;
    score_percent: number;
  };

  let query = $state('');
  let loading = $state(false);
  let error = $state('');
  let results = $state<SearchResult[]>([]);

  async function search() {
    const q = query.trim();
    if (!q) {
      error = 'Please enter a query.';
      results = [];
      return;
    }

    loading = true;
    error = '';

    try {
      const params = new URLSearchParams({ q, limit: '5' });
      const res = await fetch(`/api/search?${params.toString()}`);
      const payload = await res.json();

      if (!res.ok) {
        error = payload?.error ?? `Search failed (${res.status}).`;
        results = [];
        return;
      }

      results = payload;
    } catch {
      error = 'Could not reach search API.';
      results = [];
    } finally {
      loading = false;
    }
  }
</script>

<section class="panel">
  <h1>Natural Language RAG Query</h1>
  <p class="subtitle">Ask in plain words and retrieve the best worker matches from pgvector.</p>

  <div class="query-row">
    <input
      bind:value={query}
      placeholder="e.g., I need a plumber who can also handle AWS monitoring"
      onkeydown={(event) => event.key === 'Enter' && search()}
    />
    <button onclick={search} disabled={loading}>{loading ? 'Searching...' : 'Ask the Vault'}</button>
  </div>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <ul class="results">
    {#each results as worker}
      <li class="card">
        <h3>{worker.name}</h3>
        <p>{worker.bio}</p>
        <p class="meta">Status: {worker.status} | Match: {worker.score_percent}%</p>
      </li>
    {/each}
  </ul>
</section>

<style>
  .panel {
    width: min(760px, 100%);
    margin: 0 auto;
    padding: 1rem;
    display: grid;
    gap: 0.9rem;
  }

  .subtitle {
    margin: 0;
    color: #666;
  }

  .query-row {
    display: flex;
    gap: 0.6rem;
  }

  input {
    flex: 1;
    padding: 0.65rem 0.75rem;
    border: 1px solid #c0c0c0;
    border-radius: 8px;
    font: inherit;
  }

  button {
    padding: 0.65rem 0.95rem;
    border: 1px solid #1f6feb;
    border-radius: 8px;
    background: #1f6feb;
    color: #fff;
    cursor: pointer;
    font: inherit;
  }

  button:disabled {
    opacity: 0.65;
    cursor: default;
  }

  .results {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: 0.6rem;
  }

  .card {
    border: 1px solid #d0d0d0;
    border-radius: 10px;
    padding: 0.8rem 0.95rem;
    background: #fff;
  }

  .card h3 {
    margin: 0 0 0.35rem;
  }

  .card p {
    margin: 0 0 0.35rem;
    line-height: 1.4;
  }

  .meta {
    font-size: 0.9rem;
    color: #555;
    font-weight: 600;
  }

  .error {
    color: #b42318;
    font-weight: 600;
  }
</style>
