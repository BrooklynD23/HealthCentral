import { useState } from 'react';
import { Plus, Clock, Trash2, Loader2 } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { MedicationSchedule, ScheduleCreate } from '@/services/types';

interface ScheduleEditorProps {
  schedules: MedicationSchedule[];
  onAdd: (data: ScheduleCreate) => void;
  onDelete: (scheduleId: string) => void;
  isAdding?: boolean;
  isDeleting?: boolean;
  className?: string;
}

const scheduleLabels = [
  { value: 'morning', label: 'Morning', defaultTime: '08:00' },
  { value: 'midday', label: 'Midday', defaultTime: '12:00' },
  { value: 'afternoon', label: 'Afternoon', defaultTime: '15:00' },
  { value: 'evening', label: 'Evening', defaultTime: '18:00' },
  { value: 'bedtime', label: 'Bedtime', defaultTime: '22:00' },
];

export function ScheduleEditor({
  schedules,
  onAdd,
  onDelete,
  isAdding,
  isDeleting,
  className,
}: ScheduleEditorProps) {
  const [showAdd, setShowAdd] = useState(false);
  const [newLabel, setNewLabel] = useState('morning');
  const [newTime, setNewTime] = useState('08:00');

  const handleAdd = () => {
    onAdd({
      schedule_label: newLabel,
      target_time: newTime,
      reminder_offset_minutes: 15,
      is_active: true,
    });
    setShowAdd(false);
    setNewLabel('morning');
    setNewTime('08:00');
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Schedules</CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowAdd(!showAdd)}
          className="gap-1.5"
        >
          <Plus className="w-3.5 h-3.5" />
          Add
        </Button>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Existing schedules */}
        {schedules.length === 0 && !showAdd && (
          <p className="text-sm text-ink-secondary text-center py-4">
            No schedules set. Add one to get reminders.
          </p>
        )}

        {schedules.map((schedule) => (
          <div
            key={schedule.id}
            className={cn(
              'flex items-center justify-between p-3 rounded-xl',
              'bg-surface-elevated border border-black/[0.04]'
            )}
          >
            <div className="flex items-center gap-3">
              <Clock className="w-4 h-4 text-ink-secondary" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-ink">
                    {schedule.target_time}
                  </span>
                  <Badge variant={schedule.is_active ? 'accent' : 'default'}>
                    {schedule.schedule_label}
                  </Badge>
                </div>
                {schedule.adaptive_window_start && schedule.adaptive_window_end && (
                  <p className="text-xs text-ink-tertiary mt-0.5">
                    Window: {schedule.adaptive_window_start} - {schedule.adaptive_window_end}
                  </p>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(schedule.id)}
              disabled={isDeleting}
              className="text-ink-tertiary hover:text-status-attention"
              aria-label={`Delete ${schedule.schedule_label} schedule`}
            >
              {isDeleting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </Button>
          </div>
        ))}

        {/* Add new schedule */}
        {showAdd && (
          <div className="p-3 rounded-xl bg-accent-subtle border border-accent/10 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium text-ink">Label</label>
                <select
                  value={newLabel}
                  onChange={(e) => {
                    setNewLabel(e.target.value);
                    const preset = scheduleLabels.find((s) => s.value === e.target.value);
                    if (preset) setNewTime(preset.defaultTime);
                  }}
                  className={cn(
                    'flex h-[36px] w-full rounded-lg border border-black/[0.08] bg-white',
                    'px-2 py-1 text-sm text-ink',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent'
                  )}
                >
                  {scheduleLabels.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-ink">Time</label>
                <input
                  type="time"
                  value={newTime}
                  onChange={(e) => setNewTime(e.target.value)}
                  className={cn(
                    'flex h-[36px] w-full rounded-lg border border-black/[0.08] bg-white',
                    'px-2 py-1 text-sm text-ink',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent'
                  )}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAdd(false)}
              >
                Cancel
              </Button>
              <Button size="sm" onClick={handleAdd} disabled={isAdding}>
                {isAdding ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  'Add Schedule'
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
