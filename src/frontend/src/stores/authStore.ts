/**
 * Authentication Store
 *
 * Sprint 1 - S1-FE-002: Token storage source of truth
 *
 * Manages JWT tokens and authentication state using Zustand.
 * Persists token to localStorage for session persistence.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface AuthState {
  token: string | null;
  profileId: string | null;
  profileName: string | null;
  expiresAt: number | null;
  isAuthenticated: boolean;
}

export interface AuthActions {
  setAuth: (params: {
    token: string;
    profileId: string;
    profileName: string;
    expiresIn?: number;
  }) => void;
  clearAuth: () => void;
  isTokenExpired: () => boolean;
}

export type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  token: null,
  profileId: null,
  profileName: null,
  expiresAt: null,
  isAuthenticated: false,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setAuth: ({ token, profileId, profileName, expiresIn }) => {
        const expiresAt = expiresIn
          ? Date.now() + expiresIn * 1000
          : null;

        set({
          token,
          profileId,
          profileName,
          expiresAt,
          isAuthenticated: true,
        });
      },

      clearAuth: () => {
        set(initialState);
      },

      isTokenExpired: () => {
        const { expiresAt } = get();
        if (!expiresAt) return false;
        return Date.now() >= expiresAt;
      },
    }),
    {
      name: 'healthcentral-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        profileId: state.profileId,
        profileName: state.profileName,
        expiresAt: state.expiresAt,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

/**
 * Get current auth token for use outside of React components.
 */
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}

/**
 * Check if currently authenticated.
 */
export function isAuthenticated(): boolean {
  const state = useAuthStore.getState();
  return state.isAuthenticated && !state.isTokenExpired();
}
