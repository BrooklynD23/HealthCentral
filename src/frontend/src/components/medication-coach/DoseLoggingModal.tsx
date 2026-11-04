import { useEffect, useRef, useState } from 'react';
import { CheckCircle, X, Loader2, SkipForward } from 'lucide-react';
import { m, AnimatePresence } from 'framer-motion';
import { Button, IconButton } from '@/components/ui';
import { Modal } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';
import type { DoseLog, MedicationSchedule } from '@/services/types';

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
  // The control that opened the dialog, read at first render (before the dialog moves focus into itself).
  const [opener] = useState<HTMLElement | null>(() =>
    document.activeElement instanceof HTMLElement ? document.activeElement : null
  );
  // Radix hands focus to its Trigger on close, and this dialog has none (the parent mounts it), so the opener
  // gets focus back when the dialog unmounts. That covers Close, Escape and a successful submit (the parent
  // unmounts the dialog then, without onClose). React StrictMode also runs this cleanup once at mount, so the
  // re-run setup cancels the timer that cleanup queued; the opener is not focused while the dialog is open.
  const returnFocus = useRef<number | undefined>(undefined);
  useEffect(() => {
    window.clearTimeout(returnFocus.current);
    return () => {
      // The timer runs after Radix's own unmount work, which would otherwise win.
      returnFocus.current = window.setTimeout(() => opener?.focus(), 0);
    };
  }, [opener]);
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
    // M0 (still): the dose text is T0, so the dialog opens and closes with no motion of its own. The scrim may fade.
    <Modal
      name="DoseLoggingModal"
      variant="dialog"
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title="Log Dose"
      still
      showClose={false}
    >
      <IconButton
        variant="ghost"
        aria-label="Close"
        onClick={onClose}
        className="absolute right-4 top-4 rounded-[10px]"
      >
        <X className="w-4 h-4" aria-hidden="true" />
      </IconButton>

      <div className="space-y-4">
        <p className="text-sm text-ink-secondary" data-t0="">
          Logging for <strong className="text-ink">{medicationName}</strong>
        </p>

            {/* Taken / Skipped Toggle */}
            <div className="grid grid-cols-2 gap-2 p-1 bg-surface-muted rounded-2xl">
              <button
                type="button"
                onClick={() => setMode('taken')}
                className={cn(
                  'flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-all relative',
                  'focus:outline-hidden focus:ring-2 focus:ring-accent focus:ring-offset-2',
                  mode === 'taken'
                    ? 'bg-surface-elevated text-status-verified shadow-xs'
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
                  'focus:outline-hidden focus:ring-2 focus:ring-accent focus:ring-offset-2',
                  mode === 'skipped'
                    ? 'bg-surface-elevated text-status-caution shadow-xs'
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
                <m.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 overflow-hidden"
                >
                  <label className="inline-block text-sm font-medium text-ink">Reason</label>
                  <div className="flex flex-wrap gap-2">
                    {skipReasons.map((reason) => (
                      <button
                        key={reason.value}
                        type="button"
                        onClick={() => setSkipReason(reason.value)}
                        className={cn(
                          'px-3 py-1.5 rounded-full text-xs font-medium transition-all',
                          'focus:outline-hidden focus:ring-2 focus:ring-accent focus:ring-offset-1',
                          skipReason === reason.value
                            ? 'bg-status-caution text-[var(--on-status)] shadow-xs'
                            : 'bg-surface-sunken text-ink-secondary hover:bg-black/8'
                        )}
                      >
                        {reason.label}
                      </button>
                    ))}
                  </div>
                </m.div>
              )}
            </AnimatePresence>

            {/* Notes */}
            <div className="space-y-1.5">
              <label htmlFor="dose-notes" className="inline-block text-sm font-medium text-ink">
                Notes (optional)
              </label>
              <textarea
                id="dose-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Any notes about this dose..."
                rows={2}
                className={cn(
                  'flex w-full rounded-xl border border-black/8 bg-surface-elevated',
                  'px-3 py-2 text-sm text-ink placeholder:text-ink-tertiary',
                  'focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-0 focus:border-accent',
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
      </div>
    </Modal>
  );
}
