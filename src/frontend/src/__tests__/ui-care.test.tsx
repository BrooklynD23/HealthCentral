/**
 * UI-PG-CARE (HC-UIFU-001, HC-UIFU-002, vitest half): the Follow-ups page.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, "UI-PG-CARE". The route
 * stays /care-tasks. The Playwright half (gate G1-G10, the stillness probe and
 * the end-to-end flow) is e2e/ui-care.spec.ts.
 *
 * The API is mocked the way CareTasksService.test.tsx mocks it. A small fake
 * server keeps the rows, so a PATCH changes what the next GET returns and the
 * page's invalidation sees the same truth the user would.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import * as api from '@/services/api';
import type { CarePlanTask, CareTaskCandidate, CareTaskUpdateRequest } from '@/services/careTasks';
import { CareTasksPage } from '@/pages/CareTasksPage';
import { AppToaster } from '@/components/ui/toast';
import { MotionProvider } from '@/motion/MotionProvider';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/api')>()),
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
}));

const SAVE_FAILED = "Couldn't save that change. Try again.";

const OPEN_TASK: CarePlanTask = {
  id: 'task-open',
  title: 'Repeat CBC',
  due_date: '2026-11-20',
  due_date_confidence: 0.8,
  status: 'open',
  source_document_id: 'doc-1',
  source_entity_id: 'entity-1',
  source_quote: 'Repeat CBC in 4 weeks',
  user_note: null,
  created_at: '2026-10-01T00:00:00',
  updated_at: '2026-10-01T00:00:00',
};

const REVIEW_TASK: CarePlanTask = {
  id: 'task-review',
  title: 'Ask about the referral',
  due_date: '2026-12-05',
  due_date_confidence: 0.4,
  status: 'needs_review',
  source_document_id: 'doc-1',
  source_entity_id: 'entity-2',
  source_quote: 'Follow up on the referral',
  user_note: null,
  created_at: '2026-10-02T00:00:00',
  updated_at: '2026-10-02T00:00:00',
};

const DONE_TASK: CarePlanTask = {
  ...OPEN_TASK,
  id: 'task-done',
  title: 'Book the eye check',
  due_date: '2026-10-30',
  status: 'done',
};

const DOCUMENT = { id: 'doc-1', source: 'Lab report, March' };

const CANDIDATE: CareTaskCandidate = {
  title: 'Repeat HbA1c',
  source_entity_id: 'entity-3',
  source_document_id: 'doc-1',
  source_quote: 'Repeat HbA1c in 3 months',
  due_date: '2027-01-05',
  due_date_confidence: 0.7,
  suggested_status: 'open',
};

/**
 * A fake server. GET /care-tasks/ returns the current rows; PATCH
 * /care-tasks/:id changes the row and returns it, as the backend does.
 */
function fakeServer(
  initial: CarePlanTask[],
  extra: { documents?: typeof DOCUMENT[]; candidates?: CareTaskCandidate[] } = {}
) {
  const rows = new Map(initial.map((task) => [task.id, { ...task }]));
  vi.mocked(api.apiGet).mockImplementation((async (endpoint: string) => {
    if (endpoint === '/care-tasks/') return [...rows.values()];
    if (endpoint === '/care-tasks/candidates') return extra.candidates ?? [];
    if (endpoint === '/documents/') return extra.documents ?? [];
    return [];
  }) as typeof api.apiGet);
  vi.mocked(api.apiPatch).mockImplementation((async (endpoint: string, data: unknown) => {
    const row = rows.get(endpoint.replace('/care-tasks/', ''));
    if (!row) throw new Error(`no task at ${endpoint}`);
    row.status = (data as CareTaskUpdateRequest).status ?? row.status;
    return { ...row };
  }) as typeof api.apiPatch);
  return rows;
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MotionProvider>
        <AppToaster />
        <CareTasksPage />
      </MotionProvider>
    </QueryClientProvider>
  );
}

/**
 * The card for one task, found by its title. The card root is the rounded-xl
 * element (the shape ListSkeleton mirrors), so this lookup works before and
 * after the page change.
 */
async function taskCard(title: string): Promise<HTMLElement> {
  const card = (await screen.findByText(title)).closest<HTMLElement>('.rounded-xl');
  expect(card, `card for "${title}"`).not.toBeNull();
  return card!;
}

/** The status the card shows (the morphing label), read from its data attribute. */
function shownStatus(card: HTMLElement): string | null {
  return card.querySelector('[data-care-status]')?.getAttribute('data-care-status') ?? null;
}

beforeEach(() => {
  useAuthStore.setState({ profileId: 'profile-1' });
});

afterEach(() => {
  toast.dismiss();
  cleanup();
});

describe('HC-UIFU-002: the Follow-ups heading', () => {
  it('HC-UIFU-002: the page heading reads "Follow-ups", and it is the only h1 on the page', async () => {
    // Would not notice: a heading that still reads "Care Tasks", or a second h1 beside the page heading (PAGE-H1).
    // RED today: the h1 reads "Care Tasks", so the named lookup fails.
    fakeServer([OPEN_TASK]);
    renderPage();

    await screen.findByRole('heading', { level: 1, name: 'Follow-ups' });
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });
});

