<script lang="ts">
  import { enhance } from '$app/forms';

  let { data, form } = $props();

  type Worker = {
    id: number;
    name: string;
    bio: string;
    status: string;
  };

  const workers = $derived((data.workers ?? []) as Worker[]);

  let selectedWorkerId = $state<number | ''>('');
  let name = $state('');
  let bio = $state('');

  $effect(() => {
    if (workers.length === 0) return;

    if (selectedWorkerId === '') {
      selectedWorkerId = workers[0].id;
    }

    const selected = workers.find((worker) => worker.id === Number(selectedWorkerId));
    if (selected) {
      name = selected.name;
      bio = selected.bio;
    }
  });
</script>

<section class="panel">
  <h1>Update Worker Profile</h1>
  <p class="subtitle">Sync profile text to Postgres and regenerate embeddings locally.</p>

  {#if data.loadError}
    <p class="error">{data.loadError}</p>
  {/if}

  <form method="POST" action="?/update" use:enhance class="form-grid">
    <label>
      Worker
      <select name="worker_id" bind:value={selectedWorkerId}>
        {#each workers as worker}
          <option value={worker.id}>{worker.name} ({worker.status})</option>
        {/each}
      </select>
    </label>

    <label>
      Full Name
      <input name="name" type="text" bind:value={name} required />
    </label>

    <label>
      Skills / Bio
      <textarea name="bio" bind:value={bio} rows="6" required></textarea>
    </label>

    <button type="submit">Sync to Vault and AI</button>
  </form>

  {#if form?.message}
    <p class:success={form?.success} class:error={!form?.success}>{form.message}</p>
  {/if}
</section>

<style>
  .panel {
    width: min(760px, 100%);
    margin: 0 auto;
    padding: 1rem;
    display: grid;
    gap: 0.75rem;
  }

  .subtitle {
    margin: 0;
    color: #666;
  }

  .form-grid {
    display: grid;
    gap: 0.9rem;
  }

  label {
    display: grid;
    gap: 0.35rem;
    font-weight: 600;
  }

  input,
  select,
  textarea,
  button {
    font: inherit;
    padding: 0.6rem 0.7rem;
    border: 1px solid #c0c0c0;
    border-radius: 8px;
    background: #fff;
  }

  textarea {
    resize: vertical;
  }

  button {
    width: fit-content;
    border-color: #1f6feb;
    background: #1f6feb;
    color: #fff;
    cursor: pointer;
  }

  .success {
    color: #1a7f37;
    font-weight: 600;
  }

  .error {
    color: #b42318;
    font-weight: 600;
  }
</style>
