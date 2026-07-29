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
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
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

function mockApi(entities: unknown[]) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.includes('/entities')) return Promise.resolve(entities);
    if (url.startsWith('/observations')) return Promise.resolve([]);
    if (url.startsWith('/documents')) return Promise.resolve([]);
    return Promise.resolve([]);
  });
}

function renderAt(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <VerificationWorkbench />
      </MemoryRouter>
    </QueryClientProvider>
  );
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
});
