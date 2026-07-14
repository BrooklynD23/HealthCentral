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
  /** Lowest stored confidence among extracted observations/entities. */
  extraction_confidence: number | null;
}

export interface DocumentImportResponse {
  document: Document;
  observations_extracted: number;
  needs_verification: boolean;
  duplicate_warning: {
    match_type: 'content_hash' | 'same_date';
    document_id: string;
    title: string | null;
  } | null;
}

export interface DocumentVerifyResponse {
  document: Document;
  verified_count: number;
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
  source_page: number | null;
  source_bbox_json: string | null;
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

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface TrendPoint {
  date: string;
  value: number;
  unit: string;
  is_abnormal: boolean;
  flag: string | null;
  doc_id: string;
  extraction_confidence: number | null;
  // Set when the point was normalized from a differently-reported unit
  // (NORM-UNIT-001); both null when no conversion happened.
  original_value?: number | null;
  original_unit?: string | null;
}

export interface TrendData {
  analyte_canonical: string;
  analyte_display_name: string;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
  data_points: TrendPoint[];
  summary: string;
  excluded_count?: number;
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
  doc_id?: string;
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

// Interpretation types
export interface Citation {
  type: string;
  id: string;
  text: string;
}

export interface InterpretationResponse {
  id: string;
  observation_id: string;
  interpretation_text: string;
  severity_level: string;
  advice_text: string | null;
  citations: Citation[];
  context: Record<string, unknown> | null;
  model_id: string;
  model_tier: string;
  confidence_score: number;
  requires_physician_review: boolean;
  physician_review_reason: string | null;
  viewed_at: string | null;
  created_at: string;
}

export interface RelationshipInsight {
  relationship: string;
  value: number;
  status: string;
  interpretation: string;
  source_id: string | null;
}

export interface PanelInterpretationResponse {
  id: string;
  panel_name: string;
  collected_at: string;
  observation_ids: string[];
  summary_text: string;
  overall_status: string;
  relationship_insights: RelationshipInsight[] | null;
  advice_text: string | null;
  citations: Citation[];
  confidence_score: number;
  requires_physician_review: boolean;
  created_at: string;
}

export interface BiomarkerKnowledge {
  id: string;
  analyte_canonical: string;
  display_name: string;
  description: string;
  clinical_significance: string;
  normal_interpretation: string;
  high_interpretation: string;
  low_interpretation: string;
  reference_ranges: Record<string, unknown>;
  common_causes_high: string[] | null;
  common_causes_low: string[] | null;
  critical_low: number | null;
  critical_high: number | null;
  standard_unit: string;
  category: string;
  panels: string[] | null;
  sources: Record<string, unknown>[];
}

export interface BatchInterpretResponse {
  successful: string[];
  failed: Array<{ observation_id: string; error: string }>;
}

export interface GroundedCitation {
  source_type: string;
  doc_id: string | null;
  doc_title: string | null;
  page: number | null;
  text_snippet: string;
  authority_tier?: number;
  authority_score?: number;
}

export interface GroundedInterpretationSegment {
  segment_type: string;
  content: string;
  citations: GroundedCitation[];
}

export interface GroundedVerification {
  enabled: boolean;
  total_claims: number;
  verified_claims: number;
  failed_claims: number;
  faithfulness_score: number;
  authority_score: number;
  summary: string;
  issues: string[];
}

export interface GroundedInterpretationResponse {
  interpretation: InterpretationResponse;
  grounded_segments: GroundedInterpretationSegment[];
  full_response: string;
  insufficient_context: boolean;
  insufficient_reasons: string[];
  verification: GroundedVerification;
  is_valid: boolean;
  validation_errors: string[];
}

// Medication types
export interface MedicationSchedule {
  id: string;
  medication_id: string;
  schedule_label: string;
  target_time: string;
  adaptive_window_start: string | null;
  adaptive_window_end: string | null;
  reminder_offset_minutes: number;
  days_of_week: number[] | null;
  is_active: boolean;
  created_at: string;
}

export interface Medication {
  id: string;
  profile_id: string;
  name: string;
  generic_name: string | null;
  dosage_amount: number | null;
  dosage_unit: string | null;
  dosage_form: string | null;
  frequency: string;
  instructions: string | null;
  is_active: boolean;
  reminder_enabled: boolean;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  schedules: MedicationSchedule[];
}

export interface MedicationCreate {
  name: string;
  generic_name?: string;
  dosage_amount?: number;
  dosage_unit?: string;
  dosage_form?: string;
  frequency?: string;
  instructions?: string;
  reminder_enabled?: boolean;
  started_at?: string;
  metadata?: Record<string, unknown>;
}

export interface MedicationUpdate {
  name?: string;
  generic_name?: string;
  dosage_amount?: number;
  dosage_unit?: string;
  dosage_form?: string;
  frequency?: string;
  instructions?: string;
  reminder_enabled?: boolean;
  is_active?: boolean;
  ended_at?: string;
  metadata?: Record<string, unknown>;
}

export interface DoseLog {
  taken_at: string;
  log_method?: string;
  dosage_amount?: number;
  dosage_unit?: string;
  notes?: string;
  was_skipped?: boolean;
  skip_reason?: string;
}

export interface DoseResponse {
  id: string;
  medication_id: string;
  schedule_id: string | null;
  taken_at: string;
  log_method: string;
  dosage_amount: number | null;
  dosage_unit: string | null;
  variance_minutes: number | null;
  notes: string | null;
  was_skipped: boolean;
  skip_reason: string | null;
  logged_at: string;
}

export interface AdherenceStats {
  medication_id: string;
  current_streak_days: number;
  longest_streak_days: number;
  last_7_days_adherence: number;
  last_30_days_adherence: number;
  total_doses_taken: number;
  total_doses_skipped: number;
  total_doses_expected: number;
}

// Gamification types
export interface BadgeInfo {
  badge_id: string;
  name: string;
  description: string;
  icon: string;
  medication_id: string | null;
  earned_at: string;
}

export interface DoseLogResponse {
  dose: DoseResponse;
  newly_earned_badges: BadgeInfo[];
}

export interface BadgeStatus {
  id: string;
  name: string;
  description: string;
  icon: string;
  criteria_type: string;
  earned: boolean;
  earned_at: string | null;
  medication_id: string | null;
}

export interface BadgeListResponse {
  badges: BadgeStatus[];
}

export interface LearnPatternsResponse {
  patterns_created: number;
  schedules_updated: number;
  time_window: Record<string, unknown> | null;
  weekday_pattern: Record<string, unknown> | null;
  missed_days: Array<Record<string, unknown>> | null;
  streak: Record<string, unknown> | null;
}

export interface ScheduleCreate {
  schedule_label: string;
  target_time: string;
  reminder_offset_minutes?: number;
  days_of_week?: number[];
  is_active?: boolean;
}

export interface ScheduleUpdate {
  schedule_label?: string;
  target_time?: string;
  reminder_offset_minutes?: number;
  days_of_week?: number[];
  is_active?: boolean;
}

// Notification types
export interface NotificationSettings {
  medication_id: string;
  enabled: boolean;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  max_reminders_per_dose: number;
  initial_offset_minutes: number;
  nudge_delay_minutes: number;
  alert_delay_minutes: number;
  weekend_enabled: boolean;
  celebration_enabled: boolean;
}

export interface NotificationSettingsUpdate {
  enabled?: boolean;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  max_reminders_per_dose?: number;
  initial_offset_minutes?: number;
  nudge_delay_minutes?: number;
  alert_delay_minutes?: number;
  weekend_enabled?: boolean;
  celebration_enabled?: boolean;
}

export interface ReminderLogEntry {
  id: string;
  medication_id: string;
  medication_name: string;
  schedule_id: string | null;
  reminder_type: string;
  message_tone: string;
  message: string;
  sent_at: string;
  delivery_method: string;
  was_interacted: boolean;
  interaction_type: string | null;
  interacted_at: string | null;
}

export interface NotificationHistoryStats {
  sent_last_7_days: number;
  sent_last_30_days: number;
  interaction_rate_7d: number;
  by_type: Record<string, number>;
}

export interface NotificationHistoryResponse {
  total: number;
  reminders: ReminderLogEntry[];
  stats: NotificationHistoryStats;
}

export interface NotificationSchedulerStatus {
  state: 'stopped' | 'running' | 'paused';
  active_platform: string | null;
  registered_profiles: number;
  notifications_sent_this_hour: number;
  last_check: string | null;
}

export interface TestNotificationRequest {
  title?: string;
  body?: string;
}

export interface TestNotificationResponse {
  success: boolean;
  platform: string;
  message: string;
}

export type ReminderInteractionType =
  | 'dismissed'
  | 'snoozed'
  | 'marked_taken'
  | 'opened_app';

// Memory store types (ASSIST-MEM-001)
export interface MemoryItem {
  id: string;
  profile_id: string;
  key: string;
  value: string;
  category: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryItemCreate {
  key: string;
  value: string;
  category?: string;
}

export interface MemoryItemUpdate {
  key?: string;
  value?: string;
  category?: string;
}

// Correlation types (UX-001: frontend-only temporal overlay)

export interface MedicationOverlayPeriod {
  medicationId: string;
  medicationName: string;
  startedAt: string;
  endedAt: string | null;
  dosageLabel: string | null;
}

export interface CorrelationContext {
  observation: Observation;
  activeMedications: MedicationOverlayPeriod[];
}
