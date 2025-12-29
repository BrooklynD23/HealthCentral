/**
 * HealthCentral Frontend Application
 * 
 * Local-first medical results companion UI.
 * Designed for accessibility (WCAG 2.2 AA).
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Layout
import { AppLayout } from './components/layout';

// Pages
import {
  ProfileSetup,
  DocumentInbox,
  VerificationWorkbench,
  TrendsDashboard,
  ExplainAssistant,
  ExportPage,
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
          
          {/* Main app with sidebar layout */}
          <Route path="/" element={<AppLayout />}>
            <Route index element={<DocumentInbox />} />
            <Route path="inbox" element={<DocumentInbox />} />
            <Route path="verify" element={<VerificationWorkbench />} />
            <Route path="trends" element={<TrendsDashboard />} />
            <Route path="explain" element={<ExplainAssistant />} />
            <Route path="export" element={<ExportPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
