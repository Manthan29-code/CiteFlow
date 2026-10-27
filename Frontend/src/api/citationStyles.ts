import { apiClient } from './client';

export interface CitationStyle {
  id: string;
  style_name: string;
  description: string | null;
  sample_string: string;
  formatting_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CitationStyleListResponse {
  items: CitationStyle[];
  next_cursor: string | null;
}

export interface CitationStylePayload {
  style_name: string;
  description?: string | null;
  sample_string: string;
}

export interface CitationTransformResponse {
  reformatted_citation: string;
  diff_summary: Record<string, unknown> | null;
}

export interface ListCitationStylesParams {
  q?: string;
  limit?: number;
  cursor?: string;
}

export async function listCitationStyles(
  params: ListCitationStylesParams = {}
): Promise<CitationStyleListResponse> {
  const query = new URLSearchParams();
  if (params.q?.trim()) query.set('q', params.q.trim());
  if (params.limit) query.set('limit', String(params.limit));
  if (params.cursor) query.set('cursor', params.cursor);
  const suffix = query.toString() ? '?' + query.toString() : '';
  return apiClient<CitationStyleListResponse>('/styles' + suffix);
}

export async function createCitationStyle(payload: CitationStylePayload): Promise<CitationStyle> {
  return apiClient<CitationStyle>('/styles', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateCitationStyle(
  styleId: string,
  payload: Partial<CitationStylePayload>
): Promise<CitationStyle> {
  return apiClient<CitationStyle>('/styles/' + styleId, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteCitationStyle(styleId: string): Promise<void> {
  await apiClient<void>('/styles/' + styleId, { method: 'DELETE' });
}

export async function transformCitation(
  styleId: string,
  sourceCitation: string
): Promise<CitationTransformResponse> {
  return apiClient<CitationTransformResponse>('/styles/' + styleId + '/transform', {
    method: 'POST',
    body: JSON.stringify({ source_citation: sourceCitation }),
  });
}
