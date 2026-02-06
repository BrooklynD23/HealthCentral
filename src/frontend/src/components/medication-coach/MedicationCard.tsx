import { motion } from 'framer-motion';
import {
  Pill,
  Clock,
  CheckCircle,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import type { Medication } from '@/services/types';

interface MedicationCardProps {
  medication: Medication;
  onQuickLog: (medicationId: string) => void;
  onViewDetail: (medicationId: string) => void;
  index?: number;
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

export function MedicationCard({
  medication,
  onQuickLog,
  onViewDetail,
  index = 0,
  className,
}: MedicationCardProps) {
  const prefersReducedMotion = useReducedMotion();

  const nextSchedule = medication.schedules.find((s) => s.is_active);

  return (
    <motion.div
      initial={prefersReducedMotion ? {} : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <Card
        className={cn(
          'hover:shadow-elevated transition-shadow duration-200 cursor-pointer',
          className
        )}
        onClick={() => onViewDetail(medication.id)}
      >
        <CardContent className="p-4">
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div
              className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
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
                  <span>
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
                  <span>
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

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <Button
                variant="primary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  onQuickLog(medication.id);
                }}
                className="gap-1.5"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Log
              </Button>
              <ChevronRight className="w-4 h-4 text-ink-tertiary" />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
