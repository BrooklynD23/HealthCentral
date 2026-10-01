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
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExplainAssistant } from '@/pages/ExplainAssistant';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

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
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
}

const mockObservations = [
  { analyte_canonical: 'glucose' },
  { analyte_canonical: 'hemoglobin' },
  { analyte_canonical: 'glucose' },
];

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
    localStorage.clear();
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
    });
    vi.mocked(api.apiGet).mockImplementation(async (url) => {
      if (url === '/observations/') {
        return mockObservations;
      }

      return [];
    });
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

  describe('HC-M003-S01: Document category filter', () => {
    it('should render document category selector with backend-supported option labels', () => {
      renderWithProviders(<ExplainAssistant />);

      const categorySelect = screen.getByLabelText(/document category/i) as HTMLSelectElement;
      const optionLabels = Array.from(categorySelect.options).map((option) => option.textContent);
      const optionValues = Array.from(categorySelect.options).map((option) => option.value);

      expect(categorySelect).toBeInTheDocument();
      expect(categorySelect.value).toBe('');
      expect(optionValues).toEqual(['', 'lab', 'imaging', 'pathology', 'visit_notes']);
      expect(optionLabels).toEqual(['All documents', 'Lab', 'Imaging', 'Pathology', 'Visit Notes']);
    });

    it('should include document_category in request when a category is selected', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const categorySelect = screen.getByLabelText(/document category/i);
      await user.selectOptions(categorySelect, 'lab');

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Explain my lab results{enter}');

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            document_category: 'lab',
          })
        );
      });
    });

    it('should omit document_category after resetting to all documents while preserving other filters', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      const categorySelect = screen.getByLabelText(/document category/i) as HTMLSelectElement;
      const panelSelect = screen.getByLabelText(/panel/i);

      await user.selectOptions(panelSelect, 'Lipid Panel');
      await user.selectOptions(categorySelect, 'lab');
      expect(categorySelect.value).toBe('lab');

      await user.selectOptions(categorySelect, screen.getByRole('option', { name: 'All documents' }));
      expect(categorySelect.value).toBe('');

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

      const request = mockApiPost.mock.calls[0]?.[1] as Record<string, unknown>;
      expect(request).not.toHaveProperty('document_category');
    });

    it('should clear document category alongside existing filters when clear filters is used', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ExplainAssistant />);

      const categorySelect = screen.getByLabelText(/document category/i) as HTMLSelectElement;
      const panelSelect = screen.getByLabelText(/panel/i) as HTMLSelectElement;

      const glucoseFilter = await screen.findByRole('button', { name: 'glucose' });
      await user.click(glucoseFilter);
      await user.selectOptions(panelSelect, 'CBC');
      await user.selectOptions(categorySelect, 'visit_notes');

      expect(screen.getByText(/analytes \(1 selected\)/i)).toBeInTheDocument();
      expect(panelSelect.value).toBe('CBC');
      expect(categorySelect.value).toBe('visit_notes');
      expect(screen.getByRole('button', { name: /clear filters/i })).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /clear filters/i }));

      expect(screen.getByText(/analytes \(0 selected\)/i)).toBeInTheDocument();
      expect(panelSelect.value).toBe('');
      expect(categorySelect.value).toBe('');
      expect(screen.queryByRole('button', { name: /clear filters/i })).not.toBeInTheDocument();
    });
  });

  describe('HC-M24: record-navigation chips', () => {
    it('should render the three "Ask about your records" chips', () => {
      renderWithProviders(<ExplainAssistant />);

      expect(screen.getByText('Which follow-up tasks are open?')).toBeInTheDocument();
      expect(screen.getByText('Show all medication changes')).toBeInTheDocument();
      expect(screen.getByText('What changed since my last visit?')).toBeInTheDocument();
    });

    it('should send the question immediately when a record-query chip is clicked', async () => {
      const user = userEvent.setup();
      const mockApiPost = vi.mocked(api.apiPost);
      mockApiPost.mockResolvedValueOnce(mockChatResponse);

      renderWithProviders(<ExplainAssistant />);

      await user.click(screen.getByText('Which follow-up tasks are open?'));

      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith(
          '/assistant/chat',
          expect.objectContaining({
            question: 'Which follow-up tasks are open?',
          })
        );
      });

      // The chip send bypasses the free-text input, which should stay empty.
      const input = screen.getByPlaceholderText('Ask about your results...') as HTMLInputElement;
      expect(input.value).toBe('');
    });
  });

  describe('Suggested questions', () => {
    it('should populate input when suggested question is clicked', async () => {
      const user = userEvent.setup();
      renderWithProviders(<ExplainAssistant />);

      // Suggested questions are generated from the user's own analytes
      // (derived from /observations/), so wait for the dynamic chip.
      const suggestedQuestion = await screen.findByText("How's my Glucose?");
      await user.click(suggestedQuestion);

      const input = screen.getByPlaceholderText('Ask about your results...') as HTMLInputElement;
      expect(input.value).toBe("How's my Glucose?");
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

      // Wait for the dynamic suggested-question chips to load first.
      const suggestedQuestion = await screen.findByText("How's my Glucose?");

      const input = screen.getByPlaceholderText('Ask about your results...');
      await user.type(input, 'Test{enter}');

      expect(suggestedQuestion).toBeDisabled();

      resolvePromise!(mockChatResponse);

      await waitFor(() => {
        expect(suggestedQuestion).not.toBeDisabled();
      });
    });
  });

  describe('HC-EXT-005: break-glass warning on the chat page', () => {
    function mockExternalApi(external: Record<string, unknown>) {
      vi.mocked(api.apiGet).mockImplementation(async (url) => {
        if (url === '/settings/model/external-api') {
          return {
            use_external_api: true,
            provider: 'openai',
            model: 'gpt-x',
            api_key_configured: true,
            ...external,
          };
        }
        if (url === '/observations/') {
          return mockObservations;
        }
        return [];
      });
    }

    it('HC-EXT-005 shows the alert while the external API is on and break-glass is active', async () => {
      mockExternalApi({ redaction_break_glass: true });
      renderWithProviders(<ExplainAssistant />);

      const warning = await screen.findByText(/privacy protection override is on/i);
      expect(warning.closest('[role="alert"]')).not.toBeNull();
    });

    it('HC-EXT-005b shows no alert when break-glass is off', async () => {
      mockExternalApi({ redaction_break_glass: false });
      renderWithProviders(<ExplainAssistant />);

      await screen.findByText('openai \u00b7 gpt-x');
      expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
    });

    it('HC-EXT-005c shows no alert when an older backend sends no flag', async () => {
      mockExternalApi({});
      renderWithProviders(<ExplainAssistant />);

      await screen.findByText('openai \u00b7 gpt-x');
      expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
    });

    it('HC-EXT-005d shows no alert when the external API is off, even if the flag is true', async () => {
      mockExternalApi({ use_external_api: false, redaction_break_glass: true });
      renderWithProviders(<ExplainAssistant />);

      await screen.findByText('Local model');
      // 'Local model' also renders while the external-api query is pending, so
      // prove that query was issued and its result flushed into a render first.
      await waitFor(() => {
        expect(vi.mocked(api.apiGet)).toHaveBeenCalledWith('/settings/model/external-api');
      });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });
      expect(screen.queryByText(/privacy protection override is on/i)).toBeNull();
    });
  });
});
