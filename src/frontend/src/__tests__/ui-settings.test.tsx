/**
 * UI-PG-SETTINGS (plan section 7.8): HC-UISET-001 to HC-UISET-005, plus HC-UISET-006 to 017 for the rest of the row
 * and for what the reviews found.
 *
 * The page is rendered whole, with the real hooks and the real cards, against a routed `apiGet` mock, so the sections
 * fetch what they would fetch in the app. Only the three auth and encryption cards are stubbed: they are rendered
 * unchanged here (UI-PG-SECURITY restyles them) and each has its own test file.
 *
 *   HC-UISET-001  /settings lands on Profile & security; each ?section= renders its own section and not the others
 *   HC-UISET-002  Advanced is collapsed until "Show advanced settings" is pressed
 *   HC-UISET-003  the break-glass warning's text and role are today's (pin, D12) and nothing animates it
 *   HC-UISET-004  the consent dialog is an AlertDialog (Escape, focus return); its copy and payloads are verbatim
 *   HC-UISET-005  section height at 1440: e2e/ui-settings.spec.ts (jsdom has no layout)
 *   HC-UISET-006  T0 marks: break-glass warning, consent copy, tier availability text
 *   HC-UISET-007  honest tier copy
 *   HC-UISET-008  the switches keep their names and their payloads
 *   HC-UISET-009  on a phone the sections open from a sheet
 *   HC-UISET-010  Profile & security keeps what its cards hold when the section or the layout changes
 *   HC-UISET-011  a running download is followed after the user leaves Advanced and returns, however long they were away
 *   HC-UISET-012  Stop and delete
 *   HC-UISET-013  Current Status does not call an unread External API setting "Off"
 *   HC-UISET-014  the export confirm hands the focus back
 *   HC-UISET-015  the External API payloads carry what was typed
 *   HC-UISET-016  the diagnostics link back to /settings stays in Advanced
 *   HC-UISET-017  the export result is still there after a section change or Hide
 *   HC-UISET-019  the server's answer for a download that died (failed) leaves Download enabled and shows no bar
 *   HC-UISET-020  the tiers request starts with the settings one; the panels wait for both, so nothing shifts and "Run hardware detection first" is not shown while they load
 *   HC-UISET-021  those two reads start when the section mounts: a press after they settle renders no skeleton, a press before them does, and a failed read is asked again on the press
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsPage } from '@/pages/SettingsPage';
import { CONSENT_TEXT_VERSION, PURPOSE_COPY } from '@/components/settings/DataDonationCard';
import { useAuthStore } from '@/stores/authStore';
import * as api from '@/services/api';

vi.mock('@/services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/services/api')>();
  return {
    ...actual,
    apiGet: vi.fn(),
    apiPost: vi.fn(),
    apiPut: vi.fn(),
    apiPatch: vi.fn(),
    apiDelete: vi.fn(),
  };
});

// Rendered unchanged by this row; their own tests cover them. The recovery code card is the real one only when a test
// asks for it (HC-UISET-010: what it holds in state must survive a section change); it sits in the same wrapper either way.
const realCard = vi.hoisted(() => ({ recovery: false }));
vi.mock('@/components/settings/RecoveryCodeCard', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/settings/RecoveryCodeCard')>();
  return { RecoveryCodeCard: () => <div data-testid="recovery-card">{realCard.recovery ? <actual.RecoveryCodeCard /> : null}</div> };
});
vi.mock('@/components/settings/BackupCard', () => ({ BackupCard: () => <div data-testid="backup-card" /> }));
vi.mock('@/components/settings/DangerZone', () => ({ DangerZone: () => <div data-testid="danger-zone" /> }));

const modelSettings = {
  current_tier: 'mid',
  preferred_tier: 'mid',
  recommended_tier: 'mid',
  auto_detect_enabled: false,
  hardware_info: {
    ram_total_gb: 16,
    ram_available_gb: 8,
    cpu_cores: 8,
    cpu_name: 'Test CPU',
    disk_free_gb: 100,
    gpu_available: true,
    gpu_vram_gb: 8,
    gpu_name: 'Test GPU',
    recommended_tier: 'mid',
    max_supported_tier: 'mid',
    detection_timestamp: '2026-11-01T08:00:00Z',
  },
  tier_availability: {},
  ocr_preference_enabled: false,
  ocr_effective: false,
  ocr_blockers: ['tesseract_missing'],
  agent_enabled: true,
};

const capabilities = (context_size: number) => ({
  context_size,
  multimodal: false,
  function_calling: false,
  agentic_capable: false,
});

const tiers = {
  recommended_tier: 'mid',
  tiers: [
    {
      tier: 'low', name: 'Tier 1: Low', model: 'Qwen2.5-0.5B-Instruct', description: 'Fast, lightweight model for basic interpretations',
      available: true, downloaded: true, requirements: { ram_gb: 8, disk_gb: 1 }, can_run: true, capabilities: capabilities(2048),
    },
    {
      tier: 'mid', name: 'Tier 2: Mid', model: 'Phi-4-mini-instruct', description: 'Balanced quality and performance',
      available: false, downloaded: false, requirements: { ram_gb: 16, disk_gb: 3 }, can_run: true, capabilities: capabilities(16384),
    },
    {
      tier: 'high', name: 'Tier 3: High', model: 'BioMistral-7B', description: 'Medical-specialized model for best accuracy',
      available: false, downloaded: false, requirements: { ram_gb: 32, disk_gb: 5 }, can_run: false, capabilities: capabilities(8192),
    },
    // The backend has no display info for these two ids, so it sends the template tier's name and description.
    {
      tier: 'gemma4-e2b', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)',
      available: false, downloaded: false, requirements: { ram_gb: 8, disk_gb: 2 }, can_run: true, capabilities: capabilities(8192),
    },
    {
      tier: 'template', name: 'Template Mode', model: null, description: 'Template-based interpretations (no AI model)',
      available: true, downloaded: true, requirements: { ram_gb: 0, disk_gb: 0 }, can_run: true, capabilities: capabilities(0),
    },
  ],
};

const GB = 1_073_741_824;
let downloadProgress: Record<string, unknown> = {};
let donationRefetch: Promise<void> | null = null;
let donationGranted = true;

let externalApi: { use_external_api: boolean; provider: string; model: string; api_key_configured: boolean; redaction_break_glass?: boolean };
let externalApiFails = false;
let unmocked: string[] = [];

const responses: Record<string, () => unknown> = {
  '/settings/model': () => modelSettings,
  '/settings/model/tiers': () => tiers,
  '/settings/model/download-progress': () => downloadProgress,
  '/settings/model/external-api': () => {
    if (externalApiFails) throw new Error('external-api down');
    return externalApi;
  },
  '/settings/model/timezone': () => ({ timezone: 'UTC' }),
  '/settings/model/voice': () => ({ voice_logging_enabled: false, voice_modal_seen: false }),
  '/settings/model/gamification': () => ({ streaks_hidden: false }),
  '/settings/model/diagnostics': () => ({
    checked_at: '2026-11-01T08:00:00Z',
    components: [
      { id: 'tesseract', label: 'Tesseract OCR', status: 'error', detail: 'Not found on PATH', fix_actions: [] },
      // The backend sends this link as url="/settings" (modules/environment_diagnostics.py).
      { id: 'ollama', label: 'Ollama', status: 'warn', detail: 'Not running', fix_actions: [{ type: 'open_url', label: 'Open settings', url: '/settings' }] },
    ],
  }),
  '/feedback/stats': () => ({
    total_feedback: 3, positive_count: 2, negative_count: 1, correction_count: 0,
    tag_distribution: {}, model_distribution: {}, provider_distribution: {},
  }),
  '/memory/': () => [],
  '/donation/consents': () => ({
    consents: (['fine_tune', 'synthetic_seed', 'agent_traces'] as const).map((purpose) => ({
      purpose, granted: purpose === 'fine_tune' && donationGranted, consent_text_version: purpose === 'fine_tune' ? CONSENT_TEXT_VERSION : null,
      current: purpose === 'fine_tune', granted_at: null, revoked_at: null,
    })),
  }),
  '/profiles/': () => [{ id: 'p1', has_recovery_code: true }],
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

/**
 * `gcTime` shortens how long the query cache keeps a query nobody observes (the app's default is 5 minutes).
 * `retry` is off here so that a failure lands at once; 1 is what the app's query client does.
 */
