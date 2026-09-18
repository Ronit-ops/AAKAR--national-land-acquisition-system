import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types/auth';
import type { UserRolesResponse } from '../types/rbac';
import type {
  CreateManagedUserRequest,
  ManagedUser,
  ManagedUserDetail,
  UpdateManagedUserRequest,
  UpdateUserStatusRequest,
  UserListResponse,
} from '../types/users';

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

  if (response.status === 204) {
    return undefined as T;
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

export async function listManagedUsers(
  params: {
    search?: string;
    is_active?: boolean;
    offset?: number;
    limit?: number;
  } = {},
): Promise<UserListResponse> {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.is_active !== undefined) {
    searchParams.set('is_active', String(params.is_active));
  }

  if (params.offset !== undefined) {
    searchParams.set('offset', String(params.offset));
  }

  if (params.limit !== undefined) {
    searchParams.set('limit', String(params.limit));
  }

  const query = searchParams.toString();

  return request<UserListResponse>(
    `/users${query ? `?${query}` : ''}`,
  );
}

export async function getManagedUser(
  userId: string,
): Promise<ManagedUserDetail> {
  return request<ManagedUserDetail>(`/users/${userId}`);
}

export async function createManagedUser(
  payload: CreateManagedUserRequest,
): Promise<ManagedUser> {
  return request<ManagedUser>('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateManagedUser(
  userId: string,
  payload: UpdateManagedUserRequest,
): Promise<ManagedUser> {
  return request<ManagedUser>(`/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function updateManagedUserStatus(
  userId: string,
  payload: UpdateUserStatusRequest,
): Promise<ManagedUser> {
  return request<ManagedUser>(`/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}