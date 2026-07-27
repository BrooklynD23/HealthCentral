/**
 * Services barrel export
 */

// API utilities
export { ApiError, apiGet, apiPost, apiPut, apiPatch, apiDelete, apiUpload } from './api';

// Types
export type {
  Profile,
  ProfileCreate,
  TokenResponse,
  LoginRequest,
  UnlockRequest,
  Document,
  DocumentImportResponse,
  ImportSummary,
  DocumentVerifyResponse,
  DocumentPage,
  Observation,
  ObservationVerify,
  TrendPoint,
  TrendData,
  Panel,
  ObservationFilters,
  DocumentFilters,
  Medication,
  MedicationSchedule,
  MedicationCreate,
  MedicationUpdate,
  DoseLog,
  DoseResponse,
  AdherenceStats,
  LearnPatternsResponse,
  ScheduleCreate,
  ScheduleUpdate,
  NotificationSettings,
  NotificationSettingsUpdate,
  ReminderLogEntry,
  NotificationHistoryStats,
  NotificationHistoryResponse,
  NotificationSchedulerStatus,
  TestNotificationRequest,
  TestNotificationResponse,
  ReminderInteractionType,
} from './types';

// Profile hooks
export {
  useProfiles,
  useProfile,
  useCreateProfile,
  useLogin,
  useUnlockProfile,
  useLockProfile,
  useLogout,
  useDeleteProfile,
  PROFILE_DELETE_CONFIRMATION,
} from './profiles';

// Document hooks
export {
  useDocuments,
  useDocument,
  useDocumentPages,
  useImportDocument,
  useDeleteDocument,
  useReprocessDocument,
  useVerifyDocument,
} from './documents';

// Observation hooks
export {
  useObservations,
  useObservation,
  useVerifyObservation,
  useTrend,
  usePanel,
  useAnalyteList,
} from './observations';

// Export hooks
export {
  useExportCSV,
  useExportJSON,
  useGenerateSummary,
  useDownloadSummary,
  useGenerateQuestions,
  useGenerateVisitPrep,
  useDownloadVisitPrep,
  generateVisitPrep,
  downloadVisitPrep,
  useGenerateFhirExport,
  useDownloadFhirExport,
  generateFhirExport,
  downloadFhirExport,
} from './export';

export type {
  SummaryRequest,
  SummaryResponse,
  QuestionItem,
  ExportFilters,
  VisitPrepRequest,
  VisitPrepResponse,
  VisitPrepFormat,
  FhirExportRequest,
  FhirExportResponse,
} from './export';

// Assistant hooks
export {
  useSendMessage,
  useGlossaryLookup,
  useTestIntentLookup,
  useVerificationStatus,
  useGlossaryMutation,
  useTestIntentMutation,
  useChatSessions,
  useCreateChatSession,
  useChatSessionHistory,
  useDeleteChatSession,
  useMemorySettings,
  useUpdateMemorySettings,
  formatCitation,
  extractCitationRefs,
  formatResponseText,
  DOCUMENT_CATEGORIES,
} from './assistant';

export type {
  Citation,
  ResponseSegment,
  VerificationInfo,
  ChatMessage,
  ChatRequest,
  ChatResponse,
  GlossaryResponse,
  TestIntentResponse,
  SessionSummary,
  SessionListResponse,
  SessionHistoryResponse,
  NewSessionRequest,
  NewSessionResponse,
  MemorySettingsResponse,
  DocumentCategory,
} from './assistant';

// Model settings hooks
export {
  useModelSettings,
  useDetectHardware,
  useSetTier,
  useTiers,
  useDownloadProgress,
  useStartDownload,
  useExternalApiSettings,
  useSaveExternalApiSettings,
  useSaveOcrPreference,
  useEnvironmentDiagnostics,
  useRecheckDiagnostics,
} from './modelSettings';

