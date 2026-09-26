export type Parcel = {
  id: string;

  parcel_reference: string;

  state: string;
  district: string;
  taluka: string | null;
  village: string | null;

  survey_number: string;
  subdivision_number: string | null;

  recorded_area_sq_m: string;
  surveyed_area_sq_m: string | null;
  acquired_area_sq_m: string | null;

  land_category: string | null;
  land_record_reference: string | null;
  source_system: string | null;

  geometry: unknown | null;

  created_at: string;
  updated_at: string;
};

export type ParcelListResponse = {
  items: Parcel[];
  total: number;
  offset: number;
  limit: number;
};

export type CreateParcelRequest = {
  parcel_reference: string;

  state: string;
  district: string;
  taluka?: string | null;
  village?: string | null;

  survey_number: string;
  subdivision_number?: string | null;

  recorded_area_sq_m: string;
  surveyed_area_sq_m?: string | null;
  acquired_area_sq_m?: string | null;

  land_category?: string | null;
  land_record_reference?: string | null;
  source_system?: string | null;
};

export type UpdateParcelRequest = {
  parcel_reference: string;

  state: string;
  district: string;
  taluka?: string | null;
  village?: string | null;

  survey_number: string;
  subdivision_number?: string | null;

  recorded_area_sq_m: string;
  surveyed_area_sq_m?: string | null;
  acquired_area_sq_m?: string | null;

  land_category?: string | null;
  land_record_reference?: string | null;
  source_system?: string | null;
};