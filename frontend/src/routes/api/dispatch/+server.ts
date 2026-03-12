import { json } from "@sveltejs/kit";

/**
 * POST /api/dispatch
 * Proxies { description, worker_id } to the local vault's /tasks/dispatch endpoint.
 * Running server-side keeps LOCAL_VAULT_URL secret and avoids browser CORS pre-flights.
 */
export const POST = async ({ request }) => {
  const vaultUrl = process.env.LOCAL_VAULT_URL;

  if (!vaultUrl) {
    return json({ error: "LOCAL_VAULT_URL is not configured on the server." }, { status: 500 });
  }

  const body = await request.json();

  let res: Response;
  try {
    res = await fetch(`${vaultUrl}/tasks/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (err) {
    return json({ error: "Could not reach local vault." }, { status: 502 });
  }

  const data = await res.json();
  return json(data, { status: res.status });
};
