export type AuthorityType =
  | 'CENTRAL'
  | 'STATE'
  | 'DISTRICT'
  | 'OTHER';

export interface Department {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DepartmentListResponse {
  items: Department[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateDepartmentRequest {
  code: string;
  name: string;
  description?: string | null;
}

export interface UpdateDepartmentRequest {
  code: string;
  name: string;
  description?: string | null;
}

export interface UpdateDepartmentStatusRequest {
  is_active: boolean;
}

export interface Authority {
  id: string;
  department_id: string;
  code: string;
  name: string;
  authority_type: AuthorityType;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthorityListResponse {
  items: Authority[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateAuthorityRequest {
  department_id: string;
  code: string;
  name: string;
  authority_type: AuthorityType;
  description?: string | null;
}

export interface UpdateAuthorityRequest {
  department_id: string;
  code: string;
  name: string;
  authority_type: AuthorityType;
  description?: string | null;
}

export interface UpdateAuthorityStatusRequest {
  is_active: boolean;
}

export interface UpdateUserOrganizationRequest {
  department_id: string | null;
  authority_id: string | null;
}