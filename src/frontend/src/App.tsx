/**
 * Asclexis Frontend Application
 *
 * Local-first medical results companion UI.
 * Designed for accessibility (WCAG 2.2 AA).
 *
 * Sprint 1: Added auth routing with ProtectedRoute.
 */

import { Suspense, lazy, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Skeleton } from './components/ui';
import { ErrorBoundary } from './components/ErrorBoundary';

// Layout
import { AppLayout } from './components/layout';
import { ProtectedRoute } from './components/auth';

// First-run page (not lazy: it is the entry point before a profile exists).
// Imported from its module, not the './pages' barrel, so the lazy pages below
// are not also statically imported into the main chunk.
import { ProfileSetup } from './pages/ProfileSetup';

const DocumentInbox = lazy(async () => {
  const module = await import('./pages/DocumentInbox');
  return { default: module.DocumentInbox };
});
const VerificationWorkbench = lazy(async () => {
  const module = await import('./pages/VerificationWorkbench');
  return { default: module.VerificationWorkbench };
});
const SettingsPage = lazy(async () => {
  const module = await import('./pages/SettingsPage');
  return { default: module.SettingsPage };
});
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
const CareTasksPage = lazy(async () => {
  const module = await import('./pages/CareTasksPage');
  return { default: module.CareTasksPage };
});
const TimelinePage = lazy(async () => {
  const module = await import('./pages/TimelinePage');
  return { default: module.TimelinePage };
});
const PinboardsPage = lazy(async () => {
  const module = await import('./pages/PinboardsPage');
  return { default: module.PinboardsPage };
});
const SearchPage = lazy(async () => {
  const module = await import('./pages/SearchPage');
  return { default: module.SearchPage };
});
const RecoverProfile = lazy(async () => {
  const module = await import('./pages/RecoverProfile');
  return { default: module.RecoverProfile };
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
    <div className="max-w-7xl mx-auto p-8 space-y-8 animate-fade-in" role="status" aria-live="polite">
      <div className="space-y-2">
        <Skeleton className="h-10 w-1/4" />
        <Skeleton className="h-4 w-1/3" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-48 rounded-2xl" />
      </div>
      <span className="sr-only">Loading page...</span>
    </div>
  );
}

/**
 * Error boundary for one route. Keyed by path, so navigating to another page
 * remounts it and clears a caught error.
 */
function RouteBoundary({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  return <ErrorBoundary key={pathname}>{children}</ErrorBoundary>;
}

function lazyRoute(element: ReactNode) {
  return (
    <RouteBoundary>
      <Suspense fallback={<RouteFallback />}>{element}</Suspense>
    </RouteBoundary>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* First run / no profile */}
          <Route path="/setup" element={<RouteBoundary><ProfileSetup /></RouteBoundary>} />

          {/* Forgot password -> recovery code (SEC-RECOV-001) */}
          <Route path="/recover" element={lazyRoute(<RecoverProfile />)} />

          {/* Protected routes - require authentication */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/inbox" replace />} />
              <Route path="inbox" element={lazyRoute(<DocumentInbox />)} />
              <Route path="verify" element={lazyRoute(<VerificationWorkbench />)} />
              <Route path="trends" element={lazyRoute(<TrendsDashboard />)} />
              <Route path="timeline" element={lazyRoute(<TimelinePage />)} />
              <Route path="search" element={lazyRoute(<SearchPage />)} />
              <Route path="interpret" element={lazyRoute(<LabInterpreter />)} />
              <Route path="medications" element={lazyRoute(<MedicationCoach />)} />
              <Route path="medications/:medicationId" element={lazyRoute(<MedicationDetail />)} />
              <Route path="notifications" element={lazyRoute(<NotificationSettings />)} />
              <Route path="care-tasks" element={lazyRoute(<CareTasksPage />)} />
              <Route path="pinboards" element={lazyRoute(<PinboardsPage />)} />
              <Route path="explain" element={lazyRoute(<ExplainAssistant />)} />
              <Route path="export" element={lazyRoute(<ExportPage />)} />
              <Route path="settings" element={lazyRoute(<SettingsPage />)} />
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