function renderSettings(url = '/settings', gcTime?: number, retry: number | false = false) {
  const client = new QueryClient({ defaultOptions: { queries: { retry, ...(gcTime === undefined ? {} : { gcTime }) }, mutations: { retry: false } } });
  const user = userEvent.setup();
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <LocationProbe />
        <Routes>
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { user, client, ...view };
}

const openAdvanced = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
  await screen.findByTestId('tier-row-low');
  // The tier card mounts first and the other cards a frame or two after it (so that opening Advanced is a smaller burst of tasks):
  // Export training data is in the last of them.
  await screen.findByRole('button', { name: 'Export training data' });
};

beforeEach(() => {
  vi.clearAllMocks();
  unmocked = [];
  realCard.recovery = false;
  downloadProgress = {};
  donationRefetch = null;
  donationGranted = true;
  useAuthStore.setState({ profileId: 'p1' } as never);
  externalApiFails = false;
  externalApi = { use_external_api: false, provider: '', model: '', api_key_configured: false, redaction_break_glass: false };
  vi.mocked(api.apiGet).mockImplementation(async (path: string) => {
    const respond = responses[path];
    if (!respond) {
      unmocked.push(path);
      throw new Error(`unmocked GET ${path}`);
    }
    // A refetch of the donation choices a test holds back, to see what the page does before it arrives.
    if (path === '/donation/consents' && donationRefetch) await donationRefetch;
    return respond() as never;
  });
  vi.mocked(api.apiPut).mockResolvedValue({} as never);
  vi.mocked(api.apiPatch).mockResolvedValue({} as never);
  vi.mocked(api.apiPost).mockResolvedValue({} as never);
});

afterEach(() => {
  // A call to a path this file does not answer is a call the page makes that the test did not plan for.
  expect(unmocked, 'every GET the page made was answered').toEqual([]);
});

