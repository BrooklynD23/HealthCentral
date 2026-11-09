/**
 * OCR-COPY-ENGINE: patient-facing copy names the bundled OCR reader, not Tesseract.
 *
 *   HC-OCE-001  the inbox "OCR Required" badge title (plan row 1)
 *   HC-OCE-002  the Verification Workbench pending_ocr hint (row 2)
 *   HC-OCE-003  the Document import (OCR) card: no Tesseract, rows 4-6, switch above the status box
 *   HC-OCE-004  Off / Blocked display rules (rows 3, 7, 8); the tesseract_missing code stays
 *
 * Strings are asserted verbatim against docs/plans/2026-11-07-three-rows-plan.md (owner-approved).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DocumentInbox } from '@/pages/DocumentInbox';
import { VerificationWorkbench } from '@/pages/VerificationWorkbench';
import { SettingsPage } from '@/pages/SettingsPage';
import { useAuthStore } from '@/stores/authStore';
import * as api from '@/services/api';

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return { ...actual, apiGet: vi.fn(), apiPost: vi.fn(), apiPut: vi.fn(), apiPatch: vi.fn(), apiDelete: vi.fn() };
});
vi.mock('@/components/PageImageOverlay', () => ({ PageImageOverlay: () => <div>Document preview</div> }));
vi.mock('@/components/settings/RecoveryCodeCard', () => ({ RecoveryCodeCard: () => <div /> }));
vi.mock('@/components/settings/BackupCard', () => ({ BackupCard: () => <div /> }));
vi.mock('@/components/settings/DangerZone', () => ({ DangerZone: () => <div /> }));

const ROW1 =
  'This scan needs text recognition before its values can be read. In Settings, turn on document OCR under Document import (the reader is built in; your server must allow OCR with OCR_ENABLED).';
const ROW2 =
  'This scan needs text recognition. In Settings, turn on document OCR under Document import — the OCR reader is built into the app. Your server must allow OCR (OCR_ENABLED). Or use a clearer scan.';
const ROW3 = 'The built-in OCR reader could not start. Re-run the backend setup (dev.ps1 / dev.sh) or reinstall dependencies.';
const ROW4 = 'Turn on document OCR above for this profile.';
const ROW5 =
  'Read text from scanned PDFs and lab images with the built-in reader. Your preference applies to this profile; the server must also allow OCR (OCR_ENABLED).';
const ROW6 = 'OCR is active for this profile (built-in reader + server allow).';

const pendingDoc = {
  id: 'doc-ocr',
  profile_id: 'p1',
  doc_type: 'lab_image',
  source: 'scan.png',
  status: 'pending_ocr',
  page_count: 1,
  collection_date: null,
  imported_at: '2026-07-13T09:00:00',
  parsed_at: null,
  verified_at: null,
};

function client() {
  return new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 't', profileId: 'p1', profileName: 'P' });
});

describe('HC-OCE-001: inbox badge title', () => {
  it('names the built-in reader and not Tesseract', async () => {
    vi.mocked(api.apiGet).mockImplementation(async (url: string) => (url.startsWith('/documents') ? [pendingDoc] : []) as never);
    render(
      <QueryClientProvider client={client()}>
        <BrowserRouter>
          <DocumentInbox />
        </BrowserRouter>
      </QueryClientProvider>
    );
    const badge = await screen.findByText('OCR Required');
    const titled = badge.closest('[title]') as HTMLElement;
    expect(titled.getAttribute('title')).toBe(ROW1);
    expect(titled.getAttribute('title')).not.toMatch(/Tesseract/);
  });
});

describe('HC-OCE-002: workbench pending_ocr hint', () => {
  it('says the reader is built in', async () => {
    window.history.pushState({}, '', '/verify?doc=doc-ocr&mode=all');
    vi.mocked(api.apiGet).mockImplementation(async (url: string) => (url.startsWith('/documents') ? [pendingDoc] : []) as never);
    render(
      <QueryClientProvider client={client()}>
        <BrowserRouter>
          <VerificationWorkbench />
        </BrowserRouter>
      </QueryClientProvider>
    );
    await screen.findByRole('button', { name: /continue ocr/i });
    const hints = await screen.findAllByText(ROW2);
    expect(hints.length).toBeGreaterThan(0);
    expect(screen.queryByText(/Tesseract/)).not.toBeInTheDocument();
  });
});

function modelSettings(over: Record<string, unknown>) {
  return {
    current_tier: 'template',
    preferred_tier: 'template',
    recommended_tier: 'template',
    auto_detect_enabled: false,
    hardware_info: null,
    tier_availability: {},
    ocr_preference_enabled: false,
    ocr_effective: false,
    ocr_blockers: [],
    agent_enabled: true,
    ...over,
  };
}

async function openOcrCard(over: Record<string, unknown>) {
  vi.mocked(api.apiGet).mockImplementation((async (path: string) => {
    if (path === '/settings/model') return modelSettings(over);
    if (path === '/settings/model/tiers') return { recommended_tier: 'template', tiers: [] };
    if (path === '/settings/model/download-progress') return {};
    if (path === '/settings/model/external-api')
      return { use_external_api: false, provider: '', model: '', api_key_configured: false, redaction_break_glass: false };
    if (path === '/settings/model/diagnostics') return { checked_at: '2026-11-01T08:00:00Z', components: [] };
    throw new Error(`unmocked ${path}`);
  }) as never);
  const user = userEvent.setup();
  render(
    <QueryClientProvider client={client()}>
      <MemoryRouter initialEntries={['/settings?section=advanced']}>
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
  await screen.findByRole('button', { name: 'Export training data' });
  return { user };
}

function ocrCard() {
  let el: HTMLElement | null = screen.getByText('Document import (OCR)');
  while (el && !within(el).queryByRole('switch') && !within(el).queryByRole('checkbox')) el = el.parentElement;
  return el as HTMLElement;
}

describe('HC-OCE-003: Document import (OCR) card copy', () => {
  it('has no Tesseract, shows rows 4-6, and puts the switch above the status box', async () => {
    await openOcrCard({ ocr_blockers: ['user_disabled'] });
    const card = ocrCard();
    expect(within(card).queryByText(/Tesseract/)).not.toBeInTheDocument();
    expect(within(card).getByText(ROW4)).toBeInTheDocument();
    expect(card.textContent).toContain(ROW5.replace('(OCR_ENABLED)', '(OCR_ENABLED)'));
    const sw = within(card).getByText('Enable OCR for scans & images');
    const status = within(card).getByText(ROW4);
    expect(sw.compareDocumentPosition(status) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('active state reads row 6', async () => {
    await openOcrCard({ ocr_preference_enabled: true, ocr_effective: true, ocr_blockers: [] });
    expect(within(ocrCard()).getByText(ROW6)).toBeInTheDocument();
  });
});

describe('HC-OCE-004: Off / Blocked display rules', () => {
  it('only user_disabled: "OCR is off for this profile" and Off, no Blocked', async () => {
    await openOcrCard({ ocr_blockers: ['user_disabled'] });
    const card = ocrCard();
    expect(within(card).getByText('OCR is off for this profile')).toBeInTheDocument();
    const row = screen.getByText('OCR (profile)').parentElement as HTMLElement;
    expect(within(row).getByText('Off')).toBeInTheDocument();
    expect(screen.queryByText('Blocked')).not.toBeInTheDocument();
    expect(screen.queryByText('OCR is blocked')).not.toBeInTheDocument();
  });

  it('admin + user blockers stay Blocked', async () => {
    await openOcrCard({ ocr_blockers: ['disabled_by_admin', 'user_disabled'] });
    expect(within(ocrCard()).getByText('OCR is blocked')).toBeInTheDocument();
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('tesseract_missing stays Blocked and shows row 3', async () => {
    await openOcrCard({ ocr_blockers: ['tesseract_missing'] });
    expect(within(ocrCard()).getByText(ROW3)).toBeInTheDocument();
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });

  it('an empty blocker list that is not effective stays Blocked', async () => {
    await openOcrCard({ ocr_blockers: [] });
    expect(screen.getByText('Blocked')).toBeInTheDocument();
  });
});
