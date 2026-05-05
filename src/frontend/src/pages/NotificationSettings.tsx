import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Bell,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Send,
  Clock3,
  Activity,
  ArrowLeft,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, Input, Skeleton, StaggerGroup, StaggerItem, EmptyState } from '@/components/ui';
import { useMedications } from '@/services/medications';
import {
  useNotificationSettings,
  useUpdateNotificationSettings,
  useNotificationHistory,
  useNotificationSchedulerStatus,
  useSendTestNotification,
  useSendMedicationTestNotification,
} from '@/services/notifications';
import type {
  NotificationSettingsUpdate,
  NotificationSchedulerStatus,
} from '@/services/types';

const PAGE_SIZE = 20;

type NotificationFormState = {
  enabled: boolean;
  quietHoursStart: string;
  quietHoursEnd: string;
  maxRemindersPerDose: number;
  initialOffsetMinutes: number;
  nudgeDelayMinutes: number;
  alertDelayMinutes: number;
  weekendEnabled: boolean;
  celebrationEnabled: boolean;
};

const defaultFormState: NotificationFormState = {
  enabled: true,
  quietHoursStart: '',
  quietHoursEnd: '',
  maxRemindersPerDose: 3,
  initialOffsetMinutes: 0,
  nudgeDelayMinutes: 15,
  alertDelayMinutes: 30,
  weekendEnabled: true,
  celebrationEnabled: true,
};

function schedulerBadgeVariant(state: NotificationSchedulerStatus['state']) {
  if (state === 'running') return 'verified' as const;
  if (state === 'paused') return 'caution' as const;
  return 'default' as const;
}

function formatInteractionRate(rate: number): string {
  const bounded = Math.max(0, Math.min(1, rate));
  return `${Math.round(bounded * 100)}%`;
}

