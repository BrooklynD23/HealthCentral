import { Link } from 'react-router-dom';
import {
  Pill,
  Clock,
  CheckCircle,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { Medication } from '@/services/types';

interface MedicationCardProps {
  medication: Medication;
  onQuickLog: (medicationId: string) => void;
  className?: string;
}

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

/**
 * One medication row. The details are a real link to the detail page (keyboard reachable, Enter opens it).
 * The Log button sits beside the link, not inside it: a button inside an anchor is invalid markup.
 * The dose and the schedule time are T0 (plan §2.7): they render with no motion.
 */
export function MedicationCard({
  medication,
  onQuickLog,
  className,
}: MedicationCardProps) {
  const nextSchedule = medication.schedules.find((s) => s.is_active);

  return (
    <Card className={cn('transition-shadow duration-200 hover:shadow-elevated', className)}>
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <Link
            to={`/medications/${medication.id}`}
            className="flex min-w-0 flex-1 items-start gap-4 rounded-xl focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
          >
            {/* Icon */}
            <div
              className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
                medication.is_active
                  ? 'bg-accent-subtle'
                  : 'bg-surface-muted'
              )}
            >
              <Pill
                className={cn(
                  'w-5 h-5',
                  medication.is_active ? 'text-accent' : 'text-ink-tertiary'
                )}
              />
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-medium text-ink truncate">
                  {medication.name}
                </h3>
                {!medication.is_active && (
                  <Badge variant="default">Inactive</Badge>
                )}
                {medication.reminder_enabled && (
                  <Badge variant="info">
                    <AlertCircle className="w-3 h-3" />
                    Reminders
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-3 text-xs text-ink-secondary">
                {medication.dosage_amount && (
                  <span data-t0="">
                    {medication.dosage_amount}
                    {medication.dosage_unit ?? ''}{' '}
                    {medication.dosage_form ?? ''}
                  </span>
                )}
                <span>{frequencyLabels[medication.frequency] ?? medication.frequency}</span>
              </div>

              {nextSchedule && (
                <div className="flex items-center gap-1.5 mt-2 text-xs text-ink-secondary">
                  <Clock className="w-3.5 h-3.5" />
                  <span data-t0="">
                    Next: {nextSchedule.target_time} ({nextSchedule.schedule_label})
                  </span>
                </div>
              )}

              {medication.instructions && (
                <p className="text-xs text-ink-tertiary mt-1.5 truncate">
                  {medication.instructions}
                </p>
              )}
            </div>

            <ChevronRight className="w-4 h-4 mt-1 shrink-0 text-ink-tertiary" aria-hidden="true" />
          </Link>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="primary"
              size="sm"
              onClick={() => onQuickLog(medication.id)}
              className="gap-1.5"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              Log
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
