import { env } from '@/lib/env';
import { apiClient } from './client';
import { JobResponse, JobListResponse, ResumeRequest, TexMode } from '@/types/api';

export async function createJob(fileId: string, texMode: TexMode = 'standalone'): Promise<JobResponse> {
  return apiClient<JobResponse>(`/files/${fileId}/jobs`, {
    method: 'POST',
    body: JSON.stringify({ tex_mode: texMode }),
  });
}

export async function getJobDetail(jobId: string): Promise<JobResponse> {
  return apiClient<JobResponse>(`/jobs/${jobId}`, {
    method: 'GET',
  });
}

export interface ListJobsParams {
  fileId?: string;
  limit?: number;
  cursor?: string;
}

export async function listJobs(params: ListJobsParams = {}): Promise<JobListResponse> {
  const query = new URLSearchParams();
  if (params.fileId) query.set('file_id', params.fileId);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.cursor) query.set('cursor', params.cursor);

  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiClient<JobListResponse>(`/jobs${qs}`);
}

export async function resumeJob(jobId: string, payload: ResumeRequest): Promise<JobResponse> {
  return apiClient<JobResponse>(`/jobs/${jobId}/resume`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function cancelJob(jobId: string): Promise<JobResponse> {
  return apiClient<JobResponse>(`/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
}

export async function downloadJobTex(jobId: string): Promise<string> {
  const url = `${env.VITE_API_BASE_URL}/jobs/${jobId}/tex`;
  const res = await fetch(url, {
    method: 'GET',
    credentials: 'include',
  });

  if (!res.ok) {
    throw new Error(`Failed to download .tex: HTTP ${res.status}`);
  }

  return res.text();
}

/**
 * Connect to SSE real-time updates for a job.
 * Closes stream on terminal state and returns unsubscribe callback.
 */
export function streamJobEvents(
  jobId: string,
  onUpdate: (data: JobResponse) => void,
  onError?: () => void
): () => void {
  const url = `${env.VITE_API_BASE_URL}/jobs/${jobId}/events`;
  const eventSource = new EventSource(url, { withCredentials: true });

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as JobResponse;
      onUpdate(data);

      const terminalStatuses = ['succeeded', 'unresolved', 'failed', 'canceled', 'expired'];
      if (terminalStatuses.includes(data.status)) {
        eventSource.close();
      }
    } catch {
      // ignore parse error on heartbeat comments
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    if (onError) onError();
  };

  return () => {
    eventSource.close();
  };
}
