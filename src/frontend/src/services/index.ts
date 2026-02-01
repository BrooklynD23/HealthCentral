/**
 * Services barrel export
 */

// API utilities
export { ApiError, apiGet, apiPost, apiPut, apiDelete, apiUpload } from './api';

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
  ChatRequest,
  ChatResponse,
  GlossaryResponse,
  TestIntentResponse,
} from './assistant';