describe('HC-UISET-001: /settings lands on Profile & security; each ?section= renders its own section', () => {
  it('lists the four sections as tabs', async () => {
    renderSettings();
    const tabs = within(await screen.findByRole('tablist')).getAllByRole('tab');
    expect(tabs.map((t) => t.textContent)).toEqual(['Profile & security', 'Preferences', 'Assistant & privacy', 'Advanced']);
  });

  // ui-shell "focus is not obscured": a Tab stop on a panel taller than the screen puts its focus ring under the Safety Rail.
  it('the tab panel holds focusable controls and is not itself a Tab stop', async () => {
    renderSettings();
    await screen.findByTestId('recovery-card');
    expect(screen.getByRole('tabpanel')).toHaveAttribute('tabindex', '-1');
  });

  it('keeps the h1 and the subtitle', async () => {
    renderSettings();
    expect(await screen.findByRole('heading', { level: 1, name: 'Settings' })).toBeInTheDocument();
    expect(screen.getByText('Configure AI models, document import (OCR), and hardware.')).toBeInTheDocument();
  });

  it.each([[''], ['?section=bogus'], ['?section=security']])('%s lands on Profile & security with the three cards and no other section', async (search) => {
    renderSettings(`/settings${search}`);
    expect(await screen.findByTestId('recovery-card')).toBeInTheDocument();
    expect(screen.getByTestId('backup-card')).toBeInTheDocument();
    expect(screen.getByTestId('danger-zone')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Profile & security' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByLabelText('Time zone')).not.toBeInTheDocument();
    expect(screen.queryByRole('switch', { name: 'Use External API' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /advanced settings/i })).not.toBeInTheDocument();
  });

  it('?section=preferences renders time zone, voice and streaks only', async () => {
    renderSettings('/settings?section=preferences');
    expect(await screen.findByLabelText('Time zone')).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Enable Voice Logging' })).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Show streaks' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Preferences' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByTestId('recovery-card')).not.toBeInTheDocument();
    expect(screen.queryByRole('switch', { name: 'Use External API' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /advanced settings/i })).not.toBeInTheDocument();
  });

  it('?section=assistant-privacy renders the assistant, memory, external API and donation cards only', async () => {
    renderSettings('/settings?section=assistant-privacy');
    expect(await screen.findByRole('switch', { name: 'Step-by-step assistant' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Assistant Memory' })).toBeInTheDocument();
    expect(screen.getByRole('switch', { name: 'Use External API' })).toBeInTheDocument();
    expect(screen.getByText(/All model inference runs locally by default/)).toBeInTheDocument();
    expect(screen.getByText('Data donation')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Assistant & privacy' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByTestId('recovery-card')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Time zone')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /advanced settings/i })).not.toBeInTheDocument();
  });

  it('?section=advanced renders the collapsed Advanced section only', async () => {
    renderSettings('/settings?section=advanced');
    expect(await screen.findByRole('button', { name: 'Show advanced settings' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Advanced' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.queryByTestId('recovery-card')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Time zone')).not.toBeInTheDocument();
    expect(screen.queryByRole('switch', { name: 'Use External API' })).not.toBeInTheDocument();
  });

  it('choosing a tab shows its section and writes ?section= to the URL', async () => {
    const { user } = renderSettings();
    await screen.findByTestId('recovery-card');
    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    expect(await screen.findByLabelText('Time zone')).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('?section=preferences');
    // Hidden, not unmounted: HC-UISET-010 is why.
    expect(screen.getByTestId('recovery-card')).not.toBeVisible();
  });

  it('landing on Profile & security fetches no model settings, tiers or diagnostics', async () => {
    renderSettings();
    await screen.findByTestId('recovery-card');
    // Positive first: the section is on screen, so the page has had its chance to fetch.
    const paths = vi.mocked(api.apiGet).mock.calls.map(([path]) => path);
    for (const path of ['/settings/model', '/settings/model/tiers', '/settings/model/diagnostics', '/settings/model/download-progress']) {
      expect(paths, path).not.toContain(path);
    }
  });

  it('model settings failing does not hide the cards of Profile & security', async () => {
    vi.mocked(api.apiGet).mockImplementation(async (path: string) => {
      if (path === '/settings/model') throw new Error('model settings down');
      return (responses[path]?.() ?? {}) as never;
    });
    renderSettings();
    expect(await screen.findByTestId('recovery-card')).toBeInTheDocument();
    expect(screen.queryByText('Failed to load settings. Please try again.')).not.toBeInTheDocument();
  });
});

describe('HC-UISET-002: Advanced is collapsed until "Show advanced settings"', () => {
  it('shows no Tesseract, GPU or tier text until the button is pressed, then shows all of it', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    const button = await screen.findByRole('button', { name: 'Show advanced settings' });
    expect(button).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/Tesseract/)).not.toBeInTheDocument();
    expect(screen.queryByText(/GPU/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Phi-4-mini/)).not.toBeInTheDocument();
    expect(screen.queryByTestId('tier-row-mid')).not.toBeInTheDocument();
    expect(screen.queryByText('Detect Hardware')).not.toBeInTheDocument();
    expect(screen.queryByText('Re-detect')).not.toBeInTheDocument();

    await user.click(button);
    expect(await screen.findByTestId('tier-row-mid')).toBeInTheDocument();
    await screen.findByRole('button', { name: 'Export training data' });
    expect(screen.getAllByText(/Tesseract/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/GPU/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Phi-4-mini/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Re-detect' })).toBeInTheDocument();
    expect(screen.getByText('Current Status')).toBeInTheDocument();
    // Enabled once the feedback counts have arrived.
    await waitFor(() => expect(screen.getByRole('button', { name: 'Export training data' })).toBeEnabled());
  });

  it('an Advanced section that cannot load says so, and the other sections do not', async () => {
    vi.mocked(api.apiGet).mockImplementation(async (path: string) => {
      if (path === '/settings/model') throw new Error('model settings down');
      return (responses[path]?.() ?? {}) as never;
    });
    const { user } = renderSettings('/settings?section=advanced');
    await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
    expect(await screen.findByText('Failed to load settings. Please try again.')).toBeInTheDocument();
  });
});

const WARNING_ACTIVE =
  'Privacy protection override is on. This installation is set to send external AI requests with reduced or no redaction, so names, birth dates and record numbers may leave this device. Each such request is recorded in the audit log.';
const WARNING_UNKNOWN =
  "Could not confirm this installation's privacy settings. If the privacy protection override is on, external AI requests may leave this device with reduced redaction.";

/** The warning's root: found by its text, then walked up to the element that carries the role. */
async function findWarning(role: 'alert' | 'status'): Promise<HTMLElement> {
  const text = await screen.findByText(/Privacy protection override is on|Could not confirm this installation/);
  const root = text.closest<HTMLElement>(`[role="${role}"]`);
  expect(root, `the warning text sits in an element with role=${role}`).not.toBeNull();
  return root!;
}

describe('HC-UISET-003: the break-glass warning keeps its text and role (D12) and nothing animates it', () => {
  // Pins of the component itself: GREEN before this row. Mutated once (text, then role) to show they can fail.
  it('active renders role=alert with today’s text', async () => {
    const { ExternalApiBreakGlassWarning } = await import('@/components/settings/ExternalApiBreakGlassWarning');
    const { container } = render(<ExternalApiBreakGlassWarning active />);
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe(WARNING_ACTIVE);
    expect(container.querySelector('strong')?.textContent).toBe('Privacy protection override is on.');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('unknown renders role=status with today’s text', async () => {
    const { ExternalApiBreakGlassWarning } = await import('@/components/settings/ExternalApiBreakGlassWarning');
    render(<ExternalApiBreakGlassWarning unknown />);
    expect(screen.getByRole('status').textContent).toBe(WARNING_UNKNOWN);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('renders nothing when the flag is false or absent and the state is not unknown', async () => {
    const { ExternalApiBreakGlassWarning } = await import('@/components/settings/ExternalApiBreakGlassWarning');
    const first = render(<ExternalApiBreakGlassWarning active={false} />);
    expect(first.container).toBeEmptyDOMElement();
    first.unmount();
    const second = render(<ExternalApiBreakGlassWarning />);
    expect(second.container).toBeEmptyDOMElement();
  });

  it('the component file has no motion import, no m.* and no AnimatePresence', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/settings/ExternalApiBreakGlassWarning.tsx'), 'utf8');
    expect(source).not.toMatch(/framer-motion/);
    expect(source).not.toMatch(/\bm\.[a-z]+/);
    expect(source).not.toMatch(/AnimatePresence/);
  });

  // RED before this row: the External API card sat inside a StaggerItem (a fade and a slide) on main.
  it.each([
    ['active', { use_external_api: true, redaction_break_glass: true }, 'alert'],
    ['unknown', { use_external_api: true, redaction_break_glass: undefined }, 'status'],
  ])('on the page, the %s warning has no animated ancestor', async (_state, flags, role) => {
    externalApi = { ...externalApi, ...flags } as typeof externalApi;
    renderSettings('/settings?section=assistant-privacy');
    const warning = await findWarning(role as 'alert' | 'status');
    for (let node: HTMLElement | null = warning; node; node = node.parentElement) {
      expect(node.getAttribute('style') ?? '', `${node.tagName}.${node.className}`).not.toMatch(/opacity|transform/);
    }
  });

  it('an external-api request that fails shows the unknown notice', async () => {
    externalApiFails = true;
    renderSettings('/settings?section=assistant-privacy');
    expect((await findWarning('status')).textContent).toBe(WARNING_UNKNOWN);
  });
});

const CONSENT_COPY = [
  'External API Processing',
  'Enabling an external API means your health data will be sent to a third-party server for processing. This includes:',
  'Lab results and observations referenced in your questions',
  'Your conversation messages and context',
  'Analyte names and values for interpretation',
  "Your data will be processed according to the provider's privacy policy. You can disable this at any time to return to local-only processing.",
];

describe('HC-UISET-004: the external API consent is a still AlertDialog and its copy and payloads are verbatim', () => {
  it('opens an alertdialog named Privacy Notice with every line of today’s copy and the two buttons', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    await user.click(await screen.findByRole('switch', { name: 'Use External API' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    for (const line of CONSENT_COPY) expect(within(dialog).getByText(line), line).toBeInTheDocument();
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('data-alert-cancel');
    expect(within(dialog).getByRole('button', { name: 'I Understand, Enable' })).toBeInTheDocument();
    expect(cancel).toHaveFocus();
    // `still`: no opacity, scale or translate on the content (M0).
    expect(dialog.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
  });

  it('Escape closes it, nothing is saved, and focus returns to the switch', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const toggle = await screen.findByRole('switch', { name: 'Use External API' });
    await user.click(toggle);
    await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    // The section hands the focus back by hand once the dialog has closed: the dialog has no Trigger for Radix to return it to.
    await waitFor(() => expect(toggle).toHaveFocus());
    expect(api.apiPut).not.toHaveBeenCalled();
  });

  it('Cancel closes it and saves nothing', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    await user.click(await screen.findByRole('switch', { name: 'Use External API' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(api.apiPut).not.toHaveBeenCalled();
  });

  // Pins of the request bodies, recorded from the page before this row. GREEN before the row.
  it('I Understand, Enable PUTs the consent payload, with consent_acknowledged true', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    await user.click(await screen.findByRole('switch', { name: 'Use External API' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    await user.click(within(dialog).getByRole('button', { name: 'I Understand, Enable' }));
    expect(api.apiPut).toHaveBeenCalledTimes(1);
    expect(api.apiPut).toHaveBeenCalledWith('/settings/model/external-api', {
      use_external_api: true,
      provider: '',
      api_key: '',
      model: '',
      consent_acknowledged: true,
    });
  });

  it('turning the switch off PUTs without opening the dialog, with consent_acknowledged true', async () => {
    externalApi = { ...externalApi, use_external_api: true, provider: 'openai', redaction_break_glass: false };
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const toggle = await screen.findByRole('switch', { name: 'Use External API' });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    await user.click(toggle);
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(api.apiPut).toHaveBeenCalledTimes(1);
    expect(api.apiPut).toHaveBeenCalledWith('/settings/model/external-api', {
      use_external_api: false,
      provider: '',
      api_key: '',
      consent_acknowledged: true,
    });
  });

  it('the export confirm is a still AlertDialog with today’s copy; Cancel exports nothing, Confirm Export posts confirmed:true', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const opener = screen.getByRole('button', { name: 'Export training data' });
    await user.click(opener);
    const dialog = await screen.findByRole('alertdialog', { name: 'Export training data?' });
    expect(
      within(dialog).getByText(
        'This will write JSONL files (DPO pairs, SFT positives, GRPO rewards) to your local filesystem. Redaction is applied to all prompt and response text before writing.'
      )
    ).toBeInTheDocument();
    expect(within(dialog).getByText('Files are stored locally only and never uploaded. No network calls are made.')).toBeInTheDocument();
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('data-alert-cancel');
    expect(cancel).toHaveFocus();
    expect(dialog.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
    await user.click(cancel);
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(api.apiPost).not.toHaveBeenCalled();

    vi.mocked(api.apiPost).mockResolvedValue({ dpo_pairs_count: 1, sft_positives_count: 2, grpo_rewards_count: 3, metadata_path: '/tmp/x' } as never);
    await user.click(opener);
    const again = await screen.findByRole('alertdialog', { name: 'Export training data?' });
    await user.click(within(again).getByRole('button', { name: 'Confirm Export' }));
    await waitFor(() => expect(api.apiPost).toHaveBeenCalledWith('/feedback/export', { confirmed: true }));
    expect(await screen.findByText('Export complete')).toBeInTheDocument();
  });

  it('Stop and delete confirms in a still AlertDialog; the version and the purpose copy are unchanged', async () => {
    expect(CONSENT_TEXT_VERSION).toBe('2026-10-27-v3');
    expect(PURPOSE_COPY.fine_tune.label).toBe('Improve the assistant model');
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const stop = await screen.findByRole('button', { name: `Stop and delete: ${PURPOSE_COPY.fine_tune.label}` });
    await user.click(stop);
    const dialog = await screen.findByRole('alertdialog', { name: 'Confirm stop and delete' });
    expect(
      within(dialog).getByText(
        `Stop donating for “${PURPOSE_COPY.fine_tune.label}” and delete its donated copies? This cannot be undone.`
      )
    ).toBeInTheDocument();
    const cancel = within(dialog).getByRole('button', { name: 'Cancel' });
    expect(cancel).toHaveAttribute('data-alert-cancel');
    expect(cancel).toHaveFocus();
    expect(dialog.getAttribute('style') ?? '').not.toMatch(/opacity|transform/);
    expect(api.apiPut).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Yes, stop and delete' }));
    expect(api.apiPut).toHaveBeenCalledWith('/donation/consents/fine_tune', {
      granted: false,
      consent_text_version: CONSENT_TEXT_VERSION,
    });
  });
});

describe('HC-UISET-006: T0 marks', () => {
  it('the break-glass warning root carries data-t0', async () => {
    externalApi = { ...externalApi, use_external_api: true, redaction_break_glass: true };
    renderSettings('/settings?section=assistant-privacy');
    expect(await findWarning('alert')).toHaveAttribute('data-t0');
  });

  it('the unknown notice carries data-t0', async () => {
    externalApiFails = true;
    renderSettings('/settings?section=assistant-privacy');
    expect(await findWarning('status')).toHaveAttribute('data-t0');
  });

  it('the consent dialog copy is T0', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    await user.click(await screen.findByRole('switch', { name: 'Use External API' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    for (const line of CONSENT_COPY.slice(1)) {
      expect(within(dialog).getByText(line).closest('[data-t0]'), line).not.toBeNull();
    }
  });

  it('the donation consent copy is T0', async () => {
    renderSettings('/settings?section=assistant-privacy');
    const intro = await screen.findByText(/Donating is optional and off by default/);
    expect(intro.closest('[data-t0]')).not.toBeNull();
    expect((await screen.findByText(PURPOSE_COPY.fine_tune.description)).closest('[data-t0]')).not.toBeNull();
  });

  it('each tier row’s Ready, Download or Incompatible is T0', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const ready = within(screen.getByTestId('tier-row-low')).getByText('Ready');
    // The mark is on the word, not on the pressable Button: a Button changes its background on hover and its scale
    // on press, and a T0 node holds still (G10).
    const downloadButton = within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' });
    expect(downloadButton).not.toHaveAttribute('data-t0');
    const download = within(downloadButton).getByText('Download');
    const incompatible = within(screen.getByTestId('tier-row-high')).getByText('Incompatible');
    for (const node of [ready, download, incompatible]) {
      expect(node.closest('[data-t0]'), node.textContent ?? '').not.toBeNull();
      expect(screen.getByTestId(node.closest('[data-testid^="tier-row-"]')!.getAttribute('data-testid')!).contains(node.closest('[data-t0]'))).toBe(true);
    }
  });
});

describe('HC-UISET-007: honest tier copy', () => {
  it('names the mid tier Phi-4-mini, as the backend does', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const row = screen.getByTestId('tier-row-mid');
    expect(within(row).getByText('Mid (Phi-4-mini)')).toBeInTheDocument();
    expect(screen.queryByText(/Phi-3/)).not.toBeInTheDocument();
  });

  it('states the RAM a tier needs from the tier’s own requirements', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const high = within(screen.getByTestId('tier-row-high'));
    expect(high.getByText(/needs 32GB\+ RAM/)).toBeInTheDocument();
    expect(high.queryByText(/8GB/)).not.toBeInTheDocument();
    // Low asks for 8 GB too, so it no longer says only "works on most hardware".
    const low = within(screen.getByTestId('tier-row-low'));
    expect(low.getByText(/lightweight/)).toBeInTheDocument();
    expect(low.getByText(/needs 8GB\+ RAM/)).toBeInTheDocument();
    // Another tier states its own figure.
    expect(within(screen.getByTestId('tier-row-gemma4-e2b')).getByText(/needs 8GB\+ RAM/)).toBeInTheDocument();
  });

  it('never says "no AI model" for a tier that has a model', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const gemma = screen.getByTestId('tier-row-gemma4-e2b');
    expect(within(gemma).getByText(/8K context/)).toBeInTheDocument();
    expect(within(gemma).queryByText(/no AI model/i)).not.toBeInTheDocument();
    expect(within(gemma).queryByText(/Template-based/i)).not.toBeInTheDocument();
    // The template tier really has no model, so its text stays.
    expect(within(screen.getByTestId('tier-row-template')).getByText('Template-based interpretations (no AI model)')).toBeInTheDocument();
  });
});

describe('HC-UISET-008: the switches keep their names and their payloads', () => {
  it('Voice Logging is a switch and PATCHes voice_logging_enabled', async () => {
    const { user } = renderSettings('/settings?section=preferences');
    const toggle = await screen.findByRole('switch', { name: 'Enable Voice Logging' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    await user.click(toggle);
    expect(api.apiPatch).toHaveBeenCalledWith('/settings/model/voice', { voice_logging_enabled: true });
  });

  it('Show streaks is a switch and PATCHes streaks_hidden', async () => {
    const { user } = renderSettings('/settings?section=preferences');
    const toggle = await screen.findByRole('switch', { name: 'Show streaks' });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    await user.click(toggle);
    expect(api.apiPatch).toHaveBeenCalledWith('/settings/model/gamification', { streaks_hidden: true });
  });

  it('the time zone select saves the chosen zone', async () => {
    const { user } = renderSettings('/settings?section=preferences');
    await user.selectOptions(await screen.findByLabelText('Time zone'), 'Asia/Tokyo');
    expect(api.apiPut).toHaveBeenCalledWith('/settings/model/timezone', { timezone: 'Asia/Tokyo' });
  });

  it('OCR is a switch and PATCHes ocr_preference_enabled', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const toggle = screen.getByRole('switch', { name: 'Enable OCR for scans & images' });
    await user.click(toggle);
    expect(api.apiPatch).toHaveBeenCalledWith('/settings/model/ocr', { ocr_preference_enabled: true });
  });

  it('the step-by-step assistant switch keeps its name and description', async () => {
    renderSettings('/settings?section=assistant-privacy');
    const toggle = await screen.findByRole('switch', { name: 'Step-by-step assistant' });
    expect(toggle).toHaveAccessibleDescription(
      'Use the step-by-step assistant. When off, answers come from the simpler search path.'
    );
  });
});

describe('HC-UISET-009: on a phone the sections open from a sheet', () => {
  // Read when each test starts: the setup file defines matchMedia after collection, and later describes need it back.
  let realMatchMedia: typeof window.matchMedia;
  beforeEach(() => {
    realMatchMedia = window.matchMedia;
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: /max-width/.test(query),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })) as unknown as typeof window.matchMedia;
  });
  afterEach(() => {
    window.matchMedia = realMatchMedia;
  });

  it('shows no tab list; a button opens a sheet that lists the four sections, and choosing one switches section', async () => {
    const { user } = renderSettings('/settings?section=preferences');
    expect(await screen.findByLabelText('Time zone')).toBeInTheDocument();
    expect(screen.queryByRole('tablist')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Settings sections/ }));
    const sheet = await screen.findByRole('dialog', { name: 'Settings sections' });
    const choices = within(sheet).getAllByRole('button').filter((b) => b.getAttribute('aria-label') !== 'Close');
    expect(choices.map((b) => b.textContent)).toEqual([
      'Profile & security', 'Preferences', 'Assistant & privacy', 'Advanced',
    ]);
    await user.click(within(sheet).getByRole('button', { name: 'Assistant & privacy' }));
    expect(await screen.findByRole('switch', { name: 'Use External API' })).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('?section=assistant-privacy');
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Settings sections' })).not.toBeInTheDocument());
    expect(screen.queryByLabelText('Time zone')).not.toBeInTheDocument();
  });
});

describe('HC-UISET-010: Profile & security keeps what its cards hold when the section or the layout changes', () => {
  const CODE = 'AAAA-BBBB-CCCC-DDDD';
  type User = ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    realCard.recovery = true;
  });

  const issueCode = async (user: User) => {
    await user.type(await screen.findByLabelText('Confirm your password'), 'pw');
    await user.click(screen.getByRole('button', { name: /recovery code/i }));
  };

  // A recovery code is shown once. The old code is invalid the moment the new one is issued (recovery card text).
  it('a code on screen is still there after the user visits another section and comes back', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({ recovery_code: CODE } as never);
    const { user } = renderSettings();
    await issueCode(user);
    expect(await screen.findByTestId('recovery-code-value')).toHaveTextContent(CODE);
    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    expect(screen.getByTestId('recovery-code-value')).not.toBeVisible();
    await user.click(screen.getByRole('tab', { name: 'Profile & security' }));
    expect(screen.getByTestId('recovery-code-value')).toBeVisible();
    expect(screen.getByTestId('recovery-code-value')).toHaveTextContent(CODE);
  });

  it('a code the server issues while the user is on another section is shown when they come back', async () => {
    let issued!: (value: unknown) => void;
    vi.mocked(api.apiPost).mockImplementation((() => new Promise((resolve) => { issued = resolve; })) as never);
    const { user } = renderSettings();
    await issueCode(user);
    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await act(async () => { issued({ recovery_code: CODE }); });
    await user.click(screen.getByRole('tab', { name: 'Profile & security' }));
    expect(await screen.findByTestId('recovery-code-value')).toHaveTextContent(CODE);
  });

  describe('when the viewport crosses the shell breakpoint', () => {
    let realMatchMedia: typeof window.matchMedia;
    beforeEach(() => {
      realMatchMedia = window.matchMedia;
    });
    afterEach(() => {
      window.matchMedia = realMatchMedia;
    });

    it('a code on screen is still there', async () => {
      vi.mocked(api.apiPost).mockResolvedValue({ recovery_code: CODE } as never);
      const listeners: Array<(event: { matches: boolean }) => void> = [];
      window.matchMedia = vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: (_type: string, listener: (event: { matches: boolean }) => void) => { listeners.push(listener); },
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })) as unknown as typeof window.matchMedia;
      const { user } = renderSettings();
      await issueCode(user);
      await screen.findByTestId('recovery-code-value');
      await act(async () => { listeners.forEach((listener) => listener({ matches: true })); });
      await waitFor(() => expect(screen.queryByRole('tablist')).not.toBeInTheDocument());
      expect(screen.getByTestId('recovery-code-value')).toHaveTextContent(CODE);
    });
  });

  it('a section that was never visited is not mounted (no request, no card)', async () => {
    realCard.recovery = false;
    renderSettings('/settings?section=preferences');
    await screen.findByLabelText('Time zone');
    expect(screen.queryByTestId('recovery-card')).not.toBeInTheDocument();
    expect(vi.mocked(api.apiGet).mock.calls.map(([path]) => path)).not.toContain('/profiles/');
  });
});

