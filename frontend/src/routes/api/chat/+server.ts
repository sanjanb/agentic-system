import { streamText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

const SYSTEM_PROMPT = `You are a smart dispatch agent for a field-service platform.
When a user describes a task, you MUST call the searchLocalVault tool with their exact description to find available workers.
After receiving results, summarise the top candidate in one sentence and tell the user to click "Confirm Assignment" on the card to lock in the assignment.
Never make up worker names or availability — always rely on tool results.
Never call confirmAssignment yourself — the user confirms via the UI button.`;

export const POST = async ({ request }) => {
  const { messages } = await request.json();

  return streamText({
    model: openai("gpt-4o-mini"),
    system: SYSTEM_PROMPT,
    messages,
    maxSteps: 5,
    tools: {
      // Primary search tool — calls the local vault's hybrid vector search
      searchLocalVault: tool({
        description:
          "Search the local vault for available workers matching a task description. Always call this first.",
        parameters: z.object({
          description: z
            .string()
            .describe("The task description to match workers against"),
        }),
        execute: async ({ description }) => {
          const vaultUrl = process.env.LOCAL_VAULT_URL;
          if (!vaultUrl) throw new Error("LOCAL_VAULT_URL is not configured");
          const res = await fetch(`${vaultUrl}/tasks/match`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description }),
          });
          if (!res.ok) throw new Error(`Vault error: ${res.status}`);
          return res.json();
        },
      }),
    },
  }).toDataStreamResponse();
};
