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
  formatCitation,
  extractCitationRefs,
  formatResponseText,
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
} from './modelSettings';

export type {
  HardwareInfo,
  TierStatus,
  ModelSettings,
  DownloadProgress,
  ExternalApiSettings,
  ExternalApiSettingsSave,
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
} from './documentCategories';

export type {
  DocumentCategoryResponse,
  DocumentEntityResponse,
} from './documentCategories';

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
