import { useState } from 'react';
import { CheckCircle, X, Loader2, SkipForward } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { DoseLog } from '@/services/types';

interface DoseLoggingModalProps {
  medicationName: string;
  onSubmit: (data: DoseLog) => void;
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
  onSubmit,
  onClose,
  isSubmitting,
}: DoseLoggingModalProps) {
  const [mode, setMode] = useState<'taken' | 'skipped'>('taken');
  const [skipReason, setSkipReason] = useState('');
  const [notes, setNotes] = useState('');

  const handleSubmit = () => {
    onSubmit({
      taken_at: new Date().toISOString(),
      log_method: 'manual',
      was_skipped: mode === 'skipped',
      skip_reason: mode === 'skipped' ? skipReason || undefined : undefined,
      notes: notes.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />

      {/* Modal */}
      <Card className="relative z-10 w-full max-w-md shadow-elevated">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Log Dose</CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>

        <CardContent className="space-y-4">
          <p className="text-sm text-ink-secondary">
            Logging for <strong className="text-ink">{medicationName}</strong>
          </p>

          {/* Taken / Skipped Toggle */}
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setMode('taken')}
              className={cn(
                'flex items-center justify-center gap-2 p-3 rounded-xl text-sm font-medium transition-all',
                'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
                mode === 'taken'
                  ? 'bg-status-verified-subtle text-status-verified border-2 border-status-verified/30'
                  : 'bg-surface-muted text-ink-secondary border-2 border-transparent hover:bg-surface-sunken'
              )}
            >
              <CheckCircle className="w-4 h-4" />
              Taken
            </button>
            <button
              type="button"
              onClick={() => setMode('skipped')}
              className={cn(
                'flex items-center justify-center gap-2 p-3 rounded-xl text-sm font-medium transition-all',
                'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
                mode === 'skipped'
                  ? 'bg-status-caution-subtle text-status-caution border-2 border-status-caution/30'
                  : 'bg-surface-muted text-ink-secondary border-2 border-transparent hover:bg-surface-sunken'
              )}
            >
              <SkipForward className="w-4 h-4" />
              Skipped
            </button>
          </div>

          {/* Skip Reason */}
          {mode === 'skipped' && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-ink">Reason</label>
              <div className="flex flex-wrap gap-2">
                {skipReasons.map((reason) => (
                  <button
                    key={reason.value}
                    type="button"
                    onClick={() => setSkipReason(reason.value)}
                    className={cn(
                      'px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
                      'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-1',
                      skipReason === reason.value
                        ? 'bg-status-caution-subtle text-status-caution'
                        : 'bg-surface-muted text-ink-secondary hover:bg-surface-sunken'
                    )}
                  >
                    {reason.label}
                  </button>
                ))}
              </div>
            </div>
          )}

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
                'px-3 py-2 text-sm text-ink',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
                'resize-none'
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
    </div>
  );
}
