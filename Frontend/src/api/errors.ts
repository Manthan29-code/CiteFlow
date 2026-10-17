export class ApiError extends Error {
  public status: number;
  public code: string;
  public details?: Record<string, unknown>;
  public requestId?: string | null;

  constructor(
    status: number,
    code: string,
    message: string,
    details?: Record<string, unknown>,
    requestId?: string | null
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

export const ERROR_MESSAGES: Record<string, string> = {
  invalid_credentials: 'Email or password is incorrect.',
  registration_disabled: 'Registration is currently closed.',
  rate_limited: 'Too many attempts. Please wait before trying again.',
  csrf_failed: 'Your session expired. Please reload the page and try again.',
  name_conflict: 'An item with this name already exists here.',
  folder_too_deep: "Folders can't be nested this deeply.",
  root_folder_protected: "The top-level folder can't be deleted.",
  payload_too_large: 'This file exceeds the maximum upload size limit.',
  unsupported_type: 'Only PDF files can be uploaded.',
  invalid_file: 'This file is damaged, encrypted, or not a valid PDF.',
  quota_exceeded: "You've reached your storage limit. Delete some files first.",
  network_error: "Can't reach the server. Check your connection and try again.",
  file_not_found: 'File not found.',
  not_found: 'The requested resource could not be found.',
  token_revoked: 'Your session has expired. Please log in again.',
  internal_error: 'An internal server error occurred.',
  database_unavailable: 'Database is currently unavailable. Please try again shortly.',
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (ERROR_MESSAGES[error.code]) {
      return ERROR_MESSAGES[error.code];
    }
    if (error.message) {
      return error.message;
    }
    return `An error occurred (${error.code})${error.requestId ? ` [Ref: ${error.requestId}]` : ''}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
}
