import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
} from '../types/auth';
import type { Role, UserRolesResponse } from '../types/rbac';
import type {
  CreateManagedUserRequest,
  ManagedUser,
  ManagedUserDetail,
  UpdateManagedUserRequest,
  UpdateUserStatusRequest,
  UserListResponse,
} from '../types/users';
import type {
  Authority,
  AuthorityListResponse,
  CreateAuthorityRequest,
  CreateDepartmentRequest,
  Department,
  DepartmentListResponse,
  UpdateAuthorityRequest,
  UpdateAuthorityStatusRequest,
  UpdateDepartmentRequest,
  UpdateDepartmentStatusRequest,
  UpdateUserOrganizationRequest,
} from '../types/organization';
import type {
  CreatePermissionRequest,
  Permission,
  PermissionListResponse,
  RolePermissionAssignment,
  RolePermissionAssignmentRequest,
  UpdatePermissionRequest,
  UpdatePermissionStatusRequest,
} from '../types/permissions';
import type {
  AuditEvent,
  AuditEventListResponse,
} from '../types/audit';

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

export async function listRoles(): Promise<Role[]> {
  return request<Role[]>('/rbac/roles');
}

/* -------------------------------------------------------------------------- */
/* User Management                                                           */
/* -------------------------------------------------------------------------- */

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

export async function updateManagedUserOrganization(
  userId: string,
  payload: UpdateUserOrganizationRequest,
): Promise<ManagedUser> {
  return request<ManagedUser>(`/users/${userId}/organization`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------- */
/* Department Management                                                     */
/* -------------------------------------------------------------------------- */

export async function listDepartments(
  params: {
    search?: string;
    is_active?: boolean;
    offset?: number;
    limit?: number;
  } = {},
): Promise<DepartmentListResponse> {
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

  return request<DepartmentListResponse>(
    `/departments${query ? `?${query}` : ''}`,
  );
}

export async function getDepartment(
  departmentId: string,
): Promise<Department> {
  return request<Department>(`/departments/${departmentId}`);
}

export async function createDepartment(
  payload: CreateDepartmentRequest,
): Promise<Department> {
  return request<Department>('/departments', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateDepartment(
  departmentId: string,
  payload: UpdateDepartmentRequest,
): Promise<Department> {
  return request<Department>(`/departments/${departmentId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function updateDepartmentStatus(
  departmentId: string,
  payload: UpdateDepartmentStatusRequest,
): Promise<Department> {
  return request<Department>(`/departments/${departmentId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------- */
/* Authority Management                                                      */
/* -------------------------------------------------------------------------- */

export async function listAuthorities(
  params: {
    search?: string;
    department_id?: string;
    authority_type?: string;
    is_active?: boolean;
    offset?: number;
    limit?: number;
  } = {},
): Promise<AuthorityListResponse> {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.department_id) {
    searchParams.set('department_id', params.department_id);
  }

  if (params.authority_type) {
    searchParams.set('authority_type', params.authority_type);
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

  return request<AuthorityListResponse>(
    `/authorities${query ? `?${query}` : ''}`,
  );
}

export async function getAuthority(
  authorityId: string,
): Promise<Authority> {
  return request<Authority>(`/authorities/${authorityId}`);
}

export async function createAuthority(
  payload: CreateAuthorityRequest,
): Promise<Authority> {
  return request<Authority>('/authorities', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAuthority(
  authorityId: string,
  payload: UpdateAuthorityRequest,
): Promise<Authority> {
  return request<Authority>(`/authorities/${authorityId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function updateAuthorityStatus(
  authorityId: string,
  payload: UpdateAuthorityStatusRequest,
): Promise<Authority> {
  return request<Authority>(`/authorities/${authorityId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

/* -------------------------------------------------------------------------- */
/* Permission Management                                                     */
/* -------------------------------------------------------------------------- */

export async function listPermissions(
  params: {
    search?: string;
    resource?: string;
    action?: string;
    is_active?: boolean;
    offset?: number;
    limit?: number;
  } = {},
): Promise<PermissionListResponse> {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.resource) {
    searchParams.set('resource', params.resource);
  }

  if (params.action) {
    searchParams.set('action', params.action);
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

  return request<PermissionListResponse>(
    `/permissions${query ? `?${query}` : ''}`,
  );
}

export async function getPermission(
  permissionId: string,
): Promise<Permission> {
  return request<Permission>(`/permissions/${permissionId}`);
}

export async function createPermission(
  payload: CreatePermissionRequest,
): Promise<Permission> {
  return request<Permission>('/permissions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updatePermission(
  permissionId: string,
  payload: UpdatePermissionRequest,
): Promise<Permission> {
  return request<Permission>(`/permissions/${permissionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function updatePermissionStatus(
  permissionId: string,
  payload: UpdatePermissionStatusRequest,
): Promise<Permission> {
  return request<Permission>(`/permissions/${permissionId}/status`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function listRolePermissions(
  roleCode: string,
): Promise<RolePermissionAssignment[]> {
  return request<RolePermissionAssignment[]>(
    `/permissions/roles/${encodeURIComponent(roleCode)}`,
  );
}

export async function assignPermissionToRole(
  roleCode: string,
  payload: RolePermissionAssignmentRequest,
): Promise<RolePermissionAssignment> {
  return request<RolePermissionAssignment>(
    `/permissions/roles/${encodeURIComponent(roleCode)}/assign`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  );
}

export async function removePermissionFromRole(
  roleCode: string,
  permissionCode: string,
): Promise<void> {
  await request<void>(
    `/permissions/roles/${encodeURIComponent(
      roleCode,
    )}/assign/${encodeURIComponent(permissionCode)}`,
    {
      method: 'DELETE',
    },
  );
}

/* -------------------------------------------------------------------------- */
/* Audit & Activity History                                                  */
/* -------------------------------------------------------------------------- */

export async function listAuditEvents(
  params: {
    search?: string;
    actor_user_id?: string;
    action?: string;
    entity_type?: string;
    entity_id?: string;
    result?: string;
    start_at?: string;
    end_at?: string;
    offset?: number;
    limit?: number;
  } = {},
): Promise<AuditEventListResponse> {
  const searchParams = new URLSearchParams();

  if (params.search) {
    searchParams.set('search', params.search);
  }

  if (params.actor_user_id) {
    searchParams.set('actor_user_id', params.actor_user_id);
  }

  if (params.action) {
    searchParams.set('action', params.action);
  }

  if (params.entity_type) {
    searchParams.set('entity_type', params.entity_type);
  }

  if (params.entity_id) {
    searchParams.set('entity_id', params.entity_id);
  }

  if (params.result) {
    searchParams.set('result', params.result);
  }

  if (params.start_at) {
    searchParams.set('start_at', params.start_at);
  }

  if (params.end_at) {
    searchParams.set('end_at', params.end_at);
  }

  if (params.offset !== undefined) {
    searchParams.set('offset', String(params.offset));
  }

  if (params.limit !== undefined) {
    searchParams.set('limit', String(params.limit));
  }

  const query = searchParams.toString();

  return request<AuditEventListResponse>(
    `/audit${query ? `?${query}` : ''}`,
  );
}

export async function getAuditEvent(
  eventId: string,
): Promise<AuditEvent> {
  return request<AuditEvent>(`/audit/${eventId}`);
}