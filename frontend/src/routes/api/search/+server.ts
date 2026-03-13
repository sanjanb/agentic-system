import { json } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

export const GET = async ({ url, fetch }) => {
  const vaultUrl = env.LOCAL_VAULT_URL;
  if (!vaultUrl) {
    return json(
      { error: 'LOCAL_VAULT_URL is not configured on the server.' },
      { status: 500 }
    );
  }

  const q = (url.searchParams.get('q') ?? '').trim();
  const limit = (url.searchParams.get('limit') ?? '5').trim();

  if (!q) {
    return json({ error: 'q is required.' }, { status: 400 });
  }

  const target = new URL(`${vaultUrl}/workers/query`);
  target.searchParams.set('q', q);
  target.searchParams.set('limit', limit);
  target.searchParams.set('available_only', 'true');

  let res: Response;
  try {
    res = await fetch(target.toString(), {
      method: 'GET',
      headers: { Accept: 'application/json' }
    });
  } catch {
    return json({ error: 'Could not reach local vault.' }, { status: 502 });
  }

  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    const error =
      typeof payload === 'object' && payload && 'detail' in payload
        ? String((payload as { detail: string }).detail)
        : `Vault request failed (${res.status}).`;
    return json({ error }, { status: res.status });
  }

  return json(payload, { status: 200 });
};