export type {
  HardwareInfo,
  TierStatus,
  ModelSettings,
  DownloadProgress,
  ExternalApiSettings,
  ExternalApiSettingsSave,
  OcrSettingsResponse,
  DiagnosticFixAction,
  DiagnosticComponent,
  DiagnosticsListResponse,
} from './modelSettings';

// Notification hooks
export {
  useNotificationSettings,
  useUpdateNotificationSettings,
  useNotificationHistory,
  useNotificationSchedulerStatus,
  useSendTestNotification,
  useSendMedicationTestNotification,
  useRecordReminderInteraction,
} from './notifications';

export type {
  NotificationHistoryFilters,
} from './notifications';

// Timeline hooks (HC-M14)
export { useTimeline } from './timeline';

export type {
  TimelineEvent,
  TimelineEventType,
  TimelineDateSource,
  TimelineVerificationStatus,
  TimelineResponse,
  TimelineFilters,
} from './timeline';

// Local cross-record search hooks (HC-M21)
export { useSearch } from './search';

export type {
  SearchFilters,
  SearchRecordType,
  SearchResponse,
  SearchResult,
  SearchVerifiedStatus,
} from './search';

// Document category hooks
export {
  useDocumentCategory,
  useDocumentEntities,
  useSetEntityVerification,
  setEntityVerification,
} from './documentCategories';

export type {
  DocumentCategoryResponse,
  DocumentEntityResponse,
  EntityVerificationRequest,
} from './documentCategories';

// Care task hooks (HC-M15)
export {
  useCareTasks,
  useCareTaskCandidates,
  useAcceptCareTask,
  useUpdateCareTask,
} from './careTasks';

export type {
  CarePlanTask,
  CareTaskCandidate,
  CareTaskStatus,
  AcceptCareTaskRequest,
  CareTaskUpdateRequest,
} from './careTasks';

// Smart highlight hooks (HC-M16)
export {
  useDocumentHighlights,
  useHighlightsSummary,
  HIGHLIGHT_LABELS,
} from './highlights';

export type {
  Highlight,
  HighlightType,
  DocumentHighlightSummary,
} from './highlights';

// Medication reconciliation hooks (HC-M19)
export { useMedReconciliation } from './medReconcile';

export type {
  MedReconcileSuggestion,
  MedReconcileSuggestionType,
} from './medReconcile';

// User-curated record collections (HC-M20)
export {
  listPinboards,
  createPinboard,
  renamePinboard,
  deletePinboard,
  listPinboardItems,
  addPinboardItem,
  removePinboardItem,
  exportPinboard,
  usePinboards,
  usePinboardItems,
  useCreatePinboard,
  useRenamePinboard,
  useDeletePinboard,
  useAddPinboardItem,
  useRemovePinboardItem,
  useExportPinboard,
} from './pinboards';

export type {
  Pinboard,
  PinboardItem,
  PinboardItemType,
  AddPinboardItemRequest,
  PinboardExportRequest,
  PinboardExportResponse,
} from './pinboards';

// Memory store hooks (ASSIST-MEM-001/002)
export {
  useMemoryItems,
  useMemoryItem,
  useCreateMemoryItem,
  useUpdateMemoryItem,
  useDeleteMemoryItem,
} from './memory';

export type { MemoryItem, MemoryItemCreate, MemoryItemUpdate } from './types';

// Gamification hooks
export { useBadges } from './gamification';

export type {
  BadgeInfo,
  DoseLogResponse,
  BadgeStatus,
  BadgeListResponse,
} from './types';

// Timezone + Voice settings hooks
export {
  useTimezone,
  useSaveTimezone,
  useVoiceSettings,
  useSaveVoiceSettings,
} from './modelSettings';

// RL feedback hooks (RL-FEED-001/002)
export {
  useSubmitFeedback,
  useFeedbackStats,
  useExportDataset,
  FEEDBACK_TAGS,
} from './feedback';

export type {
  FeedbackTag,
  FeedbackRequest,
  FeedbackResponse,
  FeedbackStatsResponse,
  ExportRequest,
  ExportResponse,
} from './feedback';
