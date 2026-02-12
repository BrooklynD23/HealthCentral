/**
 * Vitest Test Setup
 *
 * Global test configuration and mocks.
 */

import { afterEach, beforeAll, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { useAuthStore } from '@/stores/authStore';

// Mock window.matchMedia for framer-motion and responsive hooks
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Mock Element.scrollIntoView for components that auto-scroll
  Element.prototype.scrollIntoView = vi.fn();
});

// Clear all mocks and reset stores after each test
afterEach(() => {
  vi.clearAllMocks();

  // Reset Zustand auth store to prevent state leaking between tests
  useAuthStore.getState().clearAuth();

  // Clear localStorage to prevent persisted store state from leaking
  localStorage.clear();
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});
