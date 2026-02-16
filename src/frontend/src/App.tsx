/**
 * HealthCentral Frontend Application
 *
 * Local-first medical results companion UI.
 * Designed for accessibility (WCAG 2.2 AA).
 *
 * Sprint 1: Added auth routing with ProtectedRoute.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Layout
import { AppLayout } from './components/layout';
import { ProtectedRoute } from './components/auth';

// Pages
import {
  ProfileSetup,
  DocumentInbox,
  VerificationWorkbench,
  TrendsDashboard,
  LabInterpreter,
  MedicationCoach,
  MedicationDetail,
  NotificationSettings,
  ExplainAssistant,
  ExportPage,
  SearchPage,
  SettingsPage,
} from './pages';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* First run / no profile */}
          <Route path="/setup" element={<ProfileSetup />} />

          {/* Protected routes - require authentication */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/inbox" replace />} />
              <Route path="inbox" element={<DocumentInbox />} />
              <Route path="verify" element={<VerificationWorkbench />} />
              <Route path="trends" element={<TrendsDashboard />} />
              <Route path="interpret" element={<LabInterpreter />} />
              <Route path="medications" element={<MedicationCoach />} />
              <Route path="medications/:medicationId" element={<MedicationDetail />} />
              <Route path="notifications" element={<NotificationSettings />} />
              <Route path="explain" element={<ExplainAssistant />} />
              <Route path="export" element={<ExportPage />} />
              <Route path="search" element={<SearchPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Route>

          {/* Fallback redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
