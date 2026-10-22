let inMemoryCsrfToken: string | null = null;

/**
 * Stores the CSRF token in memory and sessionStorage.
 * This is crucial for cross-domain SPA deployments (e.g., Vercel + Render)
 * where document.cookie cannot read cross-site cookies.
 */
export function setCsrfToken(token: string | null): void {
  inMemoryCsrfToken = token;
  if (token && typeof sessionStorage !== 'undefined') {
    try {
      sessionStorage.setItem('citeflow_csrf_token', token);
    } catch {
      // Ignore storage errors (private browsing, quota)
    }
  }
}

/**
 * Retrieves the current CSRF token from memory, sessionStorage, or document.cookie.
 */
export function getCsrfToken(): string | null {
  if (inMemoryCsrfToken) {
    return inMemoryCsrfToken;
  }

  if (typeof sessionStorage !== 'undefined') {
    try {
      const stored = sessionStorage.getItem('citeflow_csrf_token');
      if (stored) {
        inMemoryCsrfToken = stored;
        return stored;
      }
    } catch {
      // Ignore storage errors
    }
  }

  if (typeof document !== 'undefined') {
    const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
    if (match) {
      const val = decodeURIComponent(match[1]);
      inMemoryCsrfToken = val;
      return val;
    }
  }

  return null;
}
