/**
 * Care Tasks Service Contract Tests (HC-M15 / HC-TASK)
 *
 * Verifies the care-task hooks call the expected backend routes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import {
  useCareTasks,
  useCareTaskCandidates,
  useAcceptCareTask,
  useUpdateCareTask,
} from '@/services/careTasks';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
}));

const TASK = {
  id: 'task-1',
  title: 'Repeat CBC',
  due_date: '2026-04-30',
  due_date_confidence: 0.75,
  status: 'open',
  source_document_id: 'doc-1',
  source_entity_id: 'entity-1',
  source_quote: 'Repeat CBC in 4 weeks',
  user_note: null,
  created_at: '2026-07-10T00:00:00',
  updated_at: '2026-07-10T00:00:00',
};

const CANDIDATE = {
  title: 'Repeat CBC',
  source_entity_id: 'entity-1',
  source_document_id: 'doc-1',
  source_quote: 'Repeat CBC in 4 weeks',
  due_date: '2026-04-30',
  due_date_confidence: 0.75,
  suggested_status: 'open',
};

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{component}</QueryClientProvider>
  );
}

function TasksProbe({ status }: { status?: 'open' | 'done' | 'ignored' | 'needs_review' }) {
  useCareTasks(status);
  return <div>tasks-probe</div>;
}

function CandidatesProbe() {
  useCareTaskCandidates('doc-1');
  return <div>candidates-probe</div>;
}

function AcceptProbe() {
  const mutation = useAcceptCareTask();
  return (
    <button
      onClick={() =>
        mutation.mutate({
          source_entity_id: 'entity-1',
          source_document_id: 'doc-1',
          source_quote: 'Repeat CBC in 4 weeks',
        })
      }
    >
      accept-task
    </button>
  );
}

function UpdateProbe() {
  const mutation = useUpdateCareTask();
  return (
    <button onClick={() => mutation.mutate({ taskId: 'task-1', data: { status: 'done' } })}>
      update-task
    </button>
  );
}

describe('Care tasks service contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.apiGet).mockResolvedValue([TASK]);
    vi.mocked(api.apiPost).mockResolvedValue(TASK);
    vi.mocked(api.apiPatch).mockResolvedValue({ ...TASK, status: 'done' });
  });

  it('FE-TASK-API-001: tasks hook uses GET /care-tasks/', async () => {
    renderWithProviders(<TasksProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/care-tasks/', undefined);
  });

  it('FE-TASK-API-002: tasks hook passes status filter', async () => {
    renderWithProviders(<TasksProbe status="done" />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/care-tasks/', { status: 'done' });
  });

  it('FE-TASK-API-003: candidates hook uses GET /care-tasks/candidates?doc_id=', async () => {
    vi.mocked(api.apiGet).mockResolvedValue([CANDIDATE]);
    renderWithProviders(<CandidatesProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/care-tasks/candidates', { doc_id: 'doc-1' });
  });

  it('FE-TASK-API-004: accept mutation POSTs the candidate payload', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AcceptProbe />);

    await user.click(screen.getByRole('button', { name: /accept-task/i }));

    await waitFor(() => {
      expect(api.apiPost).toHaveBeenCalled();
    });

    expect(api.apiPost).toHaveBeenCalledWith('/care-tasks/accept', {
      source_entity_id: 'entity-1',
      source_document_id: 'doc-1',
      source_quote: 'Repeat CBC in 4 weeks',
    });
  });

  it('FE-TASK-API-005: update mutation PATCHes /care-tasks/{id}', async () => {
    const user = userEvent.setup();
    renderWithProviders(<UpdateProbe />);

    await user.click(screen.getByRole('button', { name: /update-task/i }));

    await waitFor(() => {
      expect(api.apiPatch).toHaveBeenCalled();
    });

    expect(api.apiPatch).toHaveBeenCalledWith('/care-tasks/task-1', { status: 'done' });
  });
});
