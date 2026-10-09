/**
 * NotificationSettings page tests
 *
 * Covers empty-state behavior and scheduler-not-initialized handling.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { NotificationSettings } from '@/pages/NotificationSettings';
import * as medicationService from '@/services/medications';
import * as notificationService from '@/services/notifications';

vi.mock('@/services/medications', () => ({
  useMedications: vi.fn(),
}));

vi.mock('@/services/notifications', () => ({
  useNotificationSettings: vi.fn(),
  useUpdateNotificationSettings: vi.fn(),
  useNotificationHistory: vi.fn(),
  useNotificationSchedulerStatus: vi.fn(),
  useSendTestNotification: vi.fn(),
  useSendMedicationTestNotification: vi.fn(),
}));

function renderPage() {
  return render(
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <NotificationSettings />
    </BrowserRouter>
  );
}

const emptyMutation = {
  mutate: vi.fn(),
  isPending: false,
  isSuccess: false,
  isError: false,
};

describe('NotificationSettings page', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(notificationService.useNotificationSettings).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof notificationService.useNotificationSettings>);

    vi.mocked(notificationService.useUpdateNotificationSettings).mockReturnValue(
      emptyMutation as unknown as ReturnType<typeof notificationService.useUpdateNotificationSettings>
    );

    vi.mocked(notificationService.useNotificationHistory).mockReturnValue({
      data: {
        total: 0,
        reminders: [],
        stats: {
          sent_last_7_days: 0,
          sent_last_30_days: 0,
          interaction_rate_7d: 0,
          by_type: {},
        },
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof notificationService.useNotificationHistory>);

    vi.mocked(notificationService.useNotificationSchedulerStatus).mockReturnValue({
      data: {
        state: 'stopped',
        active_platform: null,
        registered_profiles: 0,
        notifications_sent_this_hour: 0,
        last_check: null,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof notificationService.useNotificationSchedulerStatus>);

    vi.mocked(notificationService.useSendTestNotification).mockReturnValue(
      emptyMutation as unknown as ReturnType<typeof notificationService.useSendTestNotification>
    );

    vi.mocked(notificationService.useSendMedicationTestNotification).mockReturnValue(
      emptyMutation as unknown as ReturnType<typeof notificationService.useSendMedicationTestNotification>
    );
  });

  it('FE-NOTIFY-PAGE-001: shows empty state when no medications exist', () => {
    vi.mocked(medicationService.useMedications).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof medicationService.useMedications>);

    renderPage();

    expect(screen.getByText('No medications to configure')).toBeInTheDocument();
    expect(screen.getByText(/Add a medication first/)).toBeInTheDocument();
  });

  it('FE-NOTIFY-PAGE-002: shows scheduler-not-initialized state and local-time note', () => {
    vi.mocked(medicationService.useMedications).mockReturnValue({
      data: [
        {
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
          schedules: [],
        },
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof medicationService.useMedications>);

    vi.mocked(notificationService.useNotificationSettings).mockReturnValue({
      data: {
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
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof notificationService.useNotificationSettings>);

    renderPage();

    expect(screen.getByText(/use your device's local time/i)).toBeInTheDocument();
    expect(screen.getByText(/Scheduler is not initialized for this session yet/i)).toBeInTheDocument();
  });
});
