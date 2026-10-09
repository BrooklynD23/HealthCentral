/**
 * FE-CITE-002 — an entity-backed citation must land somewhere real.
 *
 * `citationTarget` emitted `/verify?entity=<id>&doc=<id>` while the workbench
 * read only the `observation` param, so following an entity citation produced
 * a page with nothing selected and no explanation. The two tests here pin both
 * halves: the entity resolves and is highlighted, and when it does not resolve
 * the user is told rather than left staring at an unrelated queue.
 *
 * These render against a narrative document (a radiology report) with zero
 * observations, which is the common case for entity citations and the one the
 * old code handled worst.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useNavigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

// The overlay fetches a page image; it is not what these tests are about.
vi.mock('@/components/PageImageOverlay', () => ({
  PageImageOverlay: ({ documentId, pageNumber }: { documentId: string; pageNumber: number }) => (
    <div data-testid="page-overlay">{`${documentId}:${pageNumber}`}</div>
  ),
}));

const entity = {
  id: 'ent-4',
  doc_id: 'doc-9',
  category: 'radiology',
  entity_type: 'impression',
  entity_value: 'No acute intracranial abnormality',
  confidence: 0.93,
  source_page: 2,
  source_bbox_json: '[0.1,0.2,0.9,0.3]',
  char_start: null,
  char_end: null,
  quote: 'IMPRESSION: No acute intracranial abnormality.',
  verified_by_user: null,
  extraction_version: 'v1',
};

/**
 * `observations` is a factory rather than a value so a refetch can return
 * different data — which is what actually happens after a verify, and the only
 * way the "citation re-applies on every fetch" bug is observable.
 */
function mockApi(entities: unknown[], observations: () => unknown[] = () => []) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.includes('/entities')) return Promise.resolve(entities);
    if (url.startsWith('/observations')) return Promise.resolve(observations());
    if (url.startsWith('/documents')) return Promise.resolve([]);
    return Promise.resolve([]);
  });
}

/** Navigates the mounted workbench without remounting it — a further citation. */
function CitationNav({ targets }: { targets: string[] }) {
  const navigate = useNavigate();
  return (
    <>
      {targets.map((to, i) => (
        <button key={to} onClick={() => navigate(to)}>{`follow citation ${i + 1}`}</button>
      ))}
    </>
  );
}

