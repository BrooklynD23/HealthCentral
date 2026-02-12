/**
 * ExplainAssistant Component Tests
 *
 * Sprint 5 - S5-FE-001: Wire ExplainAssistant
 *
 * Tests that:
 * - Chat sends messages to API
 * - Response displays with citations
 * - Empty/error states are handled
 * - Insufficient context is displayed
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import * as api from '@/services/api';

// Mock the API module with URL-based routing
vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
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

// Mock framer-motion to avoid animation issues
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion');
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }: React.PropsWithChildren<object>) => (
        <div {...props}>{children}</div>
      ),
    },
    AnimatePresence: ({ children }: React.PropsWithChildren) => <>{children}</>,
  };
});

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{component}</BrowserRouter>
    </QueryClientProvider>
  );
}

const mockChatResponse = {
  segments: [
    {
      segment_type: 'report_facts',
      content: 'Your hemoglobin level is 14.2 g/dL [cite:1], which is within normal range.',
      citations: [
        {
          source_type: 'user_document',
          doc_id: 'doc-1',
          doc_title: 'Quest Lab Report',
          page: 1,
          text_snippet: 'Hemoglobin: 14.2 g/dL',
        },
      ],
    },
    {
      segment_type: 'general_info',
      content: 'Hemoglobin is a protein in red blood cells that carries oxygen [cite:2].',
      citations: [
        {
          source_type: 'reference',
          doc_id: null,
          doc_title: 'Medical Reference',
          page: null,
          text_snippet: 'Hemoglobin is the oxygen-carrying protein...',
        },
      ],
    },
  ],
  full_response: `**REPORT FACTS**
Your hemoglobin level is 14.2 g/dL [cite:1], which is within normal range.

**GENERAL INFO**
Hemoglobin is a protein in red blood cells that carries oxygen [cite:2].`,
  insufficient_context: false,
  insufficient_reasons: [],
  verification: {
    enabled: true,
    total_claims: 2,
    verified_claims: 2,
    failed_claims: 0,
    faithfulness_score: 0.95,
    authority_score: 0.85,
    summary: 'All claims verified',
    issues: [],
  },
  is_valid: true,
  validation_errors: [],
};

const mockInsufficientContextResponse = {
  segments: [
    {
      segment_type: 'uncertainty',
      content: "I don't have enough information to answer this question. Please make sure you have uploaded relevant documents.",
      citations: [],
    },
  ],
  full_response: "I don't have enough information to answer this question. Please make sure you have uploaded relevant documents.",
  insufficient_context: true,
  insufficient_reasons: ['No relevant documents found'],
  verification: {
    enabled: false,
    total_claims: 0,
    verified_claims: 0,
    failed_claims: 0,
    faithfulness_score: 0,
    authority_score: 0,
    summary: '',
    issues: [],
  },
  is_valid: true,
  validation_errors: [],
};

describe('ExplainAssistant', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('FE-AST-001: Chat sends message', () => {
    it('should display initial empty state', () => {
      renderWithProviders(<ExplainAssistant />);

      expect(screen.getByText('Ask about your lab results')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Ask about your results...')).toBeInTheDocument();
    });

    it('should send message when user types and clicks send', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      const sendButton = screen.getByRole('button', { name: '' }); // Send button has no text

      await user.type(input, 'What does my hemoglobin level mean?');
      await user.click(sendButton);

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            question: 'What does my hemoglobin level mean?',
            include_references: true,
            enable_verification: true,
          })
        );
      });
    });

    it('should send message when user presses Enter', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');

      await user.type(input, 'What is my glucose level?{enter}');

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            question: 'What is my glucose level?',
          })
        );
      });
    });

    it('should disable input while sending', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      // Create a promise that doesn't resolve immediately
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockApiPost.mockReturnValueOnce(pendingPromise as Promise<unknown>);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      // Input should be disabled while loading
      await waitFor(() => {
        expect(input).toBeDisabled();
      });

      // Resolve the promise
      resolvePromise!(mockChatResponse);

      // Input should be enabled again after response
      await waitFor(() => {
        expect(input).not.toBeDisabled();
      });
    });
  });

  describe('FE-AST-002: Response displays citations', () => {
    it('should display response with citations', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'What does my hemoglobin level mean?{enter}');

      // Wait for response - use a more specific matcher
      await waitFor(() => {
        expect(screen.getByText(/hemoglobin level is 14.2/)).toBeInTheDocument();
      }, { timeout: 5000 });

      // Check citations are displayed
      await waitFor(() => {
        expect(screen.getByText(/Sources:/)).toBeInTheDocument();
      });

      // Check specific citations (they may contain index numbers)
      expect(screen.getByText(/Quest Lab Report/)).toBeInTheDocument();
      expect(screen.getByText(/Medical Reference/)).toBeInTheDocument();
    });

    it('should display verification info when available', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      await waitFor(() => {
        expect(screen.getByText(/2\/2 claims verified/)).toBeInTheDocument();
        expect(screen.getByText(/95% faithfulness/)).toBeInTheDocument();
      });
    });
  });

  describe('FE-AST-003: Empty/error states handled', () => {
    it('should display insufficient context message', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockInsufficientContextResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'What are my cholesterol levels?{enter}');

      await waitFor(() => {
        expect(screen.getByText(/Limited Context Available/)).toBeInTheDocument();
        expect(screen.getByText(/don't have enough information/)).toBeInTheDocument();
      });
    });

    it('should display error message on API failure', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockRejectedValueOnce(new Error('Network error'));

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      await waitFor(() => {
        expect(screen.getByText(/Error/)).toBeInTheDocument();
        expect(screen.getByText(/encountered an error/)).toBeInTheDocument();
      });
    });

    it('should display 501 error message correctly', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockRejectedValueOnce(new Error('501: Not Implemented'));

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      await waitFor(() => {
        expect(screen.getByText(/No AI model is configured/)).toBeInTheDocument();
      });
    });

    it('should display session expired message on 401', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockRejectedValueOnce(new Error('401: Unauthorized'));

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      await waitFor(() => {
        expect(screen.getByText(/session has expired/)).toBeInTheDocument();
      });
    });
  });

  describe('HC-REM-007: Panel selector', () => {
    it('should render panel selector in filter sidebar', () => {
      renderWithProviders(<ExplainAssistant />);

      expect(screen.getByLabelText(/panel/i)).toBeInTheDocument();
    });

    it('should include selected_panel in request', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      // Select a panel
      const panelSelect = screen.getByLabelText(/panel/i);
      await user.selectOptions(panelSelect, 'Lipid Panel');

      // Send a message
      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Explain my lipids{enter}');

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            selected_panel: 'Lipid Panel',
          })
        );
      });
    });

    it('should not include selected_panel when none selected', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test question{enter}');

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            selected_panel: undefined,
          })
        );
      });
    });
  });

  describe('Suggested questions', () => {
    it('should populate input when suggested question is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ExplainAssistant />);

      const suggestedQuestion = screen.getByText('What does my hemoglobin level mean?');
      await user.click(suggestedQuestion);

      const input = screen.getByPlaceholderText('Ask about your results...') as HTMLInputElement;
      expect(input.value).toBe('What does my hemoglobin level mean?');
    });

    it('should disable suggested questions while loading', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockApiPost.mockReturnValueOnce(pendingPromise as Promise<unknown>);

      renderWithProviders(<ExplainAssistant />);

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test{enter}');

      const suggestedQuestion = screen.getByText('What does my hemoglobin level mean?');
      expect(suggestedQuestion).toBeDisabled();

      resolvePromise!(mockChatResponse);

      await waitFor(() => {
        expect(suggestedQuestion).not.toBeDisabled();
      });
    });
  });
});
