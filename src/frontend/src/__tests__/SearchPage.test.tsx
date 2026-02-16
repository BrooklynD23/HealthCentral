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
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<object>) => <div {...props}>{children}</div>,
    },
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
});
