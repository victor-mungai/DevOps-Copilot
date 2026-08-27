// Centralized API client. All calls go through the gateway (VITE_API_BASE),
// which injects tenant identity downstream. We also send X-Tenant-ID explicitly
// so every request stays tenant-scoped even when gateway auth is disabled.

export const apiBase: string =
  (import.meta.env.VITE_API_BASE as string | undefined) || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function readBody(res: Response): Promise<unknown> {
  const raw = await res.text();
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { detail: raw };
  }
}

function extractDetail(body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === 'string') return d;
    try {
      return JSON.stringify(d);
    } catch {
      /* fall through */
    }
  }
  return 'Request failed';
}

export interface ApiOptions extends Omit<RequestInit, 'body'> {
  tenantId?: string;
  body?: unknown;
}

/**
 * Fetch JSON from the gateway. Throws ApiError on non-2xx.
 * Pass `tenantId` to scope the request (adds the X-Tenant-ID header).
 */
export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { tenantId, body, headers, ...rest } = options;

  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string> | undefined),
  };
  if (tenantId) finalHeaders['X-Tenant-ID'] = tenantId;

  const res = await fetch(`${apiBase}${path}`, {
    ...rest,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const parsed = await readBody(res);
  if (!res.ok) {
    throw new ApiError(extractDetail(parsed), res.status, parsed);
  }
  return parsed as T;
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  if (typeof e === 'string') return e;
  try {
    return JSON.stringify(e);
  } catch {
    return 'Unknown error';
  }
}
