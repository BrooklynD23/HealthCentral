/**
 * UI-PG-MEDS (plan section 7.7): HC-UIMED-001 to HC-UIMED-004, plus the page rules the medication pages share
 * (no raw colour, the adherence ring is final, T0 on the dose, schedule times and adherence figures).
 *
 * Written red first. Each test says in its comment what it would not notice.
 */
import { afterEach, describe, it, expect, vi } from 'vitest';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { StrictMode, useState } from 'react';
import type { AdherenceStats } from '@/services/types';
import { MedicationCard } from '@/components/medication-coach/MedicationCard';
import { DoseLoggingModal } from '@/components/medication-coach/DoseLoggingModal';
import { BadgeToast } from '@/components/medication-coach/BadgeToast';
import { AdherenceDashboard } from '@/components/medication-coach/AdherenceDashboard';
import { MedicationOverlay } from '@/components/MedicationOverlay';
import { NotificationSettings } from '@/pages/NotificationSettings';
import { MedicationCoach } from '@/pages/MedicationCoach';
import { notify } from '@/components/ui/toast';

const fixtures = vi.hoisted(() => {
  const medication = {
    id: 'med-1',
    profile_id: 'profile-1',
    name: 'Metformin',
    generic_name: 'metformin',
    dosage_amount: 500,
    dosage_unit: 'mg',
    dosage_form: 'tablet',
    frequency: 'twice_daily',
    instructions: null,
    is_active: true,
    reminder_enabled: true,
    started_at: '2026-01-01T00:00:00',
    ended_at: null,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-02-01T00:00:00',
    schedules: [
      {
        id: 'sched-1',
        medication_id: 'med-1',
        schedule_label: 'morning',
        target_time: '08:00',
        reminder_offset_minutes: 15,
        is_active: true,
        adaptive_window_start: null,
        adaptive_window_end: null,
      },
    ],
  };
  const notificationSettings = {
    medication_id: 'med-1',
    enabled: true,
    quiet_hours_start: '22:00',
    quiet_hours_end: '07:00',
    max_reminders_per_dose: 3,
    initial_offset_minutes: 0,
    nudge_delay_minutes: 15,
    alert_delay_minutes: 30,
    weekend_enabled: true,
    celebration_enabled: true,
  };
  // Set by a test to replace the one-medication list; reset to null after it.
  return { medication, notificationSettings, medicationList: null as null | unknown[] };
});

vi.mock('@/components/ui/toast', () => ({ notify: vi.fn(), AppToaster: () => null }));