export function NotificationSettings() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const medicationQueryParam = searchParams.get('medicationId') ?? '';

  const [selectedMedicationId, setSelectedMedicationId] = useState(medicationQueryParam);
  const [page, setPage] = useState(1);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [formState, setFormState] = useState<NotificationFormState>(defaultFormState);

  const {
    data: medications,
    isLoading: medicationsLoading,
    isError: medicationsError,
  } = useMedications(false);

  useEffect(() => {
    if (!medications || medications.length === 0) {
      setSelectedMedicationId('');
      return;
    }

    const hasCurrent = medications.some((m) => m.id === selectedMedicationId);
    if (hasCurrent) return;

    const hasQueryId = medicationQueryParam
      && medications.some((m) => m.id === medicationQueryParam);

    setSelectedMedicationId(hasQueryId ? medicationQueryParam : medications[0].id);
  }, [medications, medicationQueryParam, selectedMedicationId]);

  useEffect(() => {
    setPage(1);
  }, [selectedMedicationId, fromDate, toDate]);

  const settingsQuery = useNotificationSettings(selectedMedicationId || undefined);
  const updateSettings = useUpdateNotificationSettings();

  const historyQuery = useNotificationHistory(
    {
      medicationId: selectedMedicationId || undefined,
      fromDate: fromDate || undefined,
      toDate: toDate || undefined,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    },
    !!selectedMedicationId
  );

  const schedulerQuery = useNotificationSchedulerStatus(true);
  const sendGenericTest = useSendTestNotification();
  const sendMedicationTest = useSendMedicationTestNotification();

  useEffect(() => {
    if (!settingsQuery.data) return;

    setFormState({
      enabled: settingsQuery.data.enabled,
      quietHoursStart: settingsQuery.data.quiet_hours_start ?? '',
      quietHoursEnd: settingsQuery.data.quiet_hours_end ?? '',
      maxRemindersPerDose: settingsQuery.data.max_reminders_per_dose,
      initialOffsetMinutes: settingsQuery.data.initial_offset_minutes,
      nudgeDelayMinutes: settingsQuery.data.nudge_delay_minutes,
      alertDelayMinutes: settingsQuery.data.alert_delay_minutes,
      weekendEnabled: settingsQuery.data.weekend_enabled,
      celebrationEnabled: settingsQuery.data.celebration_enabled,
    });
  }, [settingsQuery.data]);

  const totalReminders = historyQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalReminders / PAGE_SIZE));

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const selectedMedicationName = useMemo(() => {
    if (!medications || !selectedMedicationId) return '';
    return medications.find((m) => m.id === selectedMedicationId)?.name ?? '';
  }, [medications, selectedMedicationId]);

  const handleMedicationChange = (medicationId: string) => {
    setSelectedMedicationId(medicationId);
    if (medicationId) {
      setSearchParams({ medicationId });
    } else {
      setSearchParams({});
    }
  };

  const handleSaveSettings = () => {
    if (!selectedMedicationId) return;

    const update: NotificationSettingsUpdate = {
      enabled: formState.enabled,
      quiet_hours_start: formState.quietHoursStart || undefined,
      quiet_hours_end: formState.quietHoursEnd || undefined,
      max_reminders_per_dose: formState.maxRemindersPerDose,
      initial_offset_minutes: formState.initialOffsetMinutes,
      nudge_delay_minutes: formState.nudgeDelayMinutes,
      alert_delay_minutes: formState.alertDelayMinutes,
      weekend_enabled: formState.weekendEnabled,
      celebration_enabled: formState.celebrationEnabled,
    };

    updateSettings.mutate({ medicationId: selectedMedicationId, data: update });
  };

  if (medicationsLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="lg:col-span-2 h-[600px] rounded-2xl" />
          <Skeleton className="h-[400px] rounded-2xl" />
        </div>
      </div>
    );
  }

  if (medicationsError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Failed to load medications</p>
        </div>
      </div>
    );
  }

  if (!medications || medications.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/medications')} className="h-10 w-10 rounded-xl">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
              Notification Settings
            </h1>
            <p className="text-ink-secondary mt-1">
              Configure reminders and review notification history
            </p>
          </div>
        </div>

        <EmptyState
          icon={Bell}
          title="No medications to configure"
          description="Add a medication first, then return here to tune reminder behavior."
          action={
            <Button onClick={() => navigate('/medications')} className="gap-2">
              Go to Medication Coach
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Notification Settings
          </h1>
          <p className="text-ink-secondary mt-1">
            Quiet hours and reminder timing use your device&apos;s local time.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => historyQuery.refetch()}
            className="gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh History
          </Button>
          <Button
            variant="secondary"
            onClick={() => sendGenericTest.mutate({
              title: 'HealthCentral Test Notification',
              body: 'Notifications are configured and ready.',
            })}
            disabled={sendGenericTest.isPending}
            className="gap-2"
          >
            {sendGenericTest.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            Send Test
          </Button>
        </div>
      </div>

      <StaggerGroup className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <StaggerItem className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-ink-secondary" />
                Per-Medication Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <label className="block text-sm font-medium text-ink">
                Medication
                <select
                  className="mt-1.5 h-11 w-full rounded-xl border border-black/[0.08] bg-white px-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent transition-all"
                  value={selectedMedicationId}
                  onChange={(e) => handleMedicationChange(e.target.value)}
                >
                  {medications.map((medication) => (
                    <option key={medication.id} value={medication.id}>
                      {medication.name}
                    </option>
                  ))}
                </select>
              </label>

              {settingsQuery.isLoading ? (
                <div className="space-y-4 py-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Skeleton className="h-12" />
                    <Skeleton className="h-12" />
                    <Skeleton className="h-12" />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Skeleton className="h-20" />
                    <Skeleton className="h-20" />
                  </div>
                </div>
              ) : settingsQuery.isError ? (
                <div className="rounded-xl bg-status-critical-subtle text-status-critical p-4 text-sm border border-status-critical/10">
                  Failed to load notification settings for this medication.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="flex items-center justify-between rounded-xl border border-black/[0.08] p-3 hover:bg-surface-muted transition-colors cursor-pointer group">
                      <span className="text-sm text-ink">Reminders enabled</span>
                      <input
                        type="checkbox"
                        checked={formState.enabled}
                        onChange={(e) => setFormState((prev) => ({
                          ...prev,
                          enabled: e.target.checked,
                        }))}
                        className="h-4 w-4 accent-accent rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between rounded-xl border border-black/[0.08] p-3 hover:bg-surface-muted transition-colors cursor-pointer group">
                      <span className="text-sm text-ink">Weekend reminders</span>
                      <input
                        type="checkbox"
                        checked={formState.weekendEnabled}
                        onChange={(e) => setFormState((prev) => ({
                          ...prev,
                          weekendEnabled: e.target.checked,
                        }))}
                        className="h-4 w-4 accent-accent rounded"
                      />
                    </label>

                    <label className="flex items-center justify-between rounded-xl border border-black/[0.08] p-3 hover:bg-surface-muted transition-colors cursor-pointer group">
                      <span className="text-sm text-ink">Celebration messages</span>
                      <input
                        type="checkbox"
                        checked={formState.celebrationEnabled}
                        onChange={(e) => setFormState((prev) => ({
                          ...prev,
                          celebrationEnabled: e.target.checked,
                        }))}
                        className="h-4 w-4 accent-accent rounded"
                      />
                    </label>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Input
                      type="time"
                      label="Quiet hours start"
                      value={formState.quietHoursStart}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        quietHoursStart: e.target.value,
                      }))}
                    />
                    <Input
                      type="time"
                      label="Quiet hours end"
                      value={formState.quietHoursEnd}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        quietHoursEnd: e.target.value,
                      }))}
                    />
                    <Input
                      type="number"
                      label="Max reminders per dose"
                      min={1}
                      max={5}
                      value={String(formState.maxRemindersPerDose)}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        maxRemindersPerDose: Number.parseInt(e.target.value, 10) || 1,
                      }))}
                    />
                    <Input
                      type="number"
                      label="Initial offset (minutes)"
                      min={0}
                      max={60}
                      value={String(formState.initialOffsetMinutes)}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        initialOffsetMinutes: Number.parseInt(e.target.value, 10) || 0,
                      }))}
                    />
                    <Input
                      type="number"
                      label="Nudge delay (minutes)"
                      min={5}
                      max={60}
                      value={String(formState.nudgeDelayMinutes)}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        nudgeDelayMinutes: Number.parseInt(e.target.value, 10) || 5,
                      }))}
                    />
                    <Input
                      type="number"
                      label="Alert delay (minutes)"
                      min={10}
                      max={120}
                      value={String(formState.alertDelayMinutes)}
                      onChange={(e) => setFormState((prev) => ({
                        ...prev,
                        alertDelayMinutes: Number.parseInt(e.target.value, 10) || 10,
                      }))}
                    />
                  </div>

                  <div className="flex items-center gap-2 pt-2">
                    <Button
                      onClick={handleSaveSettings}
                      disabled={updateSettings.isPending}
                      className="gap-2"
                    >
                      {updateSettings.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Bell className="w-4 h-4" />
                      )}
                      Save Settings
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={!selectedMedicationId || sendMedicationTest.isPending}
                      onClick={() => selectedMedicationId && sendMedicationTest.mutate(selectedMedicationId)}
                      className="gap-2 border-black/[0.06]"
                    >
                      {sendMedicationTest.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                      Send Medication Test
                    </Button>
                  </div>

                  {updateSettings.isSuccess && (
                    <p className="text-sm text-status-verified font-medium animate-fade-in">
                      Notification settings saved for {selectedMedicationName}.
                    </p>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-ink-secondary" />
                Notification History
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <Input
                  type="date"
                  label="From date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                />
                <Input
                  type="date"
                  label="To date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                />
              </div>

              {historyQuery.isLoading ? (
                <div className="space-y-3 py-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : historyQuery.isError ? (
                <p className="text-sm text-status-critical">
                  Unable to load notification history.
                </p>
              ) : !historyQuery.data || historyQuery.data.reminders.length === 0 ? (
                <div className="py-10 text-center border-2 border-dashed border-black/[0.04] rounded-2xl">
                  <p className="text-sm text-ink-secondary">
                    No reminder history for the selected filters.
                  </p>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto rounded-xl border border-black/[0.04]">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-ink-tertiary bg-surface-muted">
                          <th className="py-3 px-4 font-medium">Sent</th>
                          <th className="py-3 px-4 font-medium">Medication</th>
                          <th className="py-3 px-4 font-medium">Type</th>
                          <th className="py-3 px-4 font-medium">Delivery</th>
                          <th className="py-3 px-4 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-black/[0.04]">
                        {historyQuery.data.reminders.map((reminder) => (
                          <tr key={reminder.id} className="hover:bg-black/[0.01] transition-colors">
                            <td className="py-3 px-4 text-ink-secondary whitespace-nowrap">
                              {new Date(reminder.sent_at).toLocaleString()}
                            </td>
                            <td className="py-3 px-4 text-ink font-medium">{reminder.medication_name}</td>
                            <td className="py-3 px-4 text-ink-secondary capitalize">{reminder.reminder_type}</td>
                            <td className="py-3 px-4 text-ink-secondary capitalize">{reminder.delivery_method}</td>
                            <td className="py-3 px-4">
                              {reminder.was_interacted ? (
                                <Badge variant="verified" className="capitalize">
                                  {reminder.interaction_type ?? 'interacted'}
                                </Badge>
                              ) : (
                                <Badge variant="default" className="capitalize">sent</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <p className="text-xs text-ink-tertiary font-medium">
                      Page {page} of {totalPages}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={page <= 1}
                        onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                        className="h-8 rounded-lg"
                      >
                        Previous
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={page >= totalPages}
                        onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                        className="h-8 rounded-lg"
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </StaggerItem>

        <StaggerItem className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <Clock3 className="w-4 h-4 text-ink-secondary" />
                Scheduler Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {schedulerQuery.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : schedulerQuery.isError || !schedulerQuery.data ? (
                <p className="text-sm text-status-critical">
                  Could not load scheduler status.
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                    <span className="text-sm text-ink-secondary">State</span>
                    <Badge variant={schedulerBadgeVariant(schedulerQuery.data.state)} className="capitalize">
                      {schedulerQuery.data.state}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                    <span className="text-sm text-ink-secondary">Platform</span>
                    <span className="text-sm font-medium text-ink">
                      {schedulerQuery.data.active_platform ?? 'none'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                    <span className="text-sm text-ink-secondary">Profiles</span>
                    <span className="text-sm font-medium text-ink">
                      {schedulerQuery.data.registered_profiles}
                    </span>
                  </div>
                  <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                    <span className="text-sm text-ink-secondary">Sent this hour</span>
                    <span className="text-sm font-medium text-ink">
                      {schedulerQuery.data.notifications_sent_this_hour}
                    </span>
                  </div>

                  {schedulerQuery.data.state === 'stopped'
                    && schedulerQuery.data.registered_profiles === 0 && (
                    <div className="rounded-xl bg-status-info-subtle text-status-info p-3 text-sm border border-status-info/10">
                      Scheduler is not initialized for this session yet.
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">History Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">Last 7 days</span>
                <span className="text-sm font-medium text-ink">
                  {historyQuery.data?.stats.sent_last_7_days ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">Last 30 days</span>
                <span className="text-sm font-medium text-ink">
                  {historyQuery.data?.stats.sent_last_30_days ?? 0}
                </span>
              </div>
              <div className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted">
                <span className="text-sm text-ink-secondary">Interaction rate (7d)</span>
                <span className="text-sm font-medium text-ink">
                  {formatInteractionRate(historyQuery.data?.stats.interaction_rate_7d ?? 0)}
                </span>
              </div>
            </CardContent>
          </Card>
        </StaggerItem>
      </StaggerGroup>
    </div>
  );
}
