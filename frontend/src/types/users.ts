import type { Role } from './rbac';

export interface ManagedUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_email_verified: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ManagedUserDetail extends ManagedUser {
  roles: Role[];
}

export interface UserListResponse {
  items: ManagedUser[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateManagedUserRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface UpdateManagedUserRequest {
  email: string;
  full_name: string;
}

export interface UpdateUserStatusRequest {
  is_active: boolean;
}