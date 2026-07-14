/**
 * Vitest Test Setup
 *
 * Global test configuration and mocks.
 */

import { afterEach, beforeAll, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Install storage before test modules import persisted Zustand stores. Node 26
// exposes a global localStorage accessor that can otherwise resolve undefined.
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

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: localStorageMock,
});

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
afterEach(async () => {
  vi.clearAllMocks();

  // Reset Zustand auth store to prevent state leaking between tests
  const { useAuthStore } = await import('@/stores/authStore');
  useAuthStore.getState().clearAuth();

  // Clear localStorage to prevent persisted store state from leaking
  localStorage.clear();
});
