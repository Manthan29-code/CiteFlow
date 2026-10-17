import { env } from '@/lib/env';
import { apiClient } from './client';
import { getCsrfToken } from './csrf';
import { ApiError } from './errors';
import { FileItem, SignedUrlResponse } from '@/types/api';

export async function getFileDetails(fileId: string): Promise<FileItem> {
  return apiClient<FileItem>(`/files/${fileId}`, {
    method: 'GET',
  });
}

export async function getSignedUrl(fileId: string): Promise<SignedUrlResponse> {
  return apiClient<SignedUrlResponse>(`/files/${fileId}/url`, {
    method: 'GET',
  });
}

export async function deleteFile(fileId: string): Promise<void> {
  return apiClient<void>(`/files/${fileId}`, {
    method: 'DELETE',
  });
}

/**
 * Uploads a file via XMLHttpRequest to track upload progress percentages accurately.
 * Sets withCredentials = true and attaches X-CSRF-Token.
 */
export function uploadFileWithProgress(
  file: File,
  folderId: string,
  onProgress: (percentage: number) => void,
  onAbortRef?: { abort?: () => void }
): Promise<FileItem> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    if (onAbortRef) {
      onAbortRef.abort = () => {
        xhr.abort();
      };
    }

    const url = `${env.VITE_API_BASE_URL}/files`;
    xhr.open('POST', url, true);
    xhr.withCredentials = true;

    // Attach CSRF Token
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      xhr.setRequestHeader('X-CSRF-Token', csrfToken);
    }

    // Monitor upload progress
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percentComplete = Math.min(100, Math.round((event.loaded / event.total) * 100));
        onProgress(percentComplete);
      }
    };

    xhr.onload = () => {
      const requestId = xhr.getResponseHeader('X-Request-ID');
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as FileItem;
          onProgress(100);
          resolve(data);
        } catch {
          reject(new ApiError(xhr.status, 'parse_error', 'Invalid JSON from server.', undefined, requestId));
        }
      } else {
        let code = 'upload_failed';
        let message = xhr.statusText || 'Upload failed.';
        let details: Record<string, unknown> | undefined;

        if (xhr.status === 413) {
          code = 'payload_too_large';
          message = `File exceeds upload limit of ${env.VITE_MAX_UPLOAD_MB} MB.`;
        }

        try {
          const body = JSON.parse(xhr.responseText);
          if (body?.error) {
            code = body.error.code || code;
            message = body.error.message || message;
            details = body.error.details;
          }
        } catch {
          // non-JSON error
        }

        reject(new ApiError(xhr.status, code, message, details, requestId));
      }
    };

    xhr.onerror = () => {
      reject(new ApiError(0, 'network_error', 'Network error during upload.'));
    };

    xhr.onabort = () => {
      reject(new ApiError(0, 'canceled', 'Upload canceled by user.'));
    };

    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder_id', folderId);

    xhr.send(formData);
  });
}
