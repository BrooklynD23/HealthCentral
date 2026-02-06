/**
 * Protected Route Component
 *
 * Sprint 1 - S1-FE-003: Session/Lock UX
 *
 * Redirects unauthenticated users to setup/login.
 */

import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';

export function ProtectedRoute() {
  const { isAuthenticated, isTokenExpired } = useAuthStore();

  // Not authenticated - redirect to setup
  if (!isAuthenticated || isTokenExpired()) {
    return <Navigate to="/setup" replace />;
  }

  return <Outlet />;
}