describe('HC-UISET-011: a download that is running is followed after the user leaves Advanced and returns', () => {
  const tierProgress = (status: string, progress: number) => ({
    mid: { tier: 'mid', status, progress, downloaded_bytes: progress * GB, total_bytes: GB, path: null, error: null },
  });

  it('start, leave, return: the bar advances, Download stays disabled, and completion refreshes the tiers', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({} as never);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    downloadProgress = tierProgress('downloading', 0.4);
    await user.click(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' }));
    expect(await screen.findByText('40%')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await screen.findByLabelText('Time zone');
    await user.click(screen.getByRole('tab', { name: 'Advanced' }));
    downloadProgress = tierProgress('downloading', 0.9);
    await openAdvanced(user);

    expect(await screen.findByText('90%')).toBeInTheDocument();
    expect(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' })).toBeDisabled();

    const tierFetches = () => vi.mocked(api.apiGet).mock.calls.filter(([path]) => path === '/settings/model/tiers').length;
    const before = tierFetches();
    downloadProgress = tierProgress('completed', 1);
    await waitFor(() => expect(tierFetches()).toBeGreaterThan(before), { timeout: 6000 });
    await waitFor(() => expect(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' })).toBeEnabled());
    // The bar leaves through an exit animation: wait for it.
    await waitFor(() => expect(screen.queryByText('90%')).not.toBeInTheDocument());
  }, 20000);

  // The query cache drops a query nobody observes after gcTime (5 minutes in the app). A model download can take longer.
  it('the user is away longer than the cache keeps the progress: the bar and the disabled Download are still right', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({} as never);
    const { user } = renderSettings('/settings?section=advanced', 20);
    await openAdvanced(user);
    downloadProgress = tierProgress('downloading', 0.4);
    await user.click(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' }));
    expect(await screen.findByText('40%')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await screen.findByLabelText('Time zone');
    // Away for ten times the cache time: the progress entry is gone from the cache.
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 200)); });
    downloadProgress = tierProgress('downloading', 0.9);
    await user.click(screen.getByRole('tab', { name: 'Advanced' }));
    await openAdvanced(user);

    expect(await screen.findByText('90%')).toBeInTheDocument();
    expect(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' })).toBeDisabled();
  }, 20000);

  it('a download the page did not start (a reload, another window) is shown from the first look', async () => {
    downloadProgress = tierProgress('downloading', 0.6);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    expect(await screen.findByText('60%')).toBeInTheDocument();
    expect(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' })).toBeDisabled();
  });

  // The word "Download" is T0 (G10 holds its opacity, colour and rect still). While a download runs the button is disabled,
  // and a disabled Button is half opacity by default; a colour change would break the same rule, so nothing changes: the
  // spinner in the button says the tier is downloading. The press scale and the hover colour act on the Button, not on the mark.
  it('a Download button changes neither opacity nor colour while a download runs, and does not scale on press', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({} as never);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    downloadProgress = tierProgress('downloading', 0.4);
    await user.click(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' }));
    await screen.findByText('40%');
    for (const row of ['tier-row-mid', 'tier-row-gemma4-e2b']) {
      const button = within(screen.getByTestId(row)).getByRole('button', { name: 'Download' });
      expect(button, row).toBeDisabled();
      expect(button.className, row).toContain('disabled:opacity-100');
      expect(button.className, row).not.toMatch(/disabled:text-/);
      expect(button.className, row).toContain('active:scale-100');
      expect(button.querySelector('[data-t0]'), row).toHaveTextContent('Download');
    }
  });
});

describe('HC-UISET-019: a download the server reports as failed (it died, or the profile logged out) can be started again', () => {
  // The backend reports a stored pending or downloading row with no running task as failed (api/model_settings.py,
  // test_model_download_liveness.py HC-UISET-018), so this is the answer the page gets for a dead row after a reload.
  // The fixture is that answer, not a stored row: the HC-UISET-011 fixtures stand for a task that is running.
  const diedAnswer = {
    mid: {
      tier: 'mid', status: 'failed', progress: 0, downloaded_bytes: 0, total_bytes: 0, path: null,
      error: 'The download stopped before it finished. Try again.',
    },
  };

  it('a fresh load gives Download enabled, no bar, and a press reaches the POST', async () => {
    downloadProgress = diedAnswer;
    vi.mocked(api.apiPost).mockResolvedValue({} as never);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);

    const mid = within(screen.getByTestId('tier-row-mid'));
    expect(mid.getByRole('button', { name: 'Download' })).toBeEnabled();
    expect(within(screen.getByTestId('tier-row-gemma4-e2b')).getByRole('button', { name: 'Download' })).toBeEnabled();
    expect(screen.queryByText('Preparing…')).not.toBeInTheDocument();
    expect(screen.queryByText(/^Downloading /)).not.toBeInTheDocument();

    await user.click(mid.getByRole('button', { name: 'Download' }));
    await waitFor(() => expect(api.apiPost).toHaveBeenCalledWith('/settings/model/download', { tier: 'mid' }));
  });

  // A second task can share the key of a first one (a second window's POST). The server reports the tier as `failed` by two
  // real routes: the first task really fails while the second runs (its real error, then completed), or the second task's
  // first write lands after the first dropped the key (the fixed failed answer, then completed). The common order is
  // downloading, downloading, completed. The tiers must still be refreshed after a failed poll, or the finished tier
  // keeps showing Download until the page is reloaded.
  it('downloading, a failed poll, then completed: the tiers are fetched again', async () => {
    const answer = (status: string, progress: number) => ({
      mid: { tier: 'mid', status, progress, downloaded_bytes: progress * GB, total_bytes: GB, path: null, error: null },
    });
    downloadProgress = answer('downloading', 0.6);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    expect(await screen.findByText('60%')).toBeInTheDocument();

    downloadProgress = diedAnswer;
    await waitFor(() => expect(within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' })).toBeEnabled(), { timeout: 6000 });

    const tierFetches = () => vi.mocked(api.apiGet).mock.calls.filter(([path]) => path === '/settings/model/tiers').length;
    const before = tierFetches();
    downloadProgress = answer('completed', 1);
    await waitFor(() => expect(tierFetches()).toBeGreaterThan(before), { timeout: 6000 });
  }, 20000);

  // The data changes on every poll (the sibling tier's bytes move), so the effect runs on every poll. A fixture that repeats
  // one body keeps the same data reference (react-query structural sharing), the effect never re-runs, and the rule
  // "completed now" would pass this test too. Break that pins it: `p.status === 'completed'` alone in the justCompleted rule.
  it('a tier that stays completed while a sibling tier moves on every poll does not refetch the tiers', async () => {
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    let polls = 0;
    vi.mocked(api.apiGet).mockImplementation((async (path: string, ...rest: unknown[]) => {
      if (path === '/settings/model/download-progress') {
        polls += 1;
        return {
          mid: { tier: 'mid', status: 'completed', progress: 100, downloaded_bytes: GB, total_bytes: GB, path: null, error: null },
          low: { tier: 'low', status: 'downloading', progress: polls / 100, downloaded_bytes: polls * 1000, total_bytes: GB, path: null, error: null },
        };
      }
      return (base as (path: string, ...rest: unknown[]) => unknown)(path, ...rest);
    }) as never);
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const tierFetches = () => vi.mocked(api.apiGet).mock.calls.filter(([path]) => path === '/settings/model/tiers').length;
    await waitFor(() => expect(polls).toBeGreaterThanOrEqual(1));
    const polled = polls;
    const before = tierFetches();
    await waitFor(() => expect(polls).toBeGreaterThanOrEqual(polled + 2), { timeout: 8000 });
    expect(tierFetches()).toBe(before);
  }, 20000);
});

describe('HC-UISET-020: the tiers request starts with the settings one, and the panels wait for both', () => {
  const FALSE_LINE = 'Run hardware detection first to see available tiers.';

  /** Holds the reply of the given paths until released, and records the order GETs start and settings answers in. */
  function holdReplies(paths: string[]) {
    const events: string[] = [];
    const release: Record<string, () => void> = {};
    const held: Record<string, Promise<void> | undefined> = {};
    for (const path of paths) held[path] = new Promise<void>((resolve) => { release[path] = resolve; });
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation((async (path: string, ...rest: unknown[]) => {
      if (path === '/settings/model' || path === '/settings/model/tiers') events.push(`${path}:start`);
      if (held[path]) await held[path];
      if (path === '/settings/model') events.push(`${path}:reply`);
      return (base as (path: string, ...rest: unknown[]) => unknown)(path, ...rest);
    }) as never);
    return { events, release };
  }

  it('the tiers GET starts before the settings reply lands', async () => {
    const { events, release } = holdReplies(['/settings/model']);
    const { user } = renderSettings('/settings?section=advanced');
    await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
    await waitFor(() => expect(events).toContain('/settings/model:start'));
    // Nothing has answered yet: a tiers request that starts only after the settings reply is a waterfall.
    await waitFor(() => expect(events).toContain('/settings/model/tiers:start'));
    expect(events).not.toContain('/settings/model:reply');
    release['/settings/model']();
    await screen.findByTestId('tier-row-low');
  });

  // With the settings in and the tiers still out, a tier card of three skeleton blocks becomes seven rows when the tiers
  // land, and every card under it moves (below lg the columns are one). So the panels show one skeleton until both are in.
  it('settings in, tiers still out: one skeleton, no false line, no cards under it; all of it at once when the tiers land', async () => {
    const { events, release } = holdReplies(['/settings/model/tiers']);
    const { user } = renderSettings('/settings?section=advanced');
    await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
    await waitFor(() => expect(events).toContain('/settings/model:reply'));
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 100)); });
    expect(screen.getByTestId('advanced-loading')).toBeInTheDocument();
    expect(screen.queryByText(FALSE_LINE)).not.toBeInTheDocument();
    expect(screen.queryByText('Model Tier')).not.toBeInTheDocument();
    expect(screen.queryByText('Hardware Detection')).not.toBeInTheDocument();

    release['/settings/model/tiers']();
    await screen.findByTestId('tier-row-low');
    expect(screen.queryByTestId('advanced-loading')).not.toBeInTheDocument();
    expect(screen.queryByText(FALSE_LINE)).not.toBeInTheDocument();
    expect(await screen.findByText('Hardware Detection')).toBeInTheDocument();
  });

  it('tiers in, settings still out: the same skeleton, and the tier rows wait for the settings', async () => {
    const { release } = holdReplies(['/settings/model']);
    const { user } = renderSettings('/settings?section=advanced');
    await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 100)); });
    expect(screen.getByTestId('advanced-loading')).toBeInTheDocument();
    expect(screen.queryByTestId('tier-row-low')).not.toBeInTheDocument();
    release['/settings/model']();
    await screen.findByTestId('tier-row-low');
  });

  it('the line stays for a tiers request that settled with nothing to show', async () => {
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation((async (path: string, ...rest: unknown[]) => {
      if (path === '/settings/model/tiers') throw new Error('tiers down');
      return (base as (path: string, ...rest: unknown[]) => unknown)(path, ...rest);
    }) as never);
    const { user } = renderSettings('/settings?section=advanced');
    await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
    expect(await screen.findByText(FALSE_LINE)).toBeInTheDocument();
    expect(screen.queryByTestId('advanced-loading')).not.toBeInTheDocument();
    // The tier card asks again when it mounts (react-query retries an errored query on mount); the panels must not wait on
    // that second request, or the card unmounts, mounts and asks again for as long as the tiers fail.
    const tierFetches = () => vi.mocked(api.apiGet).mock.calls.filter(([path]) => path === '/settings/model/tiers').length;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 300)); });
    const settled = tierFetches();
    expect(settled).toBeLessThanOrEqual(3);
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 300)); });
    expect(tierFetches()).toBe(settled);
    expect(screen.getByText(FALSE_LINE)).toBeInTheDocument();
  });
});

