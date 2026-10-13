/**
 * Gamification: badge toast queue, achievements dates (naive UTC), streak display.
 */
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import type { BadgeInfo, BadgeStatus } from '@/services/types';

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
  return { motion, AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</> };
});

const badgesData: { badges: BadgeStatus[] } = { badges: [] };
vi.mock('@/services', () => ({
  useBadges: () => ({ data: badgesData, isLoading: false }),
  useDocuments: () => ({ data: [] }),
  useMedReconciliation: () => ({ data: [], isLoading: false }),
}));

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
