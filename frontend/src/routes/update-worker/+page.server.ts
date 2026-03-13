import { env } from '$env/dynamic/private';
import { fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type Worker = {
  id: number;
  name: string;
  bio: string;
  status: string;
};

function getVaultUrl() {
  const vaultUrl = env.LOCAL_VAULT_URL;
  if (!vaultUrl) {
    throw new Error('LOCAL_VAULT_URL is not configured on the server.');
  }
  return vaultUrl;
}

export const load: PageServerLoad = async ({ fetch }) => {
  try {
    const vaultUrl = getVaultUrl();
    const res = await fetch(`${vaultUrl}/workers`);

    if (!res.ok) {
      return {
        workers: [] as Worker[],
        loadError: `Could not load workers (${res.status}).`
      };
    }

    const workers = (await res.json()) as Worker[];
    return { workers };
  } catch {
    return {
      workers: [] as Worker[],
      loadError: 'Could not reach local vault API.'
    };
  }
};

export const actions: Actions = {
  update: async ({ request, fetch }) => {
    const formData = await request.formData();
    const workerId = Number(formData.get('worker_id'));
    const name = String(formData.get('name') ?? '').trim();
    const bio = String(formData.get('bio') ?? '').trim();

    if (!workerId || !name || !bio) {
      return fail(400, {
        success: false,
        message: 'Worker ID, full name, and bio are required.'
      });
    }

    let vaultUrl: string;
    try {
      vaultUrl = getVaultUrl();
    } catch (error) {
      return fail(500, {
        success: false,
        message: 'LOCAL_VAULT_URL is missing on the server.'
      });
    }

    let res: Response;
    try {
      res = await fetch(`${vaultUrl}/workers/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          worker_id: workerId,
          name,
          bio
        })
      });
    } catch {
      return fail(502, {
        success: false,
        message: 'Could not reach local vault API.'
      });
    }

    let payload: unknown = null;
    try {
      payload = await res.json();
    } catch {
      payload = null;
    }

    if (!res.ok) {
      const errorMessage =
        typeof payload === 'object' && payload && 'detail' in payload
          ? String((payload as { detail: string }).detail)
          : `Update failed with status ${res.status}.`;

      return fail(res.status, {
        success: false,
        message: errorMessage
      });
    }

    const message =
      typeof payload === 'object' && payload && 'message' in payload
        ? String((payload as { message: string }).message)
        : 'Worker updated. Embedding sync started.';

    return {
      success: true,
      message
    };
  }
};
