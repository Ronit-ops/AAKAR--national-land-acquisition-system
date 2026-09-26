export type AcquisitionCaseLegalFramework =
  | 'RFCTLARR_2013'
  | 'SPECIAL_CENTRAL_ACT'
  | 'STATE_LAW'
  | 'OTHER';

export type AcquisitionCaseLegalRoute =
  | 'RFCTLARR_STANDARD'
  | 'RFCTLARR_URGENT'
  | 'SPECIAL_ACT_ROUTE'
  | 'STATE_SPECIFIC_ROUTE'
  | 'NEGOTIATED_PURCHASE';

export type AcquisitionCaseAcquisitionMethod =
  | 'COMPULSORY_ACQUISITION'
  | 'CONSENT_BASED'
  | 'NEGOTIATED_PURCHASE';

export type AcquisitionCaseStatus =
  | 'DRAFT'
  | 'ACTIVE'
  | 'ON_HOLD'
  | 'CANCELLED'
  | 'CLOSED';

export type AcquisitionCaseStage =
  | 'INITIATION'
  | 'SIA'
  | 'PRELIMINARY_NOTIFICATION'
  | 'OBJECTIONS_AND_HEARING'
  | 'DECLARATION'
  | 'R_AND_R'
  | 'CLAIMS_AND_ENQUIRY'
  | 'COMPENSATION_DETERMINATION'
  | 'AWARD'
  | 'COMPENSATION_AND_RR'
  | 'POSSESSION'
  | 'VESTING'
  | 'HANDOVER';

export interface AcquisitionCase {
  id: string;

  land_requirement_id: string;

  case_number: string;

  legal_framework: AcquisitionCaseLegalFramework;

  legal_route: AcquisitionCaseLegalRoute | null;

  acquisition_method: AcquisitionCaseAcquisitionMethod;

  responsible_authority_id: string | null;

  assigned_user_id: string | null;

  status: AcquisitionCaseStatus;

  current_stage: AcquisitionCaseStage;

  description: string | null;

  opened_at: string | null;

  closed_at: string | null;

  version: number;

  created_at: string;

  updated_at: string;
}

export interface AcquisitionCaseListResponse {
  items: AcquisitionCase[];

  total: number;

  offset: number;

  limit: number;
}

export interface CreateAcquisitionCaseRequest {
  land_requirement_id: string;

  case_number: string;

  legal_framework?: AcquisitionCaseLegalFramework;

  legal_route?: AcquisitionCaseLegalRoute | null;

  acquisition_method?: AcquisitionCaseAcquisitionMethod;

  responsible_authority_id?: string | null;

  assigned_user_id?: string | null;

  description?: string | null;
}

export interface UpdateAcquisitionCaseRequest {
  expected_version: number;

  legal_framework?: AcquisitionCaseLegalFramework;

  legal_route?: AcquisitionCaseLegalRoute | null;

  acquisition_method?: AcquisitionCaseAcquisitionMethod;

  responsible_authority_id?: string | null;

  assigned_user_id?: string | null;

  description?: string | null;
}

export interface AcquisitionCaseActivateRequest {
  expected_version: number;
}

export interface AcquisitionCaseHoldRequest {
  expected_version: number;

  reason: string;
}

export interface AcquisitionCaseResumeRequest {
  expected_version: number;
}

export interface AcquisitionCaseCancelRequest {
  expected_version: number;

  reason: string;
}

export interface AcquisitionCaseCloseRequest {
  expected_version: number;
}

export interface AcquisitionCaseStageTransitionRequest {
  to_stage: AcquisitionCaseStage;

  reason?: string | null;

  expected_version: number;
}

export interface AcquisitionCaseStageHistory {
  id: string;

  acquisition_case_id: string;

  from_stage: AcquisitionCaseStage | null;

  to_stage: AcquisitionCaseStage;

  reason: string | null;

  changed_by_user_id: string | null;

  changed_at: string;
}