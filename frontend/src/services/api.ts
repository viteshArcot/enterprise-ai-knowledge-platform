/**
 * API client — centralized HTTP layer.
 *
 * All requests to the backend MUST go through this client.
 * This ensures:
 *   - Base URL is configured in one place
 *   - Error handling is consistent across the application
 *   - Support for JSON, FormData, and Streaming (SSE)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || ''; // Use env var for prod, proxy for dev

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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed: ${response.statusText}`;
    try {
      const body = await response.json();
      message = body?.error?.message ?? body?.detail ?? message;
    } catch {
      // Non-JSON error body
    }
    throw createApiError(response.status, response.statusText, message);
  }

  // If it's a 204 No Content or similar empty response
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, options);
  return handleResponse<T>(response);
}

export const apiClient = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'GET', ...options }),

  post: <T>(path: string, body: unknown, options?: RequestInit) => {
    const isFormData = body instanceof FormData;
    const headers = new Headers(options?.headers);

    // Only set application/json if it's not FormData.
    // Let the browser set the boundary for FormData.
    if (!isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return request<T>(path, {
      method: 'POST',
      body: isFormData ? (body as FormData) : JSON.stringify(body),
      headers,
      ...options,
    });
  },

  patch: <T>(path: string, body: unknown, options?: RequestInit) => {
    const isFormData = body instanceof FormData;
    const headers = new Headers(options?.headers);

    if (!isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return request<T>(path, {
      method: 'PATCH',
      body: isFormData ? (body as FormData) : JSON.stringify(body),
      headers,
      ...options,
    });
  },

  put: <T>(path: string, body: unknown, options?: RequestInit) => {
    const isFormData = body instanceof FormData;
    const headers = new Headers(options?.headers);

    if (!isFormData && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    return request<T>(path, {
      method: 'PUT',
      body: isFormData ? (body as FormData) : JSON.stringify(body),
      headers,
      ...options,
    });
  },

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { method: 'DELETE', ...options }),

  upload: <T>(path: string, formData: FormData, options?: RequestInit) =>
    apiClient.post<T>(path, formData, options),

  /**
   * SSE Stream endpoint.
   * Yields text chunks as they arrive.
   */
  stream: async function* (path: string, body: unknown, options?: RequestInit): AsyncGenerator<string, void, unknown> {
    const url = `${API_BASE_URL}${path}`;
    const headers = new Headers(options?.headers);
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(url, {
      method: 'POST',
      body: JSON.stringify(body),
      headers,
      ...options,
    });

    if (!response.ok) {
      let message = `Stream failed: ${response.statusText}`;
      try {
        const errBody = await response.json();
        message = errBody?.detail ?? message;
      } catch {}
      throw createApiError(response.status, response.statusText, message);
    }

    if (!response.body) {
      throw createApiError(500, 'Internal Server Error', 'Response body is null');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        yield decoder.decode(value, { stream: true });
      }
    } finally {
      reader.releaseLock();
    }
  }
};