vi.mock('@/services/medications', () => ({
  useMedications: () => ({ data: fixtures.medicationList ?? [fixtures.medication], isLoading: false, isError: false }),
  useCreateMedication: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateMedication: () => ({ mutate: vi.fn(), isPending: false }),
  useLogDose: () => ({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/services', () => ({
  useBadges: () => ({ data: { badges: [] }, isLoading: false }),
  useStreaks: () => ({ data: undefined }),
  useDocuments: () => ({ data: [] }),
  useMedReconciliation: () => ({ data: [], isLoading: false }),
}));

vi.mock('@/services/modelSettings', () => ({
  useGamificationSettings: () => ({ data: { streaks_hidden: false } }),
}));

vi.mock('@/services/notifications', () => ({
  useNotificationSettings: () => ({ data: fixtures.notificationSettings, isLoading: false, isError: false }),
  useUpdateNotificationSettings: () => ({ mutate: vi.fn(), isPending: false, isSuccess: false }),
  useNotificationHistory: () => ({
    data: {
      total: 0,
      reminders: [],
      stats: { sent_last_7_days: 0, sent_last_30_days: 0, interaction_rate_7d: 0, by_type: {} },
    },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
  useNotificationSchedulerStatus: () => ({
    data: {
      state: 'stopped',
      active_platform: null,
      registered_profiles: 0,
      notifications_sent_this_hour: 0,
      last_check: null,
    },
    isLoading: false,
    isError: false,
  }),
  useSendTestNotification: () => ({ mutate: vi.fn(), isPending: false }),
  useSendMedicationTestNotification: () => ({ mutate: vi.fn(), isPending: false }),
}));

const med = fixtures.medication as unknown as Parameters<typeof MedicationCard>[0]['medication'];

function LocationProbe() {
  const location = useLocation();
  return <p data-testid="location">{`${location.pathname}${location.search}`}</p>;
}

describe('HC-UIMED-001: MedicationCard and MedicationOverlay are router links', () => {
  // Would not notice: a Card with onClick and no link role (the state today).
  it('the card is a link to its detail page', () => {
    render(
      <MemoryRouter>
        <MedicationCard medication={med} onQuickLog={vi.fn()} />
      </MemoryRouter>
    );
    expect(screen.getByRole('link', { name: /Metformin/ })).toHaveAttribute('href', '/medications/med-1');
  });

  // Would not notice: a link that is not in the tab order (Tab must reach it before the Log button).
  it('Enter on the focused card opens the detail page', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/medications']}>
        <Routes>
          <Route path="/medications" element={<MedicationCard medication={med} onQuickLog={vi.fn()} />} />
          <Route path="/medications/:medicationId" element={<p>DETAIL PAGE</p>} />
        </Routes>
      </MemoryRouter>
    );
    await user.tab();
    expect(screen.getByRole('link', { name: /Metformin/ })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByText('DETAIL PAGE')).toBeInTheDocument();
  });

  // Would not notice: a plain anchor that reloads the page. jsdom does not navigate, so the router
  // location stays put and the detail route does not render.
  it('a MedicationOverlay chip navigates inside the router', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/trends']}>
        <Routes>
          <Route
            path="/trends"
            element={
              <MedicationOverlay
                medications={[
                  {
                    medicationId: 'med-1',
                    medicationName: 'Metformin',
                    startedAt: '2026-01-01',
                    endedAt: null,
                    dosageLabel: '500 mg',
                  },
                ]}
              />
            }
          />
          <Route path="/medications/:medicationId" element={<p>DETAIL PAGE</p>} />
        </Routes>
      </MemoryRouter>
    );
    await user.click(screen.getByRole('link', { name: 'View Metformin details' }));
    expect(screen.getByText('DETAIL PAGE')).toBeInTheDocument();
  });

  // Blind spot: the class name only. A hover lift written another way (an inline style, or the same shadow
  // under another utility) would pass this check.
  it('the card has no hover lift: it is not one interactive card, the Log button sits beside the link', () => {
    const { container } = render(
      <MemoryRouter>
        <MedicationCard medication={med} onQuickLog={vi.fn()} />
      </MemoryRouter>
    );
    expect(container.querySelector('.hover\\:shadow-elevated')).toBeNull();
  });
});

