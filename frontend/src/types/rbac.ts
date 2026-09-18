export interface Role {
  id: string;
  code: string;
  name: string;
  scope_level: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserRolesResponse {
  user_id: string;
  roles: Role[];
}