describe('HC-UISET-021: the settings and tiers reads start when the section mounts', () => {
  const FALSE_LINE = 'Run hardware detection first to see available tiers.';
  const FAILED_LINE = 'Failed to load settings. Please try again.';
  const SHOW = 'Show advanced settings';
  const fetches = (path: string) => vi.mocked(api.apiGet).mock.calls.filter(([called]) => called === path).length;
  const sleep = (ms: number) => act(async () => { await new Promise((resolve) => setTimeout(resolve, ms)); });

  /**
   * Counts every time the skeleton enters the DOM from now on. A read of the DOM after the press cannot do this: the skeleton
   * is on the page for one commit when the replies are quick, and a query for it afterwards finds nothing either way.
   */
  function watchSkeleton() {
    let count = 0;
    const read = (records: MutationRecord[]) => {
      for (const record of records) {
        for (const node of record.addedNodes) {
          if (!(node instanceof HTMLElement)) continue;
          if (node.matches('[data-testid="advanced-loading"]') || node.querySelector('[data-testid="advanced-loading"]')) count += 1;
        }
      }
    };
    const observer = new MutationObserver(read);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => {
      read(observer.takeRecords());
      return count;
    };
  }

  /** Waits for both reads to land, and does not throw if they never start: the press that follows is what the test judges. */
  async function settleReads(client: QueryClient) {
    const settled = () => [['model-settings'], ['model-settings', 'tiers']].every((queryKey) => {
      const state = client.getQueryState(queryKey);
      return state !== undefined && state.status !== 'pending' && state.fetchStatus === 'idle';
    });
    for (let tries = 0; tries < 50 && !settled(); tries += 1) await sleep(10);
  }

  /** A press after the reads have landed, with the skeleton watched. The panels are read last: their first card is what ends the press. */
  async function pressAfterSettling(user: ReturnType<typeof userEvent.setup>, client: QueryClient) {
    await settleReads(client);
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    await screen.findByTestId('tier-row-low');
    return skeletons;
  }

  /** Holds every reply to the two reads until released. A mock that answers at once could not tell a press before them from a press after. */
  function holdReads() {
    let release = () => {};
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation((async (path: string, ...rest: unknown[]) => {
      if (path === '/settings/model' || path === '/settings/model/tiers') await gate;
      return (base as (path: string, ...rest: unknown[]) => unknown)(path, ...rest);
    }) as never);
    return () => release();
  }

  /** Answers a read with a failure for as long as the returned object says so. */
  function failRead(failing: string) {
    const control = { fails: true };
    const base = vi.mocked(api.apiGet).getMockImplementation()!;
    vi.mocked(api.apiGet).mockImplementation((async (path: string, ...rest: unknown[]) => {
      if (path === failing && control.fails) throw new Error(`${failing} down`);
      return (base as (path: string, ...rest: unknown[]) => unknown)(path, ...rest);
    }) as never);
    return control;
  }

  // The list is exact, so moving any other card's read up to the section fails here, download-progress first of all: it polls every 2 s.
  it('before any press the section asks for the settings and the tiers and nothing else; the rest wait for the press', async () => {
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    await settleReads(client);
    await sleep(100);
    const asked = vi.mocked(api.apiGet).mock.calls.map(([path]) => path);
    expect([...asked].sort()).toEqual(['/settings/model', '/settings/model/tiers']);

    await user.click(screen.getByRole('button', { name: SHOW }));
    await screen.findByRole('button', { name: 'Export training data' });
    await waitFor(() => expect(fetches('/settings/model/download-progress')).toBeGreaterThanOrEqual(1));
    for (const path of ['/settings/model/external-api', '/settings/model/diagnostics', '/feedback/stats']) {
      expect(fetches(path), path).toBeGreaterThanOrEqual(1);
    }
    // The press shares what the section read: no second request for either.
    expect(fetches('/settings/model')).toBe(1);
    expect(fetches('/settings/model/tiers')).toBe(1);
  });

  it('a press after both have settled renders the panels with no skeleton before them', async () => {
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    const skeletons = await pressAfterSettling(user, client);
    expect(skeletons()).toBe(0);
    await screen.findByRole('button', { name: 'Export training data' });
    expect(skeletons()).toBe(0);
  });

  // The second press and the return to the section are their own events (recurring failure mode 17). The cache time is shorter
  // than the wait, so a read nothing holds has gone by the second press.
  it('Hide and a second press after longer than the cache keeps a read, then away and back: no skeleton on any press', async () => {
    const { user, client } = renderSettings('/settings?section=advanced', 20);
    await screen.findByRole('button', { name: SHOW });
    const skeletons = await pressAfterSettling(user, client);

    await user.click(screen.getByRole('button', { name: 'Hide advanced settings' }));
    await sleep(200);
    await user.click(screen.getByRole('button', { name: SHOW }));
    await screen.findByTestId('tier-row-low');

    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await screen.findByLabelText('Time zone');
    await sleep(200);
    await user.click(screen.getByRole('tab', { name: 'Advanced' }));
    await screen.findByRole('button', { name: SHOW });
    await pressAfterSettling(user, client);
    expect(skeletons()).toBe(0);
  });

  // The reads are held for the whole press, so this is a press before them whatever the box's speed. It is also the control for
  // the watcher: the zero above means nothing unless the same watcher counts a skeleton here.
  it('a press before the replies shows one skeleton and no cards, asks no second time, and all of it comes when they land', async () => {
    const release = holdReads();
    const { user } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    await sleep(100);
    expect(screen.getByTestId('advanced-loading')).toBeInTheDocument();
    expect(skeletons()).toBe(1);
    expect(screen.queryByText('Model Tier')).not.toBeInTheDocument();
    expect(screen.queryByText(FALSE_LINE)).not.toBeInTheDocument();

    release();
    await screen.findByTestId('tier-row-low');
    expect(screen.queryByTestId('advanced-loading')).not.toBeInTheDocument();
    expect(skeletons()).toBe(1);
    expect(fetches('/settings/model')).toBe(1);
    expect(fetches('/settings/model/tiers')).toBe(1);
  });

  it('a settings read that failed before the press is asked again: a skeleton, then the failure line, and the same on a second press', async () => {
    failRead('/settings/model');
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    await settleReads(client);
    const before = fetches('/settings/model');
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    expect(await screen.findByText(FAILED_LINE)).toBeInTheDocument();
    expect(skeletons()).toBe(1);
    expect(fetches('/settings/model')).toBe(before + 1);

    await user.click(screen.getByRole('button', { name: 'Hide advanced settings' }));
    await user.click(screen.getByRole('button', { name: SHOW }));
    expect(await screen.findByText(FAILED_LINE)).toBeInTheDocument();
    expect(skeletons()).toBe(2);
    expect(fetches('/settings/model')).toBe(before + 2);
  });

  it('a settings read that failed before the press and then recovers: a skeleton, then the panels', async () => {
    const down = failRead('/settings/model');
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    await settleReads(client);
    down.fails = false;
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    await screen.findByTestId('tier-row-low');
    expect(skeletons()).toBe(1);
    expect(screen.queryByText(FAILED_LINE)).not.toBeInTheDocument();
  });

  // tiersSettled: the card asks again when it mounts, and that request reads as loading. If the panels waited on it the card
  // would unmount, mount and ask again for as long as the tiers fail: the skeleton count would climb. With the section holding
  // its own observer, the panels' own wait is still once per mount.
  it('a tiers read that failed before the press: one skeleton per press, then the line, and no loop', async () => {
    failRead('/settings/model/tiers');
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    await settleReads(client);
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    expect(await screen.findByText(FALSE_LINE)).toBeInTheDocument();
    await sleep(300);
    const settled = fetches('/settings/model/tiers');
    await sleep(300);
    expect(fetches('/settings/model/tiers')).toBe(settled);
    expect(skeletons()).toBe(1);
    expect(screen.getByText(FALSE_LINE)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Hide advanced settings' }));
    await user.click(screen.getByRole('button', { name: SHOW }));
    expect(await screen.findByText(FALSE_LINE)).toBeInTheDocument();
    await sleep(300);
    expect(skeletons()).toBe(2);
  });

  it('a tiers read that failed before the press and then recovers: the rows, not the line', async () => {
    const down = failRead('/settings/model/tiers');
    const { user, client } = renderSettings('/settings?section=advanced');
    await screen.findByRole('button', { name: SHOW });
    await settleReads(client);
    down.fails = false;
    await user.click(screen.getByRole('button', { name: SHOW }));
    await screen.findByTestId('tier-row-low');
    expect(screen.queryByText(FALSE_LINE)).not.toBeInTheDocument();
  });

  // The app's client retries once, about a second later. A press inside that second joins the request in flight and waits with
  // it, as a press on the old path waited for its own retry. Retries are real here, so this takes a few seconds.
  it('with the app\'s retry, a press while the tiers wait to retry keeps the skeleton through the retry, and then gives the line once', async () => {
    failRead('/settings/model/tiers');
    const { user } = renderSettings('/settings?section=advanced', undefined, 1);
    await screen.findByRole('button', { name: SHOW });
    await waitFor(() => expect(fetches('/settings/model/tiers')).toBe(1));
    const skeletons = watchSkeleton();
    await user.click(screen.getByRole('button', { name: SHOW }));
    await sleep(200);
    expect(screen.getByTestId('advanced-loading')).toBeInTheDocument();

    expect(await screen.findByText(FALSE_LINE, undefined, { timeout: 5000 })).toBeInTheDocument();
    expect(skeletons()).toBe(1);
    // Four in all: the section's request and its retry, which the press joined and did not repeat, then the card's and its retry.
    await waitFor(() => expect(fetches('/settings/model/tiers')).toBe(4), { timeout: 5000 });
    await sleep(200);
    expect(fetches('/settings/model/tiers')).toBe(4);
    expect(skeletons()).toBe(1);
    expect(screen.getByText(FALSE_LINE)).toBeInTheDocument();
  }, 15000);
});

describe('HC-UISET-012: Stop and delete', () => {
  const label = PURPOSE_COPY.fine_tune.label;
  const stopName = `Stop and delete: ${label}`;

  it('stays where it is while its dialog is open, and Cancel gives it the focus back', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const stop = await screen.findByRole('button', { name: stopName });
    await user.click(stop);
    const dialog = await screen.findByRole('alertdialog', { name: 'Confirm stop and delete' });
    // The button is not removed under the dialog: it is the node the focus goes back to, and the rows below it stay put
    // (jsdom has no layout; e2e/ui-settings.spec.ts G10 measures the rows).
    expect(stop.isConnected).toBe(true);
    await user.click(within(dialog).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(stop).toHaveFocus());
    expect(api.apiPut).not.toHaveBeenCalled();
  });

  it('Escape gives the focus back to the button too', async () => {
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const stop = await screen.findByRole('button', { name: stopName });
    await user.click(stop);
    await screen.findByRole('alertdialog', { name: 'Confirm stop and delete' });
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(stop).toHaveFocus());
  });

  it('on success the focus ends on the purpose switch, also while the refetch is still on its way', async () => {
    vi.mocked(api.apiPut).mockResolvedValue({ deleted_count: 2 } as never);
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const toggle = await screen.findByRole('switch', { name: label });
    const stop = await screen.findByRole('button', { name: stopName });
    await user.click(stop);
    const dialog = await screen.findByRole('alertdialog', { name: 'Confirm stop and delete' });

    // The save succeeded, the choices have not been read again: the button is still on the page.
    let release!: () => void;
    donationRefetch = new Promise<void>((resolve) => { release = resolve; });
    donationGranted = false;
    await user.click(within(dialog).getByRole('button', { name: 'Yes, stop and delete' }));
    expect(await screen.findByText('Stopped. 2 donated copies were deleted.')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    expect(stop.isConnected).toBe(true);
    await waitFor(() => expect(toggle).toHaveFocus());

    await act(async () => { release(); });
    await waitFor(() => expect(screen.queryByRole('button', { name: stopName })).not.toBeInTheDocument());
    expect(toggle).toHaveFocus();
  });
});

