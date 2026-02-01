/**
 * API Type Definitions
 * 
 * Mirrors backend Pydantic models for type safety.
 */

// Profile types
export interface Profile {
  id: string;
  display_name: string;
  is_locked: boolean;
  created_at: string;
  last_accessed_at: string | null;
}

export interface ProfileCreate {
  display_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  profile_id: string;
  profile_name: string;
}

export interface LoginRequest {
  profile_id: string;
  password: string;
}

export interface UnlockRequest {
  password: string;
}

// Document types
export interface Document {
  id: string;
  profile_id: string;
  doc_type: string;
  source: string | null;
  status: string;
  page_count: number | null;
  collection_date: string | null;
  imported_at: string;
  parsed_at: string | null;
  verified_at: string | null;
}

export interface DocumentImportResponse {
  document: Document;
  observations_extracted: number;
  needs_verification: boolean;
}

export interface DocumentPage {
  page_number: number;
  text: string;
  has_tables: boolean;
}

// Observation types
export interface Observation {
  id: string;
  profile_id: string;
  doc_id: string;
  analyte_canonical: string;
  analyte_raw: string;
  value: number | null;
  value_text: string | null;
  unit: string | null;
  ref_low: number | null;
  ref_high: number | null;
  ref_range_text: string | null;
  flag: string | null;
  is_abnormal: boolean | null;
  collected_at: string | null;
  user_verified: boolean;
  extraction_confidence: number | null;
}

export interface ObservationVerify {
  value?: number;
  value_text?: string;
  unit?: string;
  ref_low?: number;
  ref_high?: number;
  collected_at?: string;
  notes?: string;
}

export interface TrendPoint {
  date: string;
  value: number;
  unit: string;
  is_abnormal: boolean;
  flag: string | null;
  doc_id: string;
}

export interface TrendData {
  analyte_canonical: string;
  analyte_display_name: string;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  data_points: TrendPoint[];
  summary: string;
}

export interface Panel {
  panel_id: string;
  panel_name: string;
  observations: Observation[];
  collection_date: string | null;
}

// Filter types
export interface ObservationFilters {
  profile_id: string;
  analyte?: string;
  from_date?: string;
  to_date?: string;
  abnormal_only?: boolean;
  needs_verification?: boolean;
}

export interface DocumentFilters {
  profile_id: string;
  status?: string;
  doc_type?: string;
}