describe('HC-UIFU-001: Done and Ignore are optimistic, with an Undo toast', () => {
  it('HC-UIFU-001: Done shows the status toast, and Undo restores the task and PATCHes the previous status', async () => {
    // Would not notice: a Done that PATCHes but shows no toast; an Undo that renders but never calls PATCH; an Undo
    // that sends a fixed status instead of the one the task had before Done; or a card that regroups under "Done"
    // (the card must stay in its "Open" section, so the dates below it do not move, G10).
    // RED today: the page shows no toast and no Undo button, so the test fails at the toast assertion.
    const user = userEvent.setup();
    fakeServer([OPEN_TASK]);
    renderPage();
    const card = await taskCard('Repeat CBC');

    await user.click(within(card).getByRole('button', { name: 'Done' }));

    expect(await screen.findByText('Marked as done.')).toBeInTheDocument();
    await waitFor(() => expect(shownStatus(card)).toBe('done'));
    expect(card.closest('section')).toHaveAttribute('aria-label', 'Open');

    await user.click(await screen.findByRole('button', { name: 'Undo' }));

    await waitFor(() => expect(shownStatus(card)).toBe('open'));
    expect(api.apiPatch).toHaveBeenNthCalledWith(1, '/care-tasks/task-open', { status: 'done' });
    expect(api.apiPatch).toHaveBeenLastCalledWith('/care-tasks/task-open', { status: 'open' });
  });

  it('HC-UIFU-001: Ignore shows the status toast, and Undo PATCHes needs_review back for a task that was in review', async () => {
    // Would not notice: an Ignore that does not reach the same optimistic path as Done; an Undo that restores "open"
    // for a task that was "needs_review" (the previous status is kept, not assumed).
    // RED today: no "Marked as ignored." toast and no Undo button, so the test fails at the toast assertion.
    const user = userEvent.setup();
    fakeServer([REVIEW_TASK]);
    renderPage();
    const card = await taskCard('Ask about the referral');

    await user.click(within(card).getByRole('button', { name: 'Ignore' }));

    expect(await screen.findByText('Marked as ignored.')).toBeInTheDocument();
    await waitFor(() => expect(shownStatus(card)).toBe('ignored'));

    await user.click(await screen.findByRole('button', { name: 'Undo' }));

    await waitFor(() => expect(shownStatus(card)).toBe('needs_review'));
    expect(api.apiPatch).toHaveBeenNthCalledWith(1, '/care-tasks/task-review', { status: 'ignored' });
    expect(api.apiPatch).toHaveBeenLastCalledWith('/care-tasks/task-review', { status: 'needs_review' });
  });

  it('HC-UIFU-001: a failed PATCH shows the change first, then rolls the card back and shows an error toast', async () => {
    // Would not notice: an optimistic Done that never shows (the change waits for the server), a failed PATCH that
    // leaves the card "done" (no rollback), or a rollback that happens with no message to the user.
    // RED today: the page writes nothing optimistically and shows no error toast, so the test fails at the first
    // wait for the "done" label.
    const user = userEvent.setup();
    fakeServer([OPEN_TASK]);
    let refuse: (reason: Error) => void = () => undefined;
    vi.mocked(api.apiPatch).mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          refuse = reject;
        })
    );
    renderPage();
    const card = await taskCard('Repeat CBC');

    await user.click(within(card).getByRole('button', { name: 'Done' }));
    await waitFor(() => expect(shownStatus(card)).toBe('done'));

    refuse(new Error('server refused'));

    expect(await screen.findByText(SAVE_FAILED)).toBeInTheDocument();
    await waitFor(() => expect(shownStatus(card)).toBe('open'));
    expect(within(card).getByRole('button', { name: 'Done' })).toBeEnabled();
  });

  it('HC-UIFU-001: Reopen still PATCHes open for a done task', async () => {
    // Would not notice: a Reopen that the optimistic change broke (it must still send status "open").
    // GREEN today: this is kept behaviour, so it passes before the change too.
    const user = userEvent.setup();
    fakeServer([DONE_TASK]);
    renderPage();
    const card = await taskCard('Book the eye check');

    await user.click(within(card).getByRole('button', { name: 'Reopen' }));

    await waitFor(() => expect(api.apiPatch).toHaveBeenLastCalledWith('/care-tasks/task-done', { status: 'open' }));
  });

  it('HC-UIFU-001: every follow-up date, "Due" and "Suggested due", carries data-t0', async () => {
    // Would not notice: a date that renders without data-t0, so the stillness probe (G10) never samples it. The
    // suggested date only shows after a document is picked, so this test picks one first.
    // RED today: no date element has data-t0, so the first assertion fails.
    const user = userEvent.setup();
    fakeServer([OPEN_TASK, REVIEW_TASK], { documents: [DOCUMENT], candidates: [CANDIDATE] });
    renderPage();
    await screen.findByText('Repeat CBC');
    await screen.findByRole('option', { name: DOCUMENT.source });
    await user.selectOptions(document.getElementById('care-task-doc-select') as HTMLSelectElement, 'doc-1');
    await screen.findByText(/^Suggested due/);

    const dates = Array.from(document.querySelectorAll('p')).filter((p) =>
      /^(Due|Suggested due) /.test(p.textContent ?? '')
    );
    expect(dates).toHaveLength(3);
    for (const date of dates) {
      expect(date).toHaveAttribute('data-t0');
    }
  });
});

describe('empty state action', () => {
  it('the empty state has one action, and it moves focus to the document picker', async () => {
    // Would not notice: an empty state with no action; an action that renders but leaves focus where it was; or a
    // picker that is not the element with id care-task-doc-select.
    // RED today: the empty state has no button, so the lookup fails.
    const user = userEvent.setup();
    fakeServer([], { documents: [DOCUMENT] });
    renderPage();
    await screen.findByText('No care tasks yet');

    await user.click(screen.getByRole('button', { name: 'Choose a document' }));

    expect(document.getElementById('care-task-doc-select')).toHaveFocus();
  });
});
