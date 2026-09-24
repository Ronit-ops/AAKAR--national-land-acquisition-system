export type LandRequirementStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'APPROVED'
  | 'REJECTED'
  | 'WITHDRAWN';

export interface LandRequirement {
  id: string;
  project_id: string;
  requirement_reference: string;
  purpose: string;
  required_area_sq_m: string;
  state: string;
  district: string;
  taluka: string | null;
  village: string | null;
  description: string | null;
  status: LandRequirementStatus;
  created_at: string;
  updated_at: string;
}

export interface LandRequirementListResponse {
  items: LandRequirement[];
  total: number;
  offset: number;
  limit: number;
}

export interface CreateLandRequirementRequest {
  project_id: string;
  requirement_reference: string;
  purpose: string;
  required_area_sq_m: number;
  state: string;
  district: string;
  taluka?: string | null;
  village?: string | null;
  description?: string | null;
}

export interface UpdateLandRequirementRequest {
  requirement_reference: string;
  purpose: string;
  required_area_sq_m: number;
  state: string;
  district: string;
  taluka?: string | null;
  village?: string | null;
  description?: string | null;
}

export interface LandRequirementStatusResponse {
  id: string;
  status: LandRequirementStatus;
}

export interface LandRequirementActionRequest {
  reason?: string | null;
}