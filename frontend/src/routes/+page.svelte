<script lang="ts">
  import { useChat } from '@ai-sdk/svelte';

  // useChat handles the streaming and tool-call state automatically
  const { messages, input, handleSubmit, isLoading } = useChat();
</script>

<main class="container">
  <h1>Dispatch Center</h1>

  <div class="chat-log">
    {#each $messages as message}
      <div class="message {message.role}">
        <strong>{message.role === 'user' ? 'Client' : 'Agent'}:</strong>
        <p>{message.content}</p>
        
        {#if message.toolInvocations}
          <div class="system-note">
            {#each message.toolInvocations as tool}
              <span>⚙️ Executing: {tool.toolName}...</span>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <form on:submit={handleSubmit}>
    <input 
      bind:value={$input} 
      placeholder="e.g., 'Find someone to fix the plumbing'" 
      disabled={$isLoading}
    />
    <button type="submit">Dispatch Agent</button>
  </form>
</main>

<style>
  .container { max-width: 800px; margin: 0 auto; padding: 2rem; }
  .chat-log { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 1rem; margin-bottom: 1rem; }
  .user { color: blue; }
  .assistant { color: green; }
  .system-note { font-size: 0.8rem; color: #666; font-style: italic; }
</style>