describe('HC-UISET-013: Current Status does not call an unread External API setting "Off"', () => {
  it('shows Unknown when the External API request fails', async () => {
    externalApiFails = true;
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const row = screen.getByText('External API').closest('div')!;
    await waitFor(() => expect(within(row).getByText('Unknown')).toBeInTheDocument());
    expect(within(row).queryByText('Off')).not.toBeInTheDocument();
  });

  it('shows Off and Enabled when it is read', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    await waitFor(() => expect(within(screen.getByText('External API').closest('div')!).getByText('Off')).toBeInTheDocument());
  });
});

describe('HC-UISET-014: the export confirm hands the focus back', () => {
  it.each([
    ['Cancel', async (dialog: HTMLElement, user: ReturnType<typeof userEvent.setup>) => { await user.click(within(dialog).getByRole('button', { name: 'Cancel' })); }],
    ['Escape', async (_dialog: HTMLElement, user: ReturnType<typeof userEvent.setup>) => { await user.keyboard('{Escape}'); }],
  ])('%s returns the focus to Export training data', async (_name, close) => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    const opener = screen.getByRole('button', { name: 'Export training data' });
    await user.click(opener);
    const dialog = await screen.findByRole('alertdialog', { name: 'Export training data?' });
    await close(dialog, user);
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await waitFor(() => expect(opener).toHaveFocus());
    expect(api.apiPost).not.toHaveBeenCalled();
  });
});

