import { streamText, tool } from "ai";
import { openai } from "@ai-sdk/openai";

export const POST = async ({ request }) => {
  return streamText({
    model: openai("gpt-4o-mini"),
    maxSteps: 5, // Allow the agent to search local DB and then decide
    tools: {
      getWorkerSuggestions: tool({
        description: "Call the local vault to find matching available workers",
        execute: async ({ taskDescription }) => {
          const res = await fetch(`${process.env.LOCAL_VAULT_URL}/match`, {
            method: "POST",
            body: JSON.stringify({ description: taskDescription }),
          });
          return res.json();
        },
      }),
    },
  });
};