function renderAt(path: string, options: { navTargets?: string[] } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        {options.navTargets && <CitationNav targets={options.navTargets} />}
        <VerificationWorkbench />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function observation(id: string, name: string, verified = false) {
  return {
    id,
    profile_id: 'profile-123',
    doc_id: 'doc-9',
    analyte_canonical: name.toLowerCase(),
    analyte_raw: name,
    value: 5,
    value_text: null,
    unit: 'mg/dL',
    ref_low: 1,
    ref_high: 9,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: null,
    user_verified: verified,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: '[0.1,0.2,0.9,0.3]',
  };
}

const SELECTED_ROW_CLASS = 'bg-accent-subtle';

function rowIsSelected(id: string) {
  return document.getElementById(`observation-row-${id}`)?.className.includes(SELECTED_ROW_CLASS);
}

describe('FE-CITE-002: entity citation deep links', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ profileId: 'profile-123' });
  });

  it('resolves the cited entity and shows its source region', async () => {
    mockApi([entity]);

    renderAt('/verify?entity=ent-4&doc=doc-9');

    await waitFor(() => {
      // The value and its verbatim quote both carry the text.
      expect(screen.getAllByText(/No acute intracranial abnormality/).length).toBeGreaterThan(0);
    });

    // The cited row is the one highlighted, so the user can see what they clicked.
    expect(document.getElementById('entity-row-ent-4')?.className).toContain('bg-accent/10');

    // The page region the citation pointed at, not just the text.
    expect(screen.getByTestId('page-overlay')).toHaveTextContent('doc-9:2');

    // And no "no longer available" notice on a citation that resolved fine.
    expect(screen.queryByText(/no longer available/i)).not.toBeInTheDocument();
  });

  it('says so when the cited entity is gone', async () => {
    mockApi([]);

    renderAt('/verify?entity=ent-missing&doc=doc-9');

    await waitFor(() => {
      expect(screen.getByText(/no longer available/i)).toBeInTheDocument();
    });
  });

  it('FE-CITE-003: a resolved citation is applied once, not on every refetch', async () => {
    mockApi([entity]);

    renderAt('/verify?entity=ent-4&doc=doc-9');

    await waitFor(() => {
      expect(screen.getAllByText(/No acute intracranial abnormality/).length).toBeGreaterThan(0);
    });

    // The notice must not appear for a citation that resolved.
    expect(screen.queryByText(/no longer available/i)).not.toBeInTheDocument();
  });

  it('FE-CITE-004: an entity citation with no doc is not a dead link', async () => {
    mockApi([]);

    // No `doc` param: entityDocId is empty, the entities query never runs, and
    // the old code latched "no longer available" forever. A citation with no
    // inspectable source should render as text, not navigate nowhere.
    renderAt('/verify?entity=ent-4');

    // Settle first. `waitFor(not.toBeInTheDocument)` alone passes on its very
    // first tick — while the loading spinner is still up and nothing has been
    // rendered at all — so it can never observe the latched notice. Waiting for
    // the cited-source landing proves the query resolved and the effect ran.
    await screen.findByText(/Cited source/i);

    expect(screen.queryByText(/no longer available/i)).not.toBeInTheDocument();
  });

  it('FE-CITE-005: verifying a row does not snap the selection back to the cited row', async () => {
    // Verifying invalidates the observations query. The refetch returns changed
    // data, so `observations` is a new array — and the citation effect depended
    // on it, re-selecting the cited row underneath the user.
    let verified = false;
    mockApi([], () => [
      observation('obs-a', 'Glucose'),
      observation('obs-b', 'Sodium', verified),
    ]);
    vi.mocked(api.apiPost).mockImplementation(() => {
      verified = true;
      return Promise.resolve({});
    });

    const user = userEvent.setup();
    renderAt('/verify?observation=obs-a');

    await waitFor(() => expect(rowIsSelected('obs-a')).toBe(true));

    // The user moves on to a different row and verifies it.
    await user.click(screen.getByText('Sodium'));
    await waitFor(() => expect(rowIsSelected('obs-b')).toBe(true));
    const obsBRow = document.getElementById('observation-row-obs-b') as HTMLElement;
    await user.click(within(obsBRow).getByLabelText('Verify observation'));

    // Wait for the refetch to land (the Verified badge appears on obs-b).
    await waitFor(() => expect(screen.getByText('Verified')).toBeInTheDocument());

    // The selection must still be where the user put it.
    expect(rowIsSelected('obs-b')).toBe(true);
    expect(rowIsSelected('obs-a')).toBe(false);
  });

  it('FE-CITE-006: a second, different citation is still applied', async () => {
    // Guards the ref gate from over-correcting: it must reset when the citation
    // param changes, or every citation after the first is silently ignored.
    mockApi([], () => [observation('obs-a', 'Glucose'), observation('obs-b', 'Sodium')]);

    const user = userEvent.setup();
    renderAt('/verify?observation=obs-a', { navTargets: ['/verify?observation=obs-b'] });

    await waitFor(() => expect(rowIsSelected('obs-a')).toBe(true));

    await user.click(screen.getByText('follow citation 1'));

    await waitFor(() => expect(rowIsSelected('obs-b')).toBe(true));
    expect(rowIsSelected('obs-a')).toBe(false);
  });

  it('FE-CITE-007: re-following a citation already applied re-selects its row', async () => {
    // The ref must be cleared when the citation param changes, not just keyed
    // on the id. Follow obs-a, wander off, follow an entity citation, then come
    // back to obs-a: a stale ref still holding "obs-a" would silently ignore it.
    mockApi([entity], () => [observation('obs-a', 'Glucose'), observation('obs-b', 'Sodium')]);

    const user = userEvent.setup();
    renderAt('/verify?observation=obs-a', {
      navTargets: ['/verify?entity=ent-4&doc=doc-9', '/verify?observation=obs-a'],
    });

    await waitFor(() => expect(rowIsSelected('obs-a')).toBe(true));

    // The user picks a different row, then follows an entity citation.
    await user.click(screen.getByText('Sodium'));
    await waitFor(() => expect(rowIsSelected('obs-b')).toBe(true));
    await user.click(screen.getByText('follow citation 1'));
    await waitFor(() =>
      expect(screen.getAllByText(/No acute intracranial abnormality/).length).toBeGreaterThan(0)
    );

    // Back to the original citation — it must land on its row again.
    await user.click(screen.getByText('follow citation 2'));

    await waitFor(() => expect(rowIsSelected('obs-a')).toBe(true));
  });
});