describe('HC-UISET-015: the External API payloads carry what was typed', () => {
  it('off sends the provider and an empty key; off then on sends the typed provider, key and model', async () => {
    externalApi = { ...externalApi, use_external_api: true, redaction_break_glass: false };
    vi.mocked(api.apiPut).mockImplementation((async (path: string, body: { use_external_api: boolean }) => {
      if (path === '/settings/model/external-api') externalApi = { ...externalApi, use_external_api: body.use_external_api };
      return {};
    }) as never);
    const { user } = renderSettings('/settings?section=assistant-privacy');
    const toggle = await screen.findByRole('switch', { name: 'Use External API' });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
    await user.selectOptions(await screen.findByLabelText('Provider'), 'openai');
    await user.type(screen.getByPlaceholderText('sk-...'), 'sk-typed-key');
    await user.type(screen.getByPlaceholderText('e.g. gpt-4o, claude-sonnet'), 'gpt-4o');

    await user.click(toggle);
    expect(api.apiPut).toHaveBeenLastCalledWith('/settings/model/external-api', {
      use_external_api: false,
      provider: 'openai',
      api_key: '',
      consent_acknowledged: true,
    });
    await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'false'));

    await user.click(toggle);
    const dialog = await screen.findByRole('alertdialog', { name: 'Privacy Notice' });
    await user.click(within(dialog).getByRole('button', { name: 'I Understand, Enable' }));
    expect(api.apiPut).toHaveBeenLastCalledWith('/settings/model/external-api', {
      use_external_api: true,
      provider: 'openai',
      api_key: 'sk-typed-key',
      model: 'gpt-4o',
      consent_acknowledged: true,
    });
  });
});

