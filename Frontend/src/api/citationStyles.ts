import { apiClient } from './client';
import {
  CitationStyle,
  CreateCitationStyleRequest,
  UpdateCitationStyleRequest,
  ValidateTemplateResponse,
} from '@/types/api';

export async function listCitationStyles(): Promise<CitationStyle[]> {
  return apiClient<CitationStyle[]>('/citation-styles', {
    method: 'GET',
  });
}

export async function getCitationStyleFields(): Promise<string[]> {
  const res = await apiClient<{ fields: string[] }>('/citation-styles/fields', {
    method: 'GET',
  });
  return res.fields;
}

export async function validateCitationTemplate(template: string): Promise<ValidateTemplateResponse> {
  return apiClient<ValidateTemplateResponse>('/citation-styles/validate', {
    method: 'POST',
    body: JSON.stringify({ template }),
  });
}

export async function getCitationStyle(id: string): Promise<CitationStyle> {
  return apiClient<CitationStyle>(`/citation-styles/${id}`, {
    method: 'GET',
  });
}

export async function createCitationStyle(data: CreateCitationStyleRequest): Promise<CitationStyle> {
  return apiClient<CitationStyle>('/citation-styles', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCitationStyle(
  id: string,
  data: UpdateCitationStyleRequest
): Promise<CitationStyle> {
  return apiClient<CitationStyle>(`/citation-styles/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCitationStyle(id: string): Promise<void> {
  await apiClient<void>(`/citation-styles/${id}`, {
    method: 'DELETE',
  });
}

