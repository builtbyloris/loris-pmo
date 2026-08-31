export interface User {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}
