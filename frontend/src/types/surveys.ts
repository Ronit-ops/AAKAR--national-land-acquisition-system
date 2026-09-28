export const SURVEY_TYPES = [
  "PRELIMINARY",
  "JOINT_MEASUREMENT",
  "BOUNDARY_VERIFICATION",
  "RE_MEASUREMENT",
  "OTHER",
] as const;

export const SURVEY_METHODS = [
  "FIELD_SURVEY",
  "GNSS",
  "TOTAL_STATION",
  "GPS",
  "DIGITIZED",
  "OTHER",
] as const;

export const SURVEY_STATUSES = [
  "PLANNED",
  "IN_PROGRESS",
  "COMPLETED",
  "REQUIRES_REVIEW",
  "VERIFIED",
  "CANCELLED",
] as const;

export type SurveyType = (typeof SURVEY_TYPES)[number];
export type SurveyMethod = (typeof SURVEY_METHODS)[number];
export type SurveyStatus = (typeof SURVEY_STATUSES)[number];

export interface SurveyRecord {
  id: string;
  acquisition_case_id: string;
  parcel_id: string;
  survey_reference: string;
  survey_type: SurveyType | string;
  survey_method: SurveyMethod | string;
  status: SurveyStatus | string;

  scheduled_at: string | null;
  conducted_at: string | null;

  surveyor_user_id: string | null;
  verified_by_user_id: string | null;
  verified_at: string | null;

  recorded_area_sq_m: string;
  measured_area_sq_m: string | null;
  area_difference_sq_m: string | null;
  area_difference_percentage: string | null;

  notes: string | null;

  created_at: string;
  updated_at: string;
}

export interface SurveyRecordListResponse {
  items: SurveyRecord[];
  total: number;
  offset: number;
  limit: number;
}

export interface SurveyRecordCreateRequest {
  acquisition_case_id: string;
  parcel_id: string;
  survey_reference: string;
  survey_type: string;
  survey_method: string;
  scheduled_at?: string | null;
  surveyor_user_id?: string | null;
  recorded_area_sq_m: string;
  notes?: string | null;
}

export interface SurveyRecordCompleteRequest {
  measured_area_sq_m: string;
  conducted_at?: string | null;
}