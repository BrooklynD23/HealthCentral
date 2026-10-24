/**
 * Gamification: badge toast queue, achievements dates (naive UTC), streak display.
 */
import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { BadgeInfo, BadgeStatus, StreakResponse } from '@/services/types';

vi.mock('framer-motion', () => {
  const MOTION_PROPS = new Set([
    'initial', 'animate', 'exit', 'transition', 'variants', 'whileHover',
    'whileTap', 'whileInView', 'layout', 'layoutId', 'custom', 'viewport',
  ]);
  const cache: Record<string, unknown> = {};
  const motion = new Proxy({}, {
    get: (_t, tag: string) =>
      (cache[tag] ??= ({ children, ...props }: Record<string, unknown>) => {
        const dom = Object.fromEntries(Object.entries(props).filter(([k]) => !MOTION_PROPS.has(k)));
        const El = tag as 'div';
        return <El {...dom}>{children as React.ReactNode}</El>;
      }),
  });
  return { motion, m: motion, AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</> };
});

const badgesData: { badges: BadgeStatus[] } = { badges: [] };
let streaksData: StreakResponse | undefined;
vi.mock('@/services', () => {
  // Inert query/mutation results for the hooks SettingsPage reads.
  const query = () => ({ data: undefined, isLoading: false, isError: false });
  const mutation = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false });
  return {
    useBadges: () => ({ data: badgesData, isLoading: false }),
    useStreaks: () => ({ data: streaksData }),
    useDocuments: () => ({ data: [] }),
    useMedReconciliation: () => ({ data: [], isLoading: false }),
    useModelSettings: query,
    useTiers: query,
    useDownloadProgress: query,
    useExternalApiSettings: query,
    useTimezone: query,
    useVoiceSettings: query,
    useEnvironmentDiagnostics: query,
    useDetectHardware: mutation,
    useSetTier: mutation,
    useStartDownload: mutation,
    useSaveExternalApiSettings: mutation,
    useSaveTimezone: mutation,
    useSaveVoiceSettings: mutation,
    useSaveOcrPreference: mutation,
    useRecheckDiagnostics: mutation,
  };
});

// C-GAM2B: streaks_hidden setting. undefined = loading or failed.
let gamificationData: { streaks_hidden: boolean } | undefined;
const saveGamificationMutate = vi.fn();
vi.mock('@/services/modelSettings', () => ({
  useGamificationSettings: () => ({ data: gamificationData }),
  useSaveGamificationSettings: () => ({ mutate: saveGamificationMutate, isPending: false }),
}));

vi.mock('@/services/feedback', () => ({
  useFeedbackStats: () => ({ data: undefined }),
  useExportDataset: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock('@/components/MemoryManager', () => ({ MemoryManager: () => null }));
vi.mock('@/components/settings/BackupCard', () => ({ BackupCard: () => null }));
vi.mock('@/components/settings/RecoveryCodeCard', () => ({ RecoveryCodeCard: () => null }));
vi.mock('@/components/settings/DangerZone', () => ({ DangerZone: () => null }));
vi.mock('@/components/settings/AgentSettingsCard', () => ({ AgentSettingsCard: () => null }));

const logDoseMutate = vi.fn();
vi.mock('@/services/medications', () => ({
  useMedications: () => ({
    data: [{ id: 'm1', name: 'Metformin' }],
    isLoading: false,
    isError: false,
  }),
  useCreateMedication: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateMedication: () => ({ mutate: vi.fn(), isPending: false }),
  useLogDose: () => ({ mutate: logDoseMutate, isPending: false }),
}));

// Real BadgeToast / AchievementsWidget / StreakDisplay; stub the heavy ones.
vi.mock('@/components/medication-coach', async () => {
  const [{ BadgeToast }, { AchievementsWidget }] = await Promise.all([
    import('@/components/medication-coach/BadgeToast'),
    import('@/components/medication-coach/AchievementsWidget'),
  ]);
  return {
    BadgeToast,
    AchievementsWidget,
    MedicationForm: () => null,
    MedicationCard: ({ medication, onQuickLog }: { medication: { id: string }; onQuickLog: (id: string) => void }) => (
      <button onClick={() => onQuickLog(medication.id)}>quick-log</button>
    ),
    DoseLoggingModal: ({ onSubmit }: { onSubmit: (d: object) => void }) => (
      <button onClick={() => onSubmit({})}>submit-dose</button>
    ),
  };
});

import { BadgeToast } from '@/components/medication-coach/BadgeToast';
import { AchievementsWidget } from '@/components/medication-coach/AchievementsWidget';
import { StreakDisplay } from '@/components/medication-coach/StreakDisplay';
import { MedicationCoach } from '@/pages/MedicationCoach';
import { AdherenceDashboard } from '@/components/medication-coach/AdherenceDashboard';
import { SettingsPage } from '@/pages/SettingsPage';

const badge = (id: string, name: string): BadgeInfo => ({ badge_id: id, name, description: '', icon: 'star', medication_id: null, earned_at: '2026-03-05T03:00:00' });
const status = (over: Partial<BadgeStatus>): BadgeStatus => ({
  id: 'b', name: 'Badge', description: '', icon: 'star', criteria_type: 'x',
  earned: false, earned_at: null, medication_id: null, ...over,
});

describe('BadgeToast', () => {
  it('renders name and dismiss calls onDismiss', () => {
    const onDismiss = vi.fn();
    render(<BadgeToast badge={badge('a', 'First Dose')} onDismiss={onDismiss} />);
    expect(screen.getByText('First Dose')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
  it('renders nothing for null badge', () => {
    render(<BadgeToast badge={null} onDismiss={vi.fn()} />);
    expect(screen.queryByRole('status')).toBeNull();
  });
});

describe('StreakDisplay', () => {
  it('shows current and longest', () => {
    render(<StreakDisplay currentStreak={3} longestStreak={12} />);
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('broken streak uses neutral copy, not "0 Day streak"', () => {
    const { container } = render(<StreakDisplay currentStreak={0} longestStreak={5} />);
    expect(screen.getByText('New streak starts today')).toBeInTheDocument();
    expect(screen.queryByText('Day streak')).toBeNull();
    expect(screen.queryByText('0')).toBeNull();
    expect(container.innerHTML).not.toContain('status-caution');
  });
});

describe('AchievementsWidget profile streak', () => {
  const streaks = (over: Partial<StreakResponse>): StreakResponse => ({
    current_streak_days: 4, longest_streak_days: 11, timezone: 'UTC', as_of_date: '2026-03-04',
    active_days_last_28: 4, weeks_with_log_last_4: 1, ...over,
  });
  const renderWidget = () => render(<BrowserRouter><AchievementsWidget /></BrowserRouter>);
  afterEach(() => { streaksData = undefined; });

  it('shows the all-medications streak above the badges', () => {
    badgesData.badges = [status({ name: 'Locked One' })];
    streaksData = streaks({ timezone: 'America/New_York' });
    renderWidget();
    expect(screen.getByText('All medications')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('11')).toBeInTheDocument();
    expect(screen.getByText('Locked One')).toBeInTheDocument();
  });

  it('shows the UTC hint with a Settings link only when the timezone is UTC', () => {
    badgesData.badges = [];
    streaksData = streaks({ timezone: 'UTC' });
    const { unmount } = renderWidget();
    expect(screen.getByText(/Streak days are counted in UTC/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Settings/ })).toHaveAttribute('href', '/settings');
    unmount();

    streaksData = streaks({ timezone: 'Europe/Berlin' });
    renderWidget();
    expect(screen.queryByText(/Streak days are counted in UTC/)).toBeNull();
  });

  it('still shows badges while the streak has not loaded', () => {
    badgesData.badges = [status({ name: 'Locked One' })];
    streaksData = undefined;
    renderWidget();
    expect(screen.getByText('Locked One')).toBeInTheDocument();
    expect(screen.queryByText('All medications')).toBeNull();
  });
});

describe('AchievementsWidget', () => {
  const prevTZ = process.env.TZ;
  beforeAll(() => { process.env.TZ = 'America/New_York'; });
  afterAll(() => { if (prevTZ === undefined) delete process.env.TZ; else process.env.TZ = prevTZ; });

  it('shows earned count and locked badge', () => {
    badgesData.badges = [status({ id: 'a', name: 'Earned One', earned: true }), status({ id: 'b', name: 'Locked One' })];
    render(<AchievementsWidget />);
    expect(screen.getByText('1 / 2')).toBeInTheDocument();
    expect(screen.getByText('Locked One')).toBeInTheDocument();
  });

  it('treats naive earned_at as UTC (not local)', () => {
    // sanity: test TZ is really non-UTC (EST, UTC-5, before DST on 2026-03-08)
    expect(new Date('2026-03-05T12:00:00Z').getTimezoneOffset()).toBe(300);
    badgesData.badges = [status({ earned: true, earned_at: '2026-03-05T03:00:00' })];
    render(<AchievementsWidget />);
    expect(screen.getByText('Mar 4')).toBeInTheDocument(); // 03:00Z = Mar 4 22:00 EST
    expect(screen.queryByText('Mar 5')).toBeNull();
  });

  it.each(['2026-03-05T03:00:00Z', '2026-03-05T03:00:00+00:00', '2026-03-05T03:00:00.123456Z'])(
    'does not double-append for tz-designated %s',
    (earned_at) => {
      badgesData.badges = [status({ earned: true, earned_at })];
      render(<AchievementsWidget />);
      expect(screen.getByText('Mar 4')).toBeInTheDocument();
    }
  );

  it('respects explicit non-UTC offset', () => {
    badgesData.badges = [status({ earned: true, earned_at: '2026-03-05T03:00:00-05:00' })];
    render(<AchievementsWidget />);
    expect(screen.getByText('Mar 5')).toBeInTheDocument(); // 08:00Z Mar 5 = 03:00 EST
  });
});

describe('MedicationCoach badge queue', () => {
  it('shows every newly earned badge, one after another', () => {
    badgesData.badges = [];
    logDoseMutate.mockImplementation((_v, opts) =>
      opts.onSuccess({ newly_earned_badges: [badge('a', 'Badge Alpha'), badge('b', 'Badge Beta')] })
    );
    render(<BrowserRouter><MedicationCoach /></BrowserRouter>);
    fireEvent.click(screen.getByText('quick-log'));
    fireEvent.click(screen.getByText('submit-dose'));

    expect(screen.getByText('Badge Alpha')).toBeInTheDocument();
    expect(screen.queryByText('Badge Beta')).toBeNull();
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(screen.getByText('Badge Beta')).toBeInTheDocument();
    expect(screen.queryByText('Badge Alpha')).toBeNull();
    fireEvent.click(screen.getByLabelText('Dismiss'));
    expect(screen.queryByText('Badge Beta')).toBeNull();
  });
});

describe('streaks_hidden (C-GAM2B)', () => {
  const streaks: StreakResponse = {
    current_streak_days: 4, longest_streak_days: 11, timezone: 'UTC', as_of_date: '2026-03-04',
    active_days_last_28: 4, weeks_with_log_last_4: 1,
  };
  const adherence = {
    medication_id: 'm1', current_streak_days: 6, longest_streak_days: 21,
    last_7_days_adherence: 0.9, last_30_days_adherence: 0.8,
    total_doses_taken: 10, total_doses_skipped: 1, total_doses_expected: 11,
  };
  const renderWidget = () => render(<BrowserRouter><AchievementsWidget /></BrowserRouter>);
  const renderDashboard = () =>
    render(<AdherenceDashboard stats={adherence} isLoading={false} isError={false} />);
  afterEach(() => {
    gamificationData = undefined;
    streaksData = undefined;
    saveGamificationMutate.mockReset();
  });

  it('hidden: profile streak and UTC hint are gone, badges stay', () => {
    gamificationData = { streaks_hidden: true };
    streaksData = streaks;
    badgesData.badges = [status({ id: 'streak-7', name: 'Week Warrior', earned: true, criteria_type: 'streak' })];
    renderWidget();
    expect(screen.queryByText('All medications')).toBeNull();
    expect(screen.queryByText(/Streak days are counted in UTC/)).toBeNull();
    expect(screen.getByText('Week Warrior')).toBeInTheDocument();
  });

  it('hidden: per-medication streak is gone from the adherence dashboard', () => {
    gamificationData = { streaks_hidden: true };
    renderDashboard();
    expect(screen.getByText('Adherence')).toBeInTheDocument();
    expect(screen.queryByText('6')).toBeNull();
    expect(screen.queryByText('21')).toBeNull();
  });

  it.each([
    ['shown', { streaks_hidden: false }],
    ['loading or failed', undefined],
  ])('%s: both streak surfaces behave as before', (_name, data) => {
    gamificationData = data;
    streaksData = streaks;
    badgesData.badges = [];
    const { unmount } = renderWidget();
    expect(screen.getByText('All medications')).toBeInTheDocument();
    expect(screen.getByText(/Streak days are counted in UTC/)).toBeInTheDocument();
    unmount();
    renderDashboard();
    expect(screen.getByText('6')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();
  });

  describe('Show streaks switch', () => {
    const renderSettings = () =>
      render(
        <QueryClientProvider client={new QueryClient()}>
          <BrowserRouter><SettingsPage /></BrowserRouter>
        </QueryClientProvider>
      );

    it('is on by default and PATCHes streaks_hidden=true when turned off', () => {
      gamificationData = { streaks_hidden: false };
      renderSettings();
      const toggle = screen.getByRole('switch', { name: 'Show streaks' });
      expect(toggle).toHaveAttribute('aria-checked', 'true');
      fireEvent.click(toggle);
      expect(saveGamificationMutate).toHaveBeenCalledWith({ streaks_hidden: true });
    });

    it('is off when hidden and PATCHes streaks_hidden=false when turned on', () => {
      gamificationData = { streaks_hidden: true };
      renderSettings();
      const toggle = screen.getByRole('switch', { name: 'Show streaks' });
      expect(toggle).toHaveAttribute('aria-checked', 'false');
      fireEvent.click(toggle);
      expect(saveGamificationMutate).toHaveBeenCalledWith({ streaks_hidden: false });
    });
  });
});
