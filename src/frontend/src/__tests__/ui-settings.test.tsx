/**
 * UI-PG-SETTINGS (plan section 7.8): HC-UISET-001 to HC-UISET-005, plus HC-UISET-006 to 009 for the rest of the row.
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
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SettingsPage } from '@/pages/SettingsPage';
import { CONSENT_TEXT_VERSION, PURPOSE_COPY } from '@/components/settings/DataDonationCard';
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

// Rendered unchanged by this row; their own tests cover them.
vi.mock('@/components/settings/RecoveryCodeCard', () => ({ RecoveryCodeCard: () => <div data-testid="recovery-card" /> }));
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

let externalApi: { use_external_api: boolean; provider: string; model: string; api_key_configured: boolean; redaction_break_glass?: boolean };
let externalApiFails = false;
let unmocked: string[] = [];

const responses: Record<string, () => unknown> = {
  '/settings/model': () => modelSettings,
  '/settings/model/tiers': () => tiers,
  '/settings/model/download-progress': () => ({}),
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
    ],
  }),
  '/feedback/stats': () => ({
    total_feedback: 3, positive_count: 2, negative_count: 1, correction_count: 0,
    tag_distribution: {}, model_distribution: {}, provider_distribution: {},
  }),
  '/memory/': () => [],
  '/donation/consents': () => ({
    consents: (['fine_tune', 'synthetic_seed', 'agent_traces'] as const).map((purpose) => ({
      purpose, granted: purpose === 'fine_tune', consent_text_version: purpose === 'fine_tune' ? CONSENT_TEXT_VERSION : null,
      current: purpose === 'fine_tune', granted_at: null, revoked_at: null,
    })),
  }),
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderSettings(url = '/settings') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
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
  return { user, ...view };
}

const openAdvanced = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(await screen.findByRole('button', { name: 'Show advanced settings' }));
  await screen.findByTestId('tier-row-low');
};

beforeEach(() => {
  vi.clearAllMocks();
  unmocked = [];
  externalApiFails = false;
  externalApi = { use_external_api: false, provider: '', model: '', api_key_configured: false, redaction_break_glass: false };
  vi.mocked(api.apiGet).mockImplementation(async (path: string) => {
    const respond = responses[path];
    if (!respond) {
      unmocked.push(path);
      throw new Error(`unmocked GET ${path}`);
    }
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
    expect(screen.queryByTestId('recovery-card')).not.toBeInTheDocument();
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
    expect(screen.getAllByText(/Tesseract/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/GPU/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Phi-4-mini/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Re-detect' })).toBeInTheDocument();
    expect(screen.getByText('Current Status')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export training data' })).toBeEnabled();
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
    // Radix hands focus back on a timer once the content has unmounted.
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
    const download = within(screen.getByTestId('tier-row-mid')).getByRole('button', { name: 'Download' });
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
  const realMatchMedia = window.matchMedia;
  beforeEach(() => {
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
