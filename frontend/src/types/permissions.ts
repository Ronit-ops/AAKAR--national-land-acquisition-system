export interface Permission {
  id: string;
  code: string;
  name: string;
  resource: string;
  action: string;
  description: string | null;
  is_system_permission: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PermissionListResponse {
  items: Permission[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreatePermissionRequest {
  code: string;
  name: string;
  resource: string;
  action: string;
  description?: string | null;
}

export interface UpdatePermissionRequest {
  code: string;
  name: string;
  resource: string;
  action: string;
  description?: string | null;
}

export interface UpdatePermissionStatusRequest {
  is_active: boolean;
}

export interface RolePermissionAssignmentRequest {
  permission_code: string;
}

export interface RolePermissionAssignment {
  role_id: string;
  permission_id: string;
  role_code: string;
  permission_code: string;
  assigned_at: string;
}