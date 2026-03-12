import { streamText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

export const POST = async ({ request }) => {
  const { messages } = await request.json();

  return streamText({
    model: openai("gpt-4o-mini"),
    messages,
    maxSteps: 5, // Important: Allows the agent to "loop" through tools
    tools: {
      // Tool 1: Get available workers from your Local Vault
      fetchAvailableWorkers: tool({
        description:
          "Get a list of currently available workers from the local database",
        parameters: z.object({}),
        execute: async () => {
          const res = await fetch(
            `${process.env.LOCAL_VAULT_URL}/workers/available`,
          );
          return res.json();
        },
      }),
      // Tool 2: Atomically assign a task
      assignTask: tool({
        description: "Assign a specific task to a worker (legacy)",
        parameters: z.object({
          taskId: z.number(),
          workerId: z.number(),
        }),
        execute: async ({ taskId, workerId }) => {
          const res = await fetch(
            `${process.env.LOCAL_VAULT_URL}/tasks/assign`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ task_id: taskId, worker_id: workerId }),
            },
          );
          return res.json();
        },
      }),
      // Tool 3: Confirm assignment using atomic claim endpoint
      confirmAssignment: tool({
        description: "Finalize the task assignment once a worker is chosen.",
        parameters: z.object({
          taskId: z.number(),
          workerId: z.number(),
        }),
        execute: async ({ taskId, workerId }) => {
          const response = await fetch(
            `${process.env.LOCAL_VAULT_URL}/tasks/claim`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ task_id: taskId, worker_id: workerId }),
            },
          );
          return response.json();
        },
      }),
    },
  });
};
