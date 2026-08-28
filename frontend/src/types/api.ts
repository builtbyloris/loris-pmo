export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}
