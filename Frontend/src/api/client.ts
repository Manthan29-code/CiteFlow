import { env } from '@/lib/env';
import { getCsrfToken } from './csrf';
import { ApiError } from './errors';

let refreshPromise: Promise<boolean> | null = null;

async function executeSingleFlightRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const csrf = getCsrfToken();
        const headers: Record<string, string> = {};
        if (csrf) {
          headers['X-CSRF-Token'] = csrf;
        }

        const res = await fetch(`${env.VITE_API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers,
        });

        return res.ok;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();
  }
  return refreshPromise;
}

export interface RequestOptions extends RequestInit {
  skipAuthRefresh?: boolean;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${env.VITE_API_BASE_URL}${endpoint}`;
  const method = (options.method || 'GET').toUpperCase();
  const headers = new Headers(options.headers || {});

  // Add CSRF token for mutating requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken && !headers.has('X-CSRF-Token')) {
      headers.set('X-CSRF-Token', csrfToken);
    }
  }

  // Set default JSON Content-Type if sending body and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      credentials: 'include',
    });
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Check your connection.');
  }

  const requestId = response.headers.get('X-Request-ID');

  // Handle 401 Unauthorized with single-flight token rotation (except for /auth endpoints)
  const isAuthEndpoint = endpoint.includes('/auth/login') || endpoint.includes('/auth/refresh') || endpoint.includes('/auth/register');
  if (response.status === 401 && !isAuthEndpoint && !options.skipAuthRefresh) {
    const refreshed = await executeSingleFlightRefresh();
    if (refreshed) {
      // Re-read CSRF in case rotated
      const newCsrf = getCsrfToken();
      if (newCsrf && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        headers.set('X-CSRF-Token', newCsrf);
      }

      try {
        response = await fetch(url, {
          ...options,
          headers,
          credentials: 'include',
        });
      } catch {
        throw new ApiError(0, 'network_error', 'Cannot reach the server on retry.');
      }
    } else {
      // Refresh failed: session expired
      if (typeof window !== 'undefined') {
        const currentPath = window.location.pathname + window.location.search;
        if (!currentPath.startsWith('/login') && !currentPath.startsWith('/register')) {
          window.location.href = `/login?next=${encodeURIComponent(currentPath)}`;
        }
      }
      throw new ApiError(401, 'unauthorized', 'Session expired. Please log in again.', undefined, requestId);
    }
  }

  if (response.status === 204) {
    return null as unknown as T;
  }

  if (!response.ok) {
    let errorBody: { error?: { code?: string; message?: string; details?: Record<string, unknown> } } = {};
    try {
      errorBody = await response.json();
    } catch {
      // If server returned plain text or proxy 413 HTML
      if (response.status === 413) {
        throw new ApiError(413, 'payload_too_large', 'File is too large.', undefined, requestId);
      }
      throw new ApiError(response.status, 'unexpected_error', `HTTP ${response.status}: ${response.statusText}`, undefined, requestId);
    }

    const error = errorBody.error || {
      code: 'unexpected_error',
      message: response.statusText || 'An unexpected error occurred.',
    };

    throw new ApiError(
      response.status,
      error.code || 'unexpected_error',
      error.message || 'An unexpected error occurred.',
      error.details,
      requestId
    );
  }

  // Parse JSON response
  try {
    return (await response.json()) as T;
  } catch {
    return null as unknown as T;
  }
}