describe('HC-UISET-016: the diagnostics link back to /settings stays in Advanced', () => {
  it('Open /settings from a fix dialog goes to ?section=advanced', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    await user.click(await screen.findByRole('button', { name: 'Fix Ollama' }));
    const link = await screen.findByRole('link', { name: 'Open /settings' });
    expect(link).toHaveAttribute('href', '/settings?section=advanced');
    await user.click(link);
    expect(screen.getByTestId('location')).toHaveTextContent('?section=advanced');
    expect(screen.getByRole('tab', { name: 'Advanced' })).toHaveAttribute('aria-selected', 'true');
  });
});

describe('HC-UISET-017: the export result is still there after a section change or Hide', () => {
  const exportOnce = async (user: ReturnType<typeof userEvent.setup>) => {
    vi.mocked(api.apiPost).mockResolvedValue({
      dpo_pairs_count: 4, sft_positives_count: 7, grpo_rewards_count: 9, metadata_path: '/home/test/exports/run-1/metadata.json',
    } as never);
    await user.click(screen.getByRole('button', { name: 'Export training data' }));
    const dialog = await screen.findByRole('alertdialog', { name: 'Export training data?' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirm Export' }));
    expect(await screen.findByText('Export complete')).toBeInTheDocument();
  };
  const expectResult = () => {
    expect(screen.getByText('Export complete')).toBeInTheDocument();
    expect(screen.getByText(/4 DPO pairs · 7 SFT positives · 9 reward records/)).toBeInTheDocument();
    expect(screen.getByText('/home/test/exports/run-1/metadata.json')).toBeInTheDocument();
  };

  // It is the only statement of how many records were written and where the file is.
  it('after another section and back', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    await exportOnce(user);
    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await screen.findByLabelText('Time zone');
    await user.click(screen.getByRole('tab', { name: 'Advanced' }));
    await openAdvanced(user);
    expectResult();
  });

  // An export that is still running when the user leaves ends with its result on the page they come back to.
  it('when the export finishes while the user is on another section', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    let finish!: (value: unknown) => void;
    vi.mocked(api.apiPost).mockImplementation((() => new Promise((resolve) => { finish = resolve; })) as never);
    await user.click(screen.getByRole('button', { name: 'Export training data' }));
    await user.click(within(await screen.findByRole('alertdialog', { name: 'Export training data?' })).getByRole('button', { name: 'Confirm Export' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument());
    await user.click(screen.getByRole('tab', { name: 'Preferences' }));
    await screen.findByLabelText('Time zone');
    await act(async () => {
      finish({ dpo_pairs_count: 4, sft_positives_count: 7, grpo_rewards_count: 9, metadata_path: '/home/test/exports/run-1/metadata.json' });
    });
    await user.click(screen.getByRole('tab', { name: 'Advanced' }));
    await openAdvanced(user);
    expectResult();
  });

  it('after Hide advanced settings and Show', async () => {
    const { user } = renderSettings('/settings?section=advanced');
    await openAdvanced(user);
    await exportOnce(user);
    await user.click(screen.getByRole('button', { name: 'Hide advanced settings' }));
    expect(screen.queryByText('Export complete')).not.toBeInTheDocument();
    await openAdvanced(user);
    expectResult();
  });
});
