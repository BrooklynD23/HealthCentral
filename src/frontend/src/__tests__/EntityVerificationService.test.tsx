/**
 * Entity Verification Service Contract Tests (HC-M12 / HC-SPAN)
 *
 * Verifies the entity verification hooks call the expected backend routes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import {
  useDocumentEntities,
  useSetEntityVerification,
  setEntityVerification,
} from '@/services/documentCategories';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
}));

const ENTITY = {
  id: 'entity-1',
  doc_id: 'doc-1',
  category: 'imaging',
  entity_type: 'modality',
  entity_value: 'MRI',
  confidence: 0.95,
  source_page: null,
  char_start: 17,
  char_end: 20,
  quote: 'MRI',
  verified_by_user: null,
  extraction_version: 'rule-v2',
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

function EntitiesProbe() {
  useDocumentEntities('doc-1');
  return <div>entities-probe</div>;
}

function VerifyProbe({ verified }: { verified: boolean | null }) {
  const mutation = useSetEntityVerification();
  return (
    <button
      onClick={() =>
        mutation.mutate({ docId: 'doc-1', entityId: 'entity-1', verified })
      }
    >
      set-verification
    </button>
  );
}

describe('Entity verification service contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.apiGet).mockResolvedValue([ENTITY]);
    vi.mocked(api.apiPatch).mockResolvedValue({ ...ENTITY, verified_by_user: true });
  });

  it('FE-SPAN-API-001: entities hook uses /documents/{id}/entities', async () => {
    renderWithProviders(<EntitiesProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/documents/doc-1/entities');
  });

  it('FE-SPAN-API-002: setEntityVerification uses PATCH .../entities/{id}/verification', async () => {
    await setEntityVerification('doc-1', 'entity-1', true);

    expect(api.apiPatch).toHaveBeenCalledWith(
      '/documents/doc-1/entities/entity-1/verification',
      { verified: true }
    );
  });

  it('FE-SPAN-API-003: verification mutation sends verified=false for reject', async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerifyProbe verified={false} />);

    await user.click(screen.getByRole('button', { name: /set-verification/i }));

    await waitFor(() => {
      expect(api.apiPatch).toHaveBeenCalled();
    });

    expect(api.apiPatch).toHaveBeenCalledWith(
      '/documents/doc-1/entities/entity-1/verification',
      { verified: false }
    );
  });

  it('FE-SPAN-API-004: verification mutation sends verified=null to reset', async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerifyProbe verified={null} />);

    await user.click(screen.getByRole('button', { name: /set-verification/i }));

    await waitFor(() => {
      expect(api.apiPatch).toHaveBeenCalled();
    });

    expect(api.apiPatch).toHaveBeenCalledWith(
      '/documents/doc-1/entities/entity-1/verification',
      { verified: null }
    );
  });
});
