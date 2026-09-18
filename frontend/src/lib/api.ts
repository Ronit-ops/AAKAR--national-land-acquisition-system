import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types/auth';
import type { UserRolesResponse } from '../types/rbac';

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1';

const ACCESS_TOKEN_KEY = 'aakar_access_token';

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

function setAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken();

  const headers = new Headers(options.headers);
  headers.set('Content-Type', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = 'Something went wrong. Please try again.';

    try {
      const errorBody = (await response.json()) as {
        detail?: string;
      };

      if (typeof errorBody.detail === 'string') {
        message = errorBody.detail;
      }
    } catch {
      // Keep the default message when the server does not return JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function registerUser(
  payload: RegisterRequest,
): Promise<User> {
  return request<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function loginUser(
  payload: LoginRequest,
): Promise<LoginResponse> {
  const response = await request<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

  setAccessToken(response.access_token);

  return response;
}

export async function getCurrentUser(): Promise<User> {
  return request<User>('/auth/me');
}

export async function getMyRoles(): Promise<UserRolesResponse> {
  return request<UserRolesResponse>('/rbac/me');
}