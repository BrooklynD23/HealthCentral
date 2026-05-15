/**
 * API Client for HealthCentral Backend
 *
 * Base configuration and fetch wrapper for all API calls.
 * Sprint 1: Added Authorization header support.
 *
 * In development, requests use same-origin `/api/v1` so Vite can proxy to the
 * backend port from `.env.local` (avoids stale absolute URLs when ports shift).
 */

import { useAuthStore } from '@/stores/authStore';

function resolveApiBaseUrl(): string {
  if (import.meta.env.DEV) {
    return '/api/v1';
  }
  const fromEnv = import.meta.env.VITE_API_URL;
  return typeof fromEnv === 'string' && fromEnv.trim()
    ? fromEnv.trim().replace(/\/$/, '')
    : 'http://localhost:8000/api/v1';
}

const API_BASE_URL = resolveApiBaseUrl();

/** Same base URL used by `api*` helpers (handy for `<img src>` and diagnostics). */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Get authorization headers if token exists.
 */
function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * After session invalidation, send the user to profile setup/sign-in so they are not
 * stuck on a protected page behind a generic error (e.g. failed document list).
 */
function redirectToSessionRecovery(): void {
  if (typeof window === 'undefined') return;
  if (window.location.pathname === '/setup') return;
  window.location.replace(`${window.location.origin}/setup`);
}

/**
 * Handle 401/403 errors by clearing auth state.
 */
function handleAuthError(status: number): void {
  if (status === 401) {
    useAuthStore.getState().clearAuth();
    redirectToSessionRecovery();
  }
  // 403 is kept - profile database locked, but token may still be valid
}

function networkFailureHint(): string {
  if (API_BASE_URL.startsWith('/')) {
    return (
      ' Start the backend (e.g. dev.ps1) and restart the frontend dev server after changing .env.local. ' +
      'If you opened this page days ago, refresh so Vite picks up the latest proxy target.'
    );
  }
  const origin = API_BASE_URL.replace(/\/api\/v1\/?$/i, '');
  return ` Is the API running at ${origin}?`;
}

async function fetchOrExplain(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    const isFetchFailed =
      e instanceof TypeError &&
      (e.message === 'Failed to fetch' || e.message.toLowerCase().includes('fetch'));
    if (isFetchFailed) {
      throw new Error(`Failed to fetch.${networkFailureHint()}`);
    }
    throw e;
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorBody = await response.text();
    let message = errorBody;
    try {
      const parsed = JSON.parse(errorBody);
      message = parsed.detail || parsed.message || errorBody;
    } catch {
      // Use raw text
    }

    // Handle auth errors
    handleAuthError(response.status);

    throw new ApiError(response.status, response.statusText, message);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/** Build `/api/v1/...` or absolute API URL with optional query string. */
function buildApiUrl(endpoint: string, params?: Record<string, string>): string {
  const base = API_BASE_URL.replace(/\/$/, '');
  const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  let url = `${base}${path}`;
  if (params) {
    const sp = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        sp.append(key, value);
      }
    });
    const q = sp.toString();
    if (q) url += `?${q}`;
  }
  return url;
}

export async function apiGet<T>(
  endpoint: string,
  params?: Record<string, string>
): Promise<T> {
  const url = buildApiUrl(endpoint, params);

  const response = await fetchOrExplain(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
  });

  return handleResponse<T>(response);
}

export async function apiPost<T, D = unknown>(
  endpoint: string,
  data?: D,
  init?: Omit<RequestInit, 'method' | 'body' | 'headers'>
): Promise<T> {
  const url = buildApiUrl(endpoint);

  const response = await fetchOrExplain(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
    body: data ? JSON.stringify(data) : undefined,
    ...init,
  });

  return handleResponse<T>(response);
}

export async function apiPut<T, D = unknown>(
  endpoint: string,
  data: D
): Promise<T> {
  const url = buildApiUrl(endpoint);

  const response = await fetchOrExplain(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  return handleResponse<T>(response);
}

export async function apiPatch<T, D = unknown>(
  endpoint: string,
  data: D
): Promise<T> {
  const url = buildApiUrl(endpoint);

  const response = await fetchOrExplain(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });

  return handleResponse<T>(response);
}

export async function apiDelete(endpoint: string): Promise<void> {
  const url = buildApiUrl(endpoint);

  const response = await fetchOrExplain(url, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    credentials: 'include',
  });

  return handleResponse<void>(response);
}

/**
 * Raw GET request that returns the Response object directly.
 * Use for binary downloads (PDF, HTML) where response.json() would fail.
 */
export async function apiGetRaw(
  endpoint: string,
  params?: Record<string, string>
): Promise<Response> {
  const url = buildApiUrl(endpoint, params);

  const response = await fetchOrExplain(url, {
    method: 'GET',
    headers: {
      ...getAuthHeaders(),
    },
    credentials: 'include',
  });

  if (!response.ok) {
    handleAuthError(response.status);
    const errorBody = await response.text();
    let message = errorBody;
    try {
      const parsed = JSON.parse(errorBody);
      message = parsed.detail || parsed.message || errorBody;
    } catch {
      // Use raw text
    }
    throw new ApiError(response.status, response.statusText, message);
  }

  return response;
}

export async function apiUpload<T>(
  endpoint: string,
  file: File,
  params?: Record<string, string>
): Promise<T> {
  const url = buildApiUrl(endpoint, params);

  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchOrExplain(url, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
    },
    credentials: 'include',
    body: formData,
  });

  return handleResponse<T>(response);
}
