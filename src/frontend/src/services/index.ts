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
} from './export';

export type {
  SummaryRequest,
  SummaryResponse,
  QuestionItem,
  ExportFilters,
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