describe('HC-UIMED-002: the dose dialog is a modal dialog with Escape, focus trap and focus return', () => {
  const renderModal = (onClose = vi.fn()) =>
    render(<DoseLoggingModal medicationName="Metformin" onSubmit={vi.fn()} onClose={onClose} />);

  // Would not notice: a dialog whose accessible name is something other than the title.
  it('is a dialog named Log Dose', () => {
    renderModal();
    expect(screen.getByRole('dialog', { name: 'Log Dose' })).toBeInTheDocument();
  });

  // Would not notice: a dialog that ignores Escape and leaves the close to the button only.
  it('Escape closes it', async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderModal(onClose);
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // Would not notice: a focus trap that holds focus only on the first Tab. Twelve Tabs cover the
  // whole control set (toggle, chips, notes, submit, close) more than once.
  it('keeps focus inside the dialog while tabbing', async () => {
    const user = userEvent.setup();
    renderModal();
    const dialog = screen.getByRole('dialog', { name: 'Log Dose' });
    for (let i = 0; i < 12; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }
  });

  // Would not notice: focus left on document.body after close. The opener must be focused again.
  it('returns focus to the opener when it closes', async () => {
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            open-dose
          </button>
          {open && (
            <DoseLoggingModal
              medicationName="Metformin"
              onSubmit={vi.fn()}
              onClose={() => setOpen(false)}
            />
          )}
        </>
      );
    }
    render(<Harness />);
    const opener = screen.getByRole('button', { name: 'open-dose' });
    await user.click(opener);
    // Without this check the test passes when no dialog ever opens (the focus stays on the opener).
    expect(screen.getByRole('dialog', { name: 'Log Dose' })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).toBeNull();
    // Radix hands focus back on a deferred timer after unmount, so wait for the positive state.
    await waitFor(() => expect(opener).toHaveFocus());
  });

  // Guard, passes before and after the fix: a successful submit unmounts the dialog without calling onClose,
  // so focus return cannot depend on the close path alone.
  it('returns focus to the opener when a submit closes the dialog', async () => {
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            open-dose
          </button>
          {open && (
            <DoseLoggingModal
              medicationName="Metformin"
              onSubmit={() => setOpen(false)}
              onClose={vi.fn()}
            />
          )}
        </>
      );
    }
    render(<Harness />);
    const opener = screen.getByRole('button', { name: 'open-dose' });
    await user.click(opener);
    await user.click(screen.getByRole('button', { name: 'Log as Taken' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    await waitFor(() => expect(opener).toHaveFocus());
  });

  // Blind spot: a late focus call that runs after the 20 ms wait would pass. StrictMode runs the mount
  // effects twice in dev, which is what queues such a call.
  it('does not move focus to the opener while the dialog stays open, under StrictMode', async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            open-dose
          </button>
          {open && (
            <DoseLoggingModal
              medicationName="Metformin"
              onSubmit={vi.fn()}
              onClose={() => setOpen(false)}
            />
          )}
        </>
      );
    }
    render(
      <StrictMode>
        <Harness />
      </StrictMode>
    );
    const opener = screen.getByRole('button', { name: 'open-dose' });
    opener.focus();
    const focusOpener = vi.spyOn(opener, 'focus');
    fireEvent.click(opener);
    expect(screen.getByRole('dialog', { name: 'Log Dose' })).toBeInTheDocument();
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });
    expect(focusOpener).not.toHaveBeenCalled();
    expect(screen.getByRole('dialog', { name: 'Log Dose' })).toBeInTheDocument();
  });

  // Would not notice: a dialog that animates opacity or transform on mount. Under `still` the content
  // carries no motion props, so it writes no inline opacity or transform. Not a check of the rendered
  // paint: the stillness probe (ui-meds.spec.ts) checks that.
  it('the dialog has no inline opacity or transform at first paint (M0)', () => {
    renderModal();
    const dialog = screen.getByRole('dialog', { name: 'Log Dose' });
    expect(dialog.style.opacity).toBe('');
    expect(dialog.style.transform).toBe('');
  });

  // Would not notice: the computed radius. The class is checked here; the TW4-MEDS e2e test reads the
  // computed radius, so a class that the CSS does not apply would fail there.
  it('the close control is an IconButton named Close with a 10px radius class', () => {
    renderModal();
    const close = screen.getByRole('button', { name: 'Close' });
    expect(close.className).toContain('rounded-[10px]');
  });

  // Would not notice: a dose text with no T0 marker, so the stillness probe would skip it.
  it('the dose text carries data-t0', () => {
    renderModal();
    expect(screen.getByText(/Logging for/).closest('[data-t0]')).not.toBeNull();
  });
});

