/**
 * Services barrel export
 */

// API utilities
export { ApiError, apiGet, apiPost, apiPut, apiDelete, apiUpload } from './api';

// Types
export type {
  Profile,
  ProfileCreate,
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
  useUnlockProfile,
  useLockProfile,
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
