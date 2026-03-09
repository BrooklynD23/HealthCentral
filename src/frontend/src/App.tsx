/**
 * HealthCentral Frontend Application
 *
 * Local-first medical results companion UI.
 * Designed for accessibility (WCAG 2.2 AA).
 *
 * Sprint 1: Added auth routing with ProtectedRoute.
 */

import { Suspense, lazy, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';

// Layout
import { AppLayout } from './components/layout';
import { ProtectedRoute } from './components/auth';

// Eager pages
import { ProfileSetup, DocumentInbox, VerificationWorkbench, SettingsPage } from './pages';

const TrendsDashboard = lazy(async () => {
  const module = await import('./pages/TrendsDashboard');
  return { default: module.TrendsDashboard };
});
const LabInterpreter = lazy(async () => {
  const module = await import('./pages/LabInterpreter');
  return { default: module.LabInterpreter };
});
const MedicationCoach = lazy(async () => {
  const module = await import('./pages/MedicationCoach');
  return { default: module.MedicationCoach };
});
const MedicationDetail = lazy(async () => {
  const module = await import('./pages/MedicationDetail');
  return { default: module.MedicationDetail };
});
const NotificationSettings = lazy(async () => {
  const module = await import('./pages/NotificationSettings');
  return { default: module.NotificationSettings };
});
const ExplainAssistant = lazy(async () => {
  const module = await import('./pages/ExplainAssistant');
  return { default: module.ExplainAssistant };
});
const ExportPage = lazy(async () => {
  const module = await import('./pages/ExportPage');
  return { default: module.ExportPage };
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
});

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center" role="status" aria-live="polite">
      <Loader2 className="h-8 w-8 animate-spin text-accent" />
      <span className="sr-only">Loading page...</span>
    </div>
  );
}

function lazyRoute(element: ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

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
              <Route path="trends" element={lazyRoute(<TrendsDashboard />)} />
              <Route path="interpret" element={lazyRoute(<LabInterpreter />)} />
              <Route path="medications" element={lazyRoute(<MedicationCoach />)} />
              <Route path="medications/:medicationId" element={lazyRoute(<MedicationDetail />)} />
              <Route path="notifications" element={lazyRoute(<NotificationSettings />)} />
              <Route path="explain" element={lazyRoute(<ExplainAssistant />)} />
              <Route path="export" element={lazyRoute(<ExportPage />)} />
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
