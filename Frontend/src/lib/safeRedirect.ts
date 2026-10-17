/**
 * Validates a redirect target URL to prevent open-redirect vulnerabilities.
 * Only accepts safe relative paths starting with a single '/' (not '//', not URLs with schemes).
 */
export function getSafeRedirectPath(rawPath: string | null | undefined): string {
  if (!rawPath) return '/';

  const trimmed = rawPath.trim();

  // Must start with exactly one forward slash, not two (protocol-relative //evil.com)
  if (!trimmed.startsWith('/') || trimmed.startsWith('//')) {
    return '/';
  }

  // Reject backslashes or encoded slashes that can confuse browsers
  if (trimmed.includes('\\') || trimmed.includes('%2f') || trimmed.includes('%2F') || trimmed.includes('%5c')) {
    return '/';
  }

  // Reject javascript:, data:, or any colon schemes
  if (trimmed.includes(':')) {
    return '/';
  }

  return trimmed;
}
