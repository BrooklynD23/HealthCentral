/**
 * Vitest Test Setup
 *
 * Global test configuration and mocks.
 */

import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';

// Mock localStorage before any module (e.g. the persisted Zustand auth store)
// reads the bare `localStorage` global at import time. This must be a plain
// (non-imported) module side effect — ESM hoists static imports ahead of it
// regardless of source order — and Node 26 exposes a global localStorage
// accessor that can otherwise resolve undefined.
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
Object.defineProperty(window, 'localStorage', {
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
  const { useAuthStore } = await vi.importActual<typeof import('@/stores/authStore')>(
    '@/stores/authStore'
  );
  useAuthStore.getState().clearAuth();

  // Clear localStorage to prevent persisted store state from leaking
  localStorage.clear();

  // TOAST-TIMER-TEARDOWN: leave no toast queued — a still-live toast keeps
  // sonner's timers armed past jsdom teardown (see afterAll below).
  const { toast } = await vi.importActual<typeof import('sonner')>('sonner');
  toast.dismiss();
});

// TOAST-TIMER-TEARDOWN (SONNER-TEARDOWN-FLAKE): sonner arms a bare
// 200 ms setTimeout(removeToast) inside deleteToast (dist/index.mjs:634-636,
// the site the CI errors name) plus 0-tick flushSync timers in its
// subscribers (:943,:951,:1032); none is cancelled on unmount. Dismiss the
// queue, then outwait the unmount timer so whichever survives fires while
// `window` still exists — else vitest reports "Unhandled error:
// ReferenceError: window is not defined" with every test green.
afterAll(async () => {
  const { toast } = await vi.importActual<typeof import('sonner')>('sonner');
  toast.dismiss();
  if (toast.getHistory().length === 0) return;
  await new Promise((resolve) => setTimeout(resolve, 250));
});