describe('HC-UIMED-003: no animate-ping under medication-coach/, and BadgeToast uses notify()', () => {
  const coachSources = import.meta.glob('../components/medication-coach/*.{ts,tsx}', {
    query: '?raw',
    import: 'default',
    eager: true,
  }) as Record<string, string>;

  // Would not notice: a ping inside a component that is not imported by the toast. The scan covers
  // every file in the folder, not only the ones a test renders.
  it('no animate-ping anywhere under medication-coach/', () => {
    const hits = Object.entries(coachSources)
      .filter(([, source]) => source.includes('animate-ping'))
      .map(([path]) => path);
    expect(hits).toEqual([]);
  });

  // Would not notice: a toast that still renders its own motion div and never reaches the Toaster.
  it('BadgeToast announces the badge through notify()', () => {
    vi.mocked(notify).mockClear();
    render(
      <BadgeToast
        badge={{
          badge_id: 'first-dose',
          name: 'First Dose',
          description: '',
          icon: 'star',
          medication_id: null,
          earned_at: '2026-03-05T03:00:00',
        }}
        onDismiss={vi.fn()}
      />
    );
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('First Dose') })
    );
  });

  // Pin (passes today): the queue advances after 5 s, so a stuck badge cannot hold the next one back.
  it('BadgeToast calls onDismiss after 5 s', () => {
    vi.useFakeTimers();
    try {
      const onDismiss = vi.fn();
      render(
        <BadgeToast
          badge={{
            badge_id: 'first-dose',
            name: 'First Dose',
            description: '',
            icon: 'star',
            medication_id: null,
            earned_at: '2026-03-05T03:00:00',
          }}
          onDismiss={onDismiss}
        />
      );
      act(() => {
        vi.advanceTimersByTime(5000);
      });
      expect(onDismiss).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('HC-UIMED-004: reminders live on the Medications page', () => {
  // Would not notice: a redirect that keeps the path but drops the medication the user came from.
  it('/notifications redirects to /medications?tab=reminders and keeps the medication', () => {
    render(
      <MemoryRouter initialEntries={['/notifications?medicationId=med-1']}>
        <Routes>
          <Route path="/notifications" element={<NotificationSettings />} />
          <Route path="/medications" element={<p>MEDICATIONS</p>} />
        </Routes>
        <LocationProbe />
      </MemoryRouter>
    );
    expect(screen.getByTestId('location').textContent).toBe(
      '/medications?tab=reminders&medicationId=med-1'
    );
  });

  // Would not notice: a Reminders tab that renders but is not the selected one, or that loses the
  // settings the old page showed.
  it('the Reminders tab is selected and shows the per-medication settings', () => {
    render(
      <MemoryRouter initialEntries={['/medications?tab=reminders&medicationId=med-1']}>
        <MedicationCoach />
      </MemoryRouter>
    );
    expect(screen.getByRole('tab', { name: 'Reminders' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByText('Per-Medication Settings')).toBeInTheDocument();
    expect(screen.getByLabelText('Quiet hours start')).toHaveValue('22:00');
  });

  // Would not notice: a tab strip that ignores ?tab= and always opens Medications.
  it('the Medications tab is the default', () => {
    render(
      <MemoryRouter initialEntries={['/medications']}>
        <MedicationCoach />
      </MemoryRouter>
    );
    expect(screen.getByRole('tab', { name: 'Medications' })).toHaveAttribute('aria-selected', 'true');
  });

  // Would not notice: reminder times rendered without a T0 marker, so the stillness probe skips them.
  it('the reminder times carry data-t0', () => {
    render(
      <MemoryRouter initialEntries={['/medications?tab=reminders&medicationId=med-1']}>
        <MedicationCoach />
      </MemoryRouter>
    );
    expect(screen.getByLabelText('Quiet hours start').closest('[data-t0]')).not.toBeNull();
  });
});

describe('UI-PG-MEDS: Add Medication from the Reminders tab', () => {
  const renderCoach = (path: string) =>
    render(
      <MemoryRouter initialEntries={[path]}>
        <MedicationCoach />
      </MemoryRouter>
    );

  afterEach(() => {
    fixtures.medicationList = null;
  });

  // Blind spot: the form is found by its label, so a form that opened in a tab the user cannot see is caught
  // only by the aria-selected check on the Medications tab.
  it('on ?tab=reminders, Add Medication switches to the Medications tab and shows the form', async () => {
    const user = userEvent.setup();
    renderCoach('/medications?tab=reminders');
    expect(screen.getByRole('tab', { name: 'Reminders' })).toHaveAttribute('aria-selected', 'true');
    await user.click(screen.getByRole('button', { name: 'Add Medication' }));
    expect(screen.getByRole('tab', { name: 'Medications' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Medication Name *')).toBeInTheDocument();
  });

  // The empty Reminders tab points at the form, not at the page the user is already on.
  it('the empty Reminders tab offers Add a medication, which opens the form', async () => {
    const user = userEvent.setup();
    fixtures.medicationList = [];
    renderCoach('/medications?tab=reminders');
    await user.click(screen.getByRole('button', { name: 'Add a medication' }));
    expect(screen.getByRole('tab', { name: 'Medications' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByLabelText('Medication Name *')).toBeInTheDocument();
  });
});

describe('UI-PG-MEDS page rules (plan section 7.7)', () => {
  const stats = {
    medication_id: 'med-1',
    current_streak_days: 3,
    longest_streak_days: 5,
    last_7_days_adherence: 0.9,
    last_30_days_adherence: 0.6,
    total_doses_taken: 10,
    total_doses_skipped: 2,
    total_doses_expected: 12,
  } as unknown as AdherenceStats;

  // Would not notice: a ring that still runs a 700 ms draw, or a hard-coded hex stroke that does not
  // follow the theme.
  it('the adherence ring is final and its colours come from tokens', () => {
    const { container } = render(
      <MemoryRouter>
        <AdherenceDashboard stats={stats} isLoading={false} isError={false} />
      </MemoryRouter>
    );
    expect(container.innerHTML).not.toMatch(/duration-700/);
    expect(container.innerHTML).not.toMatch(/#[0-9A-Fa-f]{6}/);
  });

  // Would not notice: an adherence figure that counts up, because it has no T0 marker to probe.
  it('the adherence figures carry data-t0', () => {
    render(
      <MemoryRouter>
        <AdherenceDashboard stats={stats} isLoading={false} isError={false} />
      </MemoryRouter>
    );
    expect(screen.getByText('90%').closest('[data-t0]')).not.toBeNull();
    expect(screen.getByText('60%').closest('[data-t0]')).not.toBeNull();
    expect(screen.getByText('10').closest('[data-t0]')).not.toBeNull();
  });

  // Would not notice: a raw white, a palette utility or a hex value in any file of the pages or the
  // medication components. `bg-black/..` overlays are not scanned; they are the design's hairlines.
  it('no raw white, palette or hex colour utility in the medication pages and components', () => {
    const files = import.meta.glob(
      [
        '../components/medication-coach/*.{ts,tsx}',
        '../components/MedicationOverlay.tsx',
        '../pages/MedicationCoach.tsx',
        '../pages/MedicationDetail.tsx',
        '../pages/NotificationSettings.tsx',
      ],
      { query: '?raw', import: 'default', eager: true }
    ) as Record<string, string>;
    const raw =
      /\b(?:bg|text|border|ring|fill|stroke)-white\b|#[0-9A-Fa-f]{6}\b|\b(?:bg|text|border)-(?:red|green|blue|yellow|amber|emerald|orange|purple|pink|gray|slate|zinc|neutral|stone|rose|sky|indigo|violet)-\d{2,3}\b/g;
    const hits = Object.entries(files).flatMap(([path, source]) =>
      (source.match(raw) ?? []).map((hit) => `${path}: ${hit}`)
    );
    expect(hits).toEqual([]);
  });

  // Would not notice: a browser confirm or prompt that blocks the page and cannot be styled.
  it('no window.confirm or window.prompt in the medication pages and components', () => {
    const files = import.meta.glob(
      [
        '../components/medication-coach/*.{ts,tsx}',
        '../pages/MedicationCoach.tsx',
        '../pages/MedicationDetail.tsx',
        '../pages/NotificationSettings.tsx',
      ],
      { query: '?raw', import: 'default', eager: true }
    ) as Record<string, string>;
    const hits = Object.entries(files)
      .filter(([, source]) => /window\.(confirm|prompt)\s*\(/.test(source))
      .map(([path]) => path);
    expect(hits).toEqual([]);
  });

  // Blind spot: the label only. A button labelled Reminders that opened another page would pass; no e2e test
  // clicks this button.
  it('the medication detail button that opens the Reminders tab is labelled Reminders', () => {
    const files = import.meta.glob('../pages/MedicationDetail.tsx', {
      query: '?raw',
      import: 'default',
      eager: true,
    }) as Record<string, string>;
    const source = Object.values(files)[0] ?? '';
    expect(source).toContain('tab=reminders');
    expect(source).not.toContain('Notification Settings');
  });
});
