/**
 * Notifications Service Contract Tests
 *
 * Verifies notification hooks call the expected backend routes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import {
  useNotificationSettings,
  useUpdateNotificationSettings,
  useNotificationHistory,
  useNotificationSchedulerStatus,
  useSendTestNotification,
  useSendMedicationTestNotification,
} from '@/services/notifications';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
}));

function renderWithProviders(component: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
}

function SettingsProbe() {
  useNotificationSettings('med-123');
  return <div>settings-probe</div>;
}

function HistoryProbe() {
  useNotificationHistory({
    medicationId: 'med-123',
    fromDate: '2026-02-01',
    toDate: '2026-02-09',
    limit: 20,
    offset: 0,
  });
  return <div>history-probe</div>;
}

function SchedulerProbe() {
  useNotificationSchedulerStatus();
  return <div>scheduler-probe</div>;
}

function UpdateProbe() {
  const mutation = useUpdateNotificationSettings();
  return (
    <button
      onClick={() =>
        mutation.mutate({
          medicationId: 'med-123',
          data: {
            enabled: true,
            quiet_hours_start: '22:00',
            quiet_hours_end: '07:00',
          },
        })
      }
    >
      update-settings
    </button>
  );
}

function SendTestProbe() {
  const mutation = useSendTestNotification();
  return (
    <button
      onClick={() =>
        mutation.mutate({
          title: 'Test Notification',
          body: 'Testing reminder delivery.',
        })
      }
    >
      send-test
    </button>
  );
}

function SendMedicationTestProbe() {
  const mutation = useSendMedicationTestNotification();
  return (
    <button onClick={() => mutation.mutate('med-123')}>
      send-med-test
    </button>
  );
}

describe('Notifications service contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.apiGet).mockImplementation((endpoint: string) => {
      if (endpoint.includes('/scheduler/status')) {
        return Promise.resolve({
          state: 'stopped',
          active_platform: null,
          registered_profiles: 0,
          notifications_sent_this_hour: 0,
          last_check: null,
        });
      }

      if (endpoint.includes('/history')) {
        return Promise.resolve({
          total: 0,
          reminders: [],
          stats: {
            sent_last_7_days: 0,
            sent_last_30_days: 0,
            interaction_rate_7d: 0,
            by_type: {},
          },
        });
      }

      return Promise.resolve({
        medication_id: 'med-123',
        enabled: true,
        quiet_hours_start: null,
        quiet_hours_end: null,
        max_reminders_per_dose: 3,
        initial_offset_minutes: 0,
        nudge_delay_minutes: 15,
        alert_delay_minutes: 30,
        weekend_enabled: true,
        celebration_enabled: true,
      });
    });

    vi.mocked(api.apiPatch).mockResolvedValue({
      medication_id: 'med-123',
      enabled: true,
      quiet_hours_start: '22:00',
      quiet_hours_end: '07:00',
      max_reminders_per_dose: 3,
      initial_offset_minutes: 0,
      nudge_delay_minutes: 15,
      alert_delay_minutes: 30,
      weekend_enabled: true,
      celebration_enabled: true,
    });

    vi.mocked(api.apiPost).mockResolvedValue({
      success: true,
      platform: 'mock',
      message: 'sent',
    });
  });

  it('FE-NOTIFY-API-001: settings hook uses /notifications/settings/{id}', async () => {
    renderWithProviders(<SettingsProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/notifications/settings/med-123');
  });

  it('FE-NOTIFY-API-002: history hook uses /notifications/history with query params', async () => {
    renderWithProviders(<HistoryProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/notifications/history', {
      medication_id: 'med-123',
      from_date: '2026-02-01T00:00:00',
      to_date: '2026-02-09T23:59:59',
      limit: '20',
      offset: '0',
    });
  });

  it('FE-NOTIFY-API-003: scheduler hook uses /notifications/scheduler/status', async () => {
    renderWithProviders(<SchedulerProbe />);

    await waitFor(() => {
      expect(api.apiGet).toHaveBeenCalled();
    });

    expect(api.apiGet).toHaveBeenCalledWith('/notifications/scheduler/status');
  });

  it('FE-NOTIFY-API-004: update mutation uses PATCH /notifications/settings/{id}', async () => {
    const user = userEvent.setup();
    renderWithProviders(<UpdateProbe />);

    await user.click(screen.getByRole('button', { name: /update-settings/i }));

    await waitFor(() => {
      expect(api.apiPatch).toHaveBeenCalled();
    });

    expect(api.apiPatch).toHaveBeenCalledWith('/notifications/settings/med-123', {
      enabled: true,
      quiet_hours_start: '22:00',
      quiet_hours_end: '07:00',
    });
  });

  it('FE-NOTIFY-API-005: generic test mutation uses POST /notifications/test', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SendTestProbe />);

    await user.click(screen.getByRole('button', { name: /send-test/i }));

    await waitFor(() => {
      expect(api.apiPost).toHaveBeenCalled();
    });

    expect(api.apiPost).toHaveBeenCalledWith('/notifications/test', {
      title: 'Test Notification',
      body: 'Testing reminder delivery.',
    });
  });

  it('FE-NOTIFY-API-006: medication test mutation uses POST /notifications/test/{id}', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SendMedicationTestProbe />);

    await user.click(screen.getByRole('button', { name: /send-med-test/i }));

    await waitFor(() => {
      expect(api.apiPost).toHaveBeenCalled();
    });

    expect(api.apiPost).toHaveBeenCalledWith('/notifications/test/med-123');
  });
});
