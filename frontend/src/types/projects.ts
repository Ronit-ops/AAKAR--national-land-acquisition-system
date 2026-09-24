export type ProjectStatus = 'DRAFT' | 'ACTIVE' | 'CLOSED';

export interface ProjectBoundary {
  type: 'Polygon' | 'MultiPolygon';
  coordinates: number[][][] | number[][][][];
}

export interface Project {
  id: string;
  code: string;
  name: string;
  sector: string;
  description: string | null;
  responsible_authority_id: string;
  boundary: ProjectBoundary | null;
  status: ProjectStatus;
  created_by_user_id: string;
  updated_by_user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateProjectRequest {
  code: string;
  name: string;
  sector: string;
  description?: string | null;
  responsible_authority_id: string;
  boundary?: ProjectBoundary | null;
}

export interface UpdateProjectRequest {
  code: string;
  name: string;
  sector: string;
  description?: string | null;
  responsible_authority_id: string;
  boundary?: ProjectBoundary | null;
}

export interface ProjectStatusResponse {
  id: string;
  status: ProjectStatus;
}