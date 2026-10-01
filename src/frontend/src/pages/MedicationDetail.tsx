import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Pill,
  Loader2,
  AlertTriangle,
  CheckCircle,
  SkipForward,
  Sparkles,
  Bell,
  Trash2,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
} from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  AdherenceDashboard,
  ScheduleEditor,
  DoseLoggingModal,
} from '@/components/medication-coach';
import {
  useMedication,
  useAdherenceStats,
  useDoses,
  useLogDose,
  useCreateSchedule,
  useDeleteSchedule,
  useDeleteMedication,
  useLearnPatterns,
  useMedicationCorrelations,
} from '@/services/medications';
import { FlaskConical } from 'lucide-react';
import type { ScheduleCreate, DoseLog } from '@/services/types';

const frequencyLabels: Record<string, string> = {
  once_daily: 'Once daily',
  twice_daily: 'Twice daily',
  three_times_daily: '3x daily',
  four_times_daily: '4x daily',
  every_other_day: 'Every other day',
  weekly: 'Weekly',
  as_needed: 'As needed',
  custom: 'Custom',
};

export function MedicationDetail() {
  const { medicationId } = useParams<{ medicationId: string }>();
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [showLogModal, setShowLogModal] = useState(false);

  const {
    data: medication,
    isLoading,
    isError,
  } = useMedication(medicationId);

  const {
    data: stats,
    isLoading: statsLoading,
    isError: statsError,
  } = useAdherenceStats(medicationId);

  const { data: doses } = useDoses(medicationId);

  // MED-CORR-002: the backend owns the overlap rule (MED-CORR-001). It defaults
  // to verified observations only — an unverified extraction is not a fact to
  // correlate against — which the old frontend heuristic did not do.
  const { data: correlations } = useMedicationCorrelations(medicationId);
  const relatedObservations = correlations?.observations ?? [];
  const excludedUndatedCount = correlations?.excluded_undated_count ?? 0;

  const logDose = useLogDose();
  const createSchedule = useCreateSchedule();
  const deleteSchedule = useDeleteSchedule();
  const deleteMedication = useDeleteMedication();
  const learnPatterns = useLearnPatterns();

  const handleLogDose = (data: DoseLog) => {
    if (!medicationId) return;
    logDose.mutate(
      { medicationId, data },
      { onSuccess: () => setShowLogModal(false) }
    );
  };

  const handleAddSchedule = (data: ScheduleCreate) => {
    if (!medicationId) return;
    createSchedule.mutate({ medicationId, data });
  };

  const handleDeleteSchedule = (scheduleId: string) => {
    if (!medicationId) return;
    deleteSchedule.mutate({ medicationId, scheduleId });
  };

  const handleDelete = () => {
    if (!medicationId) return;
    deleteMedication.mutate(
      { medicationId },
      { onSuccess: () => navigate('/medications') }
    );
  };

  const handleLearnPatterns = () => {
    if (!medicationId) return;
    learnPatterns.mutate({ medicationId });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" role="status" aria-live="polite">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="sr-only">Loading medication details...</span>
      </div>
    );
  }

  if (isError || !medication) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Medication not found</p>
          <Button
            variant="ghost"
            className="mt-3"
            onClick={() => navigate('/medications')}
          >
            Back to Medications
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/medications')}
            aria-label="Back to medications"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <Pill className="w-6 h-6 text-accent" />
              <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
                {medication.name}
              </h1>
              {!medication.is_active && (
                <Badge variant="default">Inactive</Badge>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-sm text-ink-secondary">
              {medication.dosage_amount && (
                <span>
                  {medication.dosage_amount}{medication.dosage_unit ?? ''}{' '}
                  {medication.dosage_form ?? ''}
                </span>
              )}
              <span>{frequencyLabels[medication.frequency] ?? medication.frequency}</span>
              {medication.generic_name && (
                <span className="text-ink-tertiary">({medication.generic_name})</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button onClick={() => setShowLogModal(true)} className="gap-2">
            <CheckCircle className="w-4 h-4" />
            Log Dose
          </Button>
          <Button
            variant="secondary"
            onClick={handleLearnPatterns}
            disabled={learnPatterns.isPending}
            className="gap-2"
          >
            {learnPatterns.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            Learn Patterns
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate(`/notifications?medicationId=${medication.id}`)}
            className="gap-2"
          >
            <Bell className="w-4 h-4" />
            Notification Settings
          </Button>
          <Button
            variant="danger"
            size="icon"
            onClick={handleDelete}
            disabled={deleteMedication.isPending}
            aria-label="Delete medication"
          >
            {deleteMedication.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Pattern Learning Results */}
      {learnPatterns.data && (
        <Card className="bg-accent-subtle border-accent/10">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-accent" />
              <p className="text-sm font-medium text-ink">Pattern Analysis Complete</p>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {learnPatterns.data.time_window && (
                <div>
                  <p className="text-xs text-ink-secondary">Typical Time</p>
                  <p className="font-medium text-ink">
                    {(learnPatterns.data.time_window as Record<string, string>).avg_time}
                  </p>
                </div>
              )}
              {learnPatterns.data.streak && (
                <div>
                  <p className="text-xs text-ink-secondary">Current Streak</p>
                  <p className="font-medium text-ink">
                    {(learnPatterns.data.streak as Record<string, number>).current_streak} days
                  </p>
                </div>
              )}
              <div>
                <p className="text-xs text-ink-secondary">Patterns Found</p>
                <p className="font-medium text-ink">{learnPatterns.data.patterns_created}</p>
              </div>
              <div>
                <p className="text-xs text-ink-secondary">Schedules Updated</p>
                <p className="font-medium text-ink">{learnPatterns.data.schedules_updated}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left: Dose History */}
        <div className="col-span-2 space-y-4">
          {/* Instructions */}
          {medication.instructions && (
            <Card>
              <CardContent className="p-4">
                <p className="text-sm text-ink-secondary">
                  <strong className="text-ink">Instructions:</strong>{' '}
                  {medication.instructions}
                </p>
              </CardContent>
            </Card>
          )}

          {/* Dose History */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Dose History</CardTitle>
            </CardHeader>
            <CardContent>
              {!doses || doses.length === 0 ? (
                <p className="text-sm text-ink-secondary text-center py-8">
                  No doses logged yet. Log your first dose to start tracking.
                </p>
              ) : (
                <div className="divide-y divide-black/[0.04]">
                  {doses.map((dose, i) => (
                    <motion.div
                      key={dose.id}
                      initial={prefersReducedMotion ? {} : { opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center justify-between py-3"
                    >
                      <div className="flex items-center gap-3">
                        {dose.was_skipped ? (
                          <SkipForward className="w-4 h-4 text-status-caution" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-status-verified" />
                        )}
                        <div>
                          <p className="text-sm text-ink">
                            {new Date(dose.taken_at).toLocaleString()}
                          </p>
                          {dose.notes && (
                            <p className="text-xs text-ink-tertiary">{dose.notes}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {dose.was_skipped && dose.skip_reason && (
                          <Badge variant="caution">{dose.skip_reason}</Badge>
                        )}
                        {dose.variance_minutes !== null && (
                          <span className={cn(
                            'text-xs',
                            Math.abs(dose.variance_minutes) <= 15
                              ? 'text-status-verified'
                              : 'text-status-caution'
                          )}>
                            {dose.variance_minutes > 0 ? '+' : ''}{dose.variance_minutes}m
                          </span>
                        )}
                        <Badge variant={dose.was_skipped ? 'caution' : 'verified'}>
                          {dose.was_skipped ? 'Skipped' : 'Taken'}
                        </Badge>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Adherence + Schedules */}
        <div className="space-y-4">
          <AdherenceDashboard
            stats={stats}
            isLoading={statsLoading}
            isError={statsError}
          />

          <ScheduleEditor
            schedules={medication.schedules}
            onAdd={handleAddSchedule}
            onDelete={handleDeleteSchedule}
            isAdding={createSchedule.isPending}
            isDeleting={deleteSchedule.isPending}
          />

          {/* Related Lab Results (UX-001 correlation) */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-ink-secondary" />
                Related Lab Results
              </CardTitle>
            </CardHeader>
            <CardContent>
              {relatedObservations.length === 0 ? (
                <p className="text-sm text-ink-tertiary text-center py-4" data-testid="related-labs-empty">
                  No lab results collected during this medication period.
                </p>
              ) : (
                <div className="divide-y divide-black/[0.04]" data-testid="related-labs-list">
                  {relatedObservations.slice(0, 8).map((obs) => (
                    <a
                      key={obs.id}
                      href={`/trends?analyte=${obs.analyte_canonical}`}
                      className="flex items-center justify-between py-2.5 hover:bg-surface-muted/50 -mx-2 px-2 rounded-lg transition-colors"
                      aria-label={`View ${obs.analyte_canonical} trend`}
                    >
                      <div>
                        <p className="text-sm font-medium text-ink">{obs.analyte_canonical}</p>
                        <p className="text-xs text-ink-tertiary">
                          {obs.collected_at
                            ? new Date(obs.collected_at).toLocaleDateString()
                            : 'No date'}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-mono font-medium text-ink">
                          {obs.value ?? obs.value_text ?? '-'}
                        </span>
                        <span className="text-xs text-ink-secondary ml-1">{obs.unit}</span>
                      </div>
                    </a>
                  ))}
                  {relatedObservations.length > 8 && (
                    <p className="text-xs text-ink-tertiary text-center pt-2">
                      +{relatedObservations.length - 8} more
                    </p>
                  )}
                </div>
              )}
              {excludedUndatedCount > 0 && (
                <p
                  className="text-xs text-ink-tertiary pt-3"
                  data-testid="related-labs-undated"
                >
                  {excludedUndatedCount} undated result
                  {excludedUndatedCount === 1 ? ' is' : 's are'} not shown — a
                  result with no collection date cannot be placed in this
                  medication's window.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Meta Info */}
          <Card>
            <CardContent className="p-4 space-y-2 text-xs text-ink-tertiary">
              <p>Started: {new Date(medication.started_at).toLocaleDateString()}</p>
              {medication.ended_at && (
                <p>Ended: {new Date(medication.ended_at).toLocaleDateString()}</p>
              )}
              <p>Last updated: {new Date(medication.updated_at).toLocaleDateString()}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dose Logging Modal */}
      {showLogModal && (
        <DoseLoggingModal
          medicationName={medication.name}
          onSubmit={handleLogDose}
          onClose={() => setShowLogModal(false)}
          isSubmitting={logDose.isPending}
        />
      )}
    </div>
  );
}
