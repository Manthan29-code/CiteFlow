// Schema definitions derived from api_doc.md

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
}

export interface Breadcrumb {
  id: string;
  name: string;
}

export interface FileItem {
  id: string;
  name: string;
  ext: string;
  size_bytes: number;
  folder_id?: string;
  created_at: string;
}

export interface FolderDetailResponse {
  folder: Folder;
  breadcrumbs: Breadcrumb[];
  folders: Folder[];
  files: FileItem[];
  next_cursor: string | number | null;
}

export interface CreateFolderRequest {
  name: string;
  parent_id: string;
}

export interface SignedUrlResponse {
  url: string;
  expires_in: number;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export type UploadStatus = 'queued' | 'uploading' | 'done' | 'error' | 'canceled';

export interface UploadQueueItem {
  id: string;
  file: File;
  name: string;
  sizeBytes: number;
  folderId: string;
  folderName: string;
  progress: number;
  status: UploadStatus;
  errorMessage?: string;
}

// ==========================================
// Part B: Citation Jobs & Interrupt Schemas
// ==========================================

export type TexMode = 'standalone' | 'fragment';

export type JobStatus =
  | 'queued'
  | 'running'
  | 'needs_title_confirmation'
  | 'needs_review'
  | 'succeeded'
  | 'unresolved'
  | 'failed'
  | 'canceled'
  | 'expired';

export interface ConfirmTitleCandidate {
  index?: number;
  title?: string;
  text?: string;
  score?: number;
  source?: string;
  confidence?: 'low' | 'medium' | 'high';
}

export interface ConfirmTitleInterrupt {
  kind: 'confirm_title';
  candidates: ConfirmTitleCandidate[];
}

export interface ReviewAuthor {
  surname?: string;
  given_name?: string;
  middle_name?: string;
  name?: string;
}

export interface ReviewConflict {
  field: string;
  values?: Array<{ source: string; value: unknown }>;
  crossref_val?: unknown;
  openalex_val?: unknown;
}

export interface ReviewFieldItem {
  name: string;
  value: unknown;
  source: string | null;
  warning?: string;
}

export interface ReviewInterrupt {
  kind: 'user_review';
  record?: Record<string, unknown>;
  fields?: ReviewFieldItem[];
  conflicts?: ReviewConflict[];
  warnings?: string[];
}

export type JobInterrupt = ConfirmTitleInterrupt | ReviewInterrupt | Record<string, unknown>;

export interface JobResponse {
  id: string;
  owner_id: string;
  file_id: string;
  status: JobStatus;
  tex_mode: TexMode;
  pending_interrupt?: JobInterrupt | null;
  result_metadata?: Record<string, unknown> | null;
  reasons?: string[] | null;
  error_code?: string | null;
  created_at: string;
  updated_at: string;
  finished_at?: string | null;
}

export interface JobListResponse {
  items: JobResponse[];
  next_cursor?: string | null;
}

export type ResumeAction = 'select' | 'custom' | 'accept' | 'edit' | 'skip';

export interface ResumeRequest {
  action: ResumeAction;
  index?: number;
  title?: string;
  edits?: Record<string, unknown>;
}
