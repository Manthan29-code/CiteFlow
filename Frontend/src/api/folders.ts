import { apiClient } from './client';
import { Folder, FolderDetailResponse, CreateFolderRequest } from '@/types/api';

export interface FolderQueryParams {
  limit?: number;
  cursor?: string | number | null;
}

export async function getRootFolder(params: FolderQueryParams = {}): Promise<FolderDetailResponse> {
  const query = new URLSearchParams();
  if (params.limit) query.set('limit', String(params.limit));
  if (params.cursor) query.set('cursor', String(params.cursor));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiClient<FolderDetailResponse>(`/folders/root${qs}`);
}

export async function getFolderDetails(folderId: string, params: FolderQueryParams = {}): Promise<FolderDetailResponse> {
  const query = new URLSearchParams();
  if (params.limit) query.set('limit', String(params.limit));
  if (params.cursor) query.set('cursor', String(params.cursor));

  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiClient<FolderDetailResponse>(`/folders/${folderId}${qs}`);
}

export async function createFolder(payload: CreateFolderRequest): Promise<Folder> {
  return apiClient<Folder>('/folders', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteFolder(folderId: string): Promise<void> {
  return apiClient<void>(`/folders/${folderId}`, {
    method: 'DELETE',
  });
}
