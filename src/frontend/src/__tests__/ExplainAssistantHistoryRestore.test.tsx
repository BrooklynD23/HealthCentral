import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    const Component = ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => {
      const domProps = Object.fromEntries(
        Object.entries(props).filter(
          ([key]) =>
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
        )
      );
      const Tag = tag as keyof JSX.IntrinsicElements;
      return <Tag {...domProps}>{children}</Tag>;
    };
    Component.displayName = `motion.${tag}`;
    return Component;
  };
  return {
    motion: new Proxy({}, { get: (_, prop: string) => createMotionComponent(prop) }),
    m: new Proxy({}, { get: (_, prop: string) => createMotionComponent(prop) }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ExplainAssistant />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const later = <T,>(fn: () => T) =>
  new Promise<T>((resolve, reject) =>
    setTimeout(() => {
      try {
        resolve(fn());
      } catch (e) {
        reject(e);
      }
    }, 50)
  );

function mockApi(sessions: () => unknown) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url === '/assistant/sessions') return later(sessions) as Promise<never>;
    if (url === '/assistant/sessions/s1') {
      return Promise.resolve({
        session_id: 's1',
        title: null,
        turns: [
          { role: 'user', content: 'What is my A1C?', turn_id: 't1' },
          { role: 'assistant', content: 'Your A1C restored answer', turn_id: 't2' },
        ],
      }) as Promise<never>;
    }
    return Promise.resolve([]) as Promise<never>;
  });
}

const historyCalls = () =>
  vi.mocked(api.apiGet).mock.calls.filter(([u]) => String(u).startsWith('/assistant/sessions/'));

describe('ExplainAssistant history restore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
  });

  it('ASSIST-HIST-001: restores previous conversation when sessions resolve late', async () => {
    mockApi(() => ({
      sessions: [
        { session_id: 's1', title: null, turn_count: 2, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
      ],
    }));
    renderPage();
    expect(await screen.findByText('What is my A1C?')).toBeInTheDocument();
    expect(await screen.findByText('Your A1C restored answer')).toBeInTheDocument();
  });

  it('ASSIST-HIST-001: empty sessions list shows empty state, no history request', async () => {
    mockApi(() => ({ sessions: [] }));
    renderPage();
    await waitFor(() =>
      expect(vi.mocked(api.apiGet).mock.calls.some(([u]) => u === '/assistant/sessions')).toBe(true)
    );
    expect(await screen.findByText(/Ask about your lab results/i)).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 100));
    expect(historyCalls()).toHaveLength(0);
  });

  it('ASSIST-HIST-001: failed sessions request shows empty state, no history request', async () => {
    mockApi(() => {
      throw new Error('boom');
    });
    renderPage();
    expect(await screen.findByText(/Ask about your lab results/i)).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 100));
    expect(historyCalls()).toHaveLength(0);
  });
});
