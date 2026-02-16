/**
 * SearchPage Tests
 *
 * Sprint 04: DATA-005
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SearchPage } from '@/pages/SearchPage';
import * as api from '@/services/api';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
    }
  },
}));

vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  const filterDomProps = (props: Record<string, unknown>) => {
    const {
      variants: _variants,
      initial: _initial,
      animate: _animate,
      exit: _exit,
      whileHover: _whileHover,
      whileTap: _whileTap,
      transition: _transition,
      layout: _layout,
      layoutId: _layoutId,
      ...domProps
    } = props;
    return domProps;
  };

  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <div {...filterDomProps(props)}>{children}</div>;
      },
      button: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <button {...filterDomProps(props)}>{children}</button>;
      },
      tr: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => {
        return <tr {...filterDomProps(props)}>{children}</tr>;
      },
    },
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it('renders search input', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByPlaceholderText(/search analytes/i)).toBeInTheDocument();
  });

  it('shows empty state before search', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByText(/enter a search term/i)).toBeInTheDocument();
  });

  it('displays results after typing', async () => {
    const mockResponse = {
      results: [
        {
          id: 'obs-1', type: 'observation', title: 'Glucose',
          score: 0.95, snippet: 'Glucose: 95 mg/dL', highlight: '',
          collected_at: '2024-01-15', analyte: 'glucose',
          value: 95, unit: 'mg/dL', explanation: 'FTS match',
        },
      ],
      total_count: 1, query: 'glucose', mode: 'hybrid',
    };
    vi.mocked(api.apiGet).mockResolvedValue(mockResponse);

    const user = userEvent.setup();
    renderWithProviders(<SearchPage />);

    await user.type(screen.getByPlaceholderText(/search analytes/i), 'glucose');

    await waitFor(() => {
      expect(screen.getByText('Glucose')).toBeInTheDocument();
    }, { timeout: 2000 });
  });

  it('shows search mode buttons', () => {
    renderWithProviders(<SearchPage />);
    expect(screen.getByText(/hybrid/i)).toBeInTheDocument();
    expect(screen.getByText(/full text/i)).toBeInTheDocument();
    expect(screen.getByText(/semantic/i)).toBeInTheDocument();
  });

  it('stores recent queries in history', async () => {
    vi.mocked(api.apiGet).mockResolvedValue({
      results: [],
      total_count: 0,
      query: 'ferritin',
      mode: 'hybrid',
    });

    const user = userEvent.setup();
    renderWithProviders(<SearchPage />);
    await user.type(screen.getByPlaceholderText(/search analytes/i), 'ferritin');

    await waitFor(() => {
      const history = JSON.parse(window.sessionStorage.getItem('hc.search.history.v1') || '[]');
      expect(history[0]).toBe('ferritin');
    });
    expect(window.localStorage.getItem('hc.search.history.v1')).toBeNull();
  });

  it('saves a search preset', async () => {
    vi.mocked(api.apiGet).mockResolvedValue({
      results: [],
      total_count: 0,
      query: 'glucose',
      mode: 'hybrid',
    });

    const user = userEvent.setup();
    renderWithProviders(<SearchPage />);
    await user.type(screen.getByPlaceholderText(/search analytes/i), 'glucose');

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save search/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('button', { name: /save search/i }));

    const saved = JSON.parse(window.sessionStorage.getItem('hc.search.saved.v1') || '[]');
    expect(saved[0].query).toBe('glucose');
    expect(window.localStorage.getItem('hc.search.saved.v1')).toBeNull();
  });

  it('persists searches to localStorage when remember-on-device is enabled', async () => {
    vi.mocked(api.apiGet).mockResolvedValue({
      results: [],
      total_count: 0,
      query: 'vitamin d',
      mode: 'hybrid',
    });

    const user = userEvent.setup();
    renderWithProviders(<SearchPage />);
    await user.click(screen.getByLabelText(/remember searches on this device/i));
    await user.type(screen.getByPlaceholderText(/search analytes/i), 'vitamin d');

    await waitFor(() => {
      const history = JSON.parse(window.localStorage.getItem('hc.search.history.v1') || '[]');
      expect(history[0]).toBe('vitamin d');
      expect(window.localStorage.getItem('hc.search.persist_device.v1')).toBe('true');
    });
  });
});
