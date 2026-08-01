/**
 * API client — centralized HTTP layer.
 *
 * All requests to the backend MUST go through this client.
 * This ensures:
 *   - Base URL is configured in one place (VITE_API_BASE_URL env var)
 *   - Request/response interceptors can be added globally
 *   - Error handling is consistent across the application
 *
 * Why not axios?
 *   fetch() is built into modern browsers and Node 18+. For Phase 1,
 *   the native API is sufficient and reduces bundle size. If we need
 *   advanced features (interceptors, retries, cancellation), we can
 *   migrate to axios or ky in Phase 2 without changing call sites.
 *
 * Evolution plan:
 *   Phase 2: Add request authentication headers (Bearer token)
 *   Phase 2: Add request cancellation via AbortController
 *   Phase 3: Add retry logic for transient failures
 *   Phase 4: Add response caching layer
 */

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

export interface ApiError extends Error {
  status: number;
  statusText: string;
}

export function createApiError(status: number, statusText: string, message: string): ApiError {
  const err = new Error(message) as ApiError;
  err.name = 'ApiError';
  err.status = status;
  err.statusText = statusText;
  return err;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.statusText}`;
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      message = body?.error?.message ?? message;
    } catch {
      // Non-JSON error body — use status text
    }
    throw createApiError(response.status, response.statusText, message);
  }

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, options?: RequestInit) => request<T>(path, { method: 'GET', ...options }),

  post: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body),
      ...options,
    }),

  put: <T>(path: string, body: unknown, options?: RequestInit) =>
    request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body),
      ...options,
    }),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...options }),
};
