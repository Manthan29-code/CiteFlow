/**
 * Format bytes into human-readable string (e.g. 1.2 MB)
 */
export function formatBytes(bytes: number, decimals = 1): string {
  if (bytes === 0) return '0 B';
  if (!bytes || bytes < 0) return '-';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const idx = Math.min(i, sizes.length - 1);

  return `${parseFloat((bytes / Math.pow(k, idx)).toFixed(dm))} ${sizes[idx]}`;
}

/**
 * Format ISO date string into readable date (e.g. Oct 17, 2026)
 */
export function formatDate(isoString: string): string {
  if (!isoString) return '-';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return '-';
  }
}

/**
 * Validates folder name according to Citegen rules:
 * - NFC normalized
 * - 1 to 120 characters
 * - No slashes (/ or \)
 * - No NUL or control characters
 * - Cannot be '.' or '..'
 * - No trailing dot or space
 */
export function validateFolderName(name: string): { isValid: boolean; error?: string; normalized: string } {
  const normalized = name.normalize('NFC').trim();

  if (!normalized) {
    return { isValid: false, error: 'Folder name cannot be empty', normalized };
  }

  if (normalized.length > 120) {
    return { isValid: false, error: 'Folder name cannot exceed 120 characters', normalized };
  }

  if (normalized === '.' || normalized === '..') {
    return { isValid: false, error: 'Folder name cannot be "." or ".."', normalized };
  }

  if (normalized.endsWith('.') || normalized.endsWith(' ')) {
    return { isValid: false, error: 'Folder name cannot end with a dot or space', normalized };
  }

  // eslint-disable-next-line no-control-regex
  if (/[/\\:\0\x00-\x1F\x7F]/.test(normalized)) {
    return { isValid: false, error: 'Folder name contains invalid characters (/ \\ : or control characters)', normalized };
  }

  return { isValid: true, normalized };
}
