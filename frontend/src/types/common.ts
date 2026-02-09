/** 共通型定義 */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ErrorResponse {
  detail: string;
  error_code?: string;
  field_errors?: Record<string, string[]>;
}
