import { useState } from 'react';
import { CheckCircle, X, Loader2, SkipForward } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, CardContent, CardHeader, CardTitle, modalVariants, backdropVariants } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { DoseLog, MedicationSchedule } from '@/services/types';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface DoseLoggingModalProps {
  medicationName: string;
  schedules?: MedicationSchedule[];
  onSubmit: (data: DoseLog, scheduleId?: string) => void;
  onClose: () => void;
  isSubmitting?: boolean;
}

const skipReasons = [
  { value: 'forgot', label: 'Forgot' },
  { value: 'side_effects', label: 'Side effects' },
  { value: 'ran_out', label: 'Ran out' },
  { value: 'felt_unnecessary', label: 'Felt unnecessary' },
  { value: 'doctor_advised', label: 'Doctor advised' },
  { value: 'other', label: 'Other' },
];

export function DoseLoggingModal({
  medicationName,
  schedules,
  onSubmit,
  onClose,
  isSubmitting,
}: DoseLoggingModalProps) {
  const prefersReducedMotion = useReducedMotion();
  const [mode, setMode] = useState<'taken' | 'skipped'>('taken');
  const [skipReason, setSkipReason] = useState('');
  const [notes, setNotes] = useState('');

  const handleSubmit = () => {
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();

    // Auto-match to nearest active schedule
    let matchedScheduleId: string | undefined;
    if (schedules && schedules.length > 0 && mode === 'taken') {
      let closestDist = Infinity;
      for (const sched of schedules) {
        if (!sched.is_active) continue;
        const [h, m] = sched.target_time.split(':').map(Number);
        const schedMinutes = h * 60 + m;
        const rawDist = Math.abs(nowMinutes - schedMinutes);
        const dist = Math.min(rawDist, 1440 - rawDist);
        if (dist < closestDist) {
          closestDist = dist;
          matchedScheduleId = sched.id;
        }
      }
    }

    onSubmit(
      {
        taken_at: now.toISOString(),
        log_method: 'manual',
        was_skipped: mode === 'skipped',
        skip_reason: mode === 'skipped' ? skipReason || undefined : undefined,
        notes: notes.trim() || undefined,
      },
      matchedScheduleId,
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <motion.div
        initial="initial"
        animate="animate"
        exit="exit"
        variants={backdropVariants}
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Modal */}
      <motion.div
        initial="initial"
        animate="animate"
        exit="exit"
        variants={prefersReducedMotion ? backdropVariants : modalVariants}
        className="relative z-10 w-full max-w-md"
      >
        <Card className="shadow-elevated border-black/[0.08]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Log Dose</CardTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="Close"
              className="h-8 w-8 rounded-lg"
            >
              <X className="w-4 h-4" />
            </Button>
          </CardHeader>

          <CardContent className="space-y-4">
            <p className="text-sm text-ink-secondary">
              Logging for <strong className="text-ink">{medicationName}</strong>
            </p>

            {/* Taken / Skipped Toggle */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-surface-muted rounded-2xl">
              <button
                type="button"
                onClick={() => setMode('taken')}
                className={cn(
                  'flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all relative',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
                  mode === 'taken'
                    ? 'bg-white text-status-verified shadow-sm'
                    : 'text-ink-secondary hover:text-ink'
                )}
              >
                <CheckCircle className={cn('w-4 h-4', mode === 'taken' ? 'text-status-verified' : 'text-ink-tertiary')} />
                Taken
              </button>
              <button
                type="button"
                onClick={() => setMode('skipped')}
                className={cn(
                  'flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all relative',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
                  mode === 'skipped'
                    ? 'bg-white text-status-caution shadow-sm'
                    : 'text-ink-secondary hover:text-ink'
                )}
              >
                <SkipForward className={cn('w-4 h-4', mode === 'skipped' ? 'text-status-caution' : 'text-ink-tertiary')} />
                Skipped
              </button>
            </div>

            {/* Skip Reason */}
            <AnimatePresence mode="wait">
              {mode === 'skipped' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 overflow-hidden"
                >
                  <label className="text-sm font-medium text-ink">Reason</label>
                  <div className="flex flex-wrap gap-2">
                    {skipReasons.map((reason) => (
                      <button
                        key={reason.value}
                        type="button"
                        onClick={() => setSkipReason(reason.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                          'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1',
                          skipReason === reason.value
                            ? 'bg-status-caution text-white shadow-sm'
                            : 'bg-surface-sunken text-ink-secondary hover:bg-black/[0.08]'
                        )}
                      >
                        {reason.label}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Notes */}
            <div className="space-y-1.5">
              <label htmlFor="dose-notes" className="text-sm font-medium text-ink">
                Notes (optional)
              </label>
              <textarea
                id="dose-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any notes about this dose..."
                rows={2}
                className={cn(
                  'flex w-full rounded-xl border border-black/[0.08] bg-surface-elevated',
                  'px-3 py-2 text-sm text-ink placeholder:text-ink-tertiary',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-0 focus:border-accent',
                  'resize-none transition-all'
                )}
              />
            </div>

            {/* Submit */}
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || (mode === 'skipped' && !skipReason)}
              className="w-full"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : mode === 'taken' ? (
                'Log as Taken'
              ) : (
                'Log as Skipped'
              )}
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
