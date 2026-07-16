import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Input } from '@/components/ui';
import { cn } from '@/utils/cn';
import type { MedicationCreate, Medication } from '@/services/types';

interface MedicationFormProps {
  initialValues?: Partial<Medication>;
  /**
   * 'add' keeps the create labels even when fields are pre-filled (e.g. a
   * reconciliation suggestion seeding the name). Defaults to 'edit' when
   * initialValues are present, 'add' otherwise.
   */
  mode?: 'add' | 'edit';
  onSubmit: (data: MedicationCreate) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
  className?: string;
}

const frequencies = [
  { value: 'once_daily', label: 'Once daily' },
  { value: 'twice_daily', label: 'Twice daily' },
  { value: 'three_times_daily', label: '3x daily' },
  { value: 'four_times_daily', label: '4x daily' },
  { value: 'every_other_day', label: 'Every other day' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'as_needed', label: 'As needed' },
];

const dosageForms = [
  'tablet', 'capsule', 'liquid', 'injection', 'patch',
  'inhaler', 'cream', 'drops', 'other',
];

export function MedicationForm({
  initialValues,
  mode,
  onSubmit,
  onCancel,
  isSubmitting,
  className,
}: MedicationFormProps) {
  const isEdit = mode ? mode === 'edit' : Boolean(initialValues);
  const [name, setName] = useState(initialValues?.name ?? '');
  const [genericName, setGenericName] = useState(initialValues?.generic_name ?? '');
  const [dosageAmount, setDosageAmount] = useState(
    initialValues?.dosage_amount?.toString() ?? ''
  );
  const [dosageUnit, setDosageUnit] = useState(initialValues?.dosage_unit ?? 'mg');
  const [dosageForm, setDosageForm] = useState(initialValues?.dosage_form ?? 'tablet');
  const [frequency, setFrequency] = useState(initialValues?.frequency ?? 'once_daily');
  const [instructions, setInstructions] = useState(initialValues?.instructions ?? '');
  const [reminderEnabled, setReminderEnabled] = useState(
    initialValues?.reminder_enabled ?? false
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      name: name.trim(),
      generic_name: genericName.trim() || undefined,
      dosage_amount: dosageAmount ? parseFloat(dosageAmount) : undefined,
      dosage_unit: dosageUnit || undefined,
      dosage_form: dosageForm || undefined,
      frequency,
      instructions: instructions.trim() || undefined,
      reminder_enabled: reminderEnabled,
    });
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>
          {isEdit ? 'Edit Medication' : 'Add Medication'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Name */}
          <div className="space-y-1.5">
            <label htmlFor="med-name" className="text-sm font-medium text-ink">
              Medication Name *
            </label>
            <Input
              id="med-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Lisinopril"
              required
            />
          </div>

          {/* Generic Name */}
          <div className="space-y-1.5">
            <label htmlFor="med-generic" className="text-sm font-medium text-ink">
              Generic Name
            </label>
            <Input
              id="med-generic"
              value={genericName}
              onChange={(e) => setGenericName(e.target.value)}
              placeholder="e.g. lisinopril"
            />
          </div>

          {/* Dosage Row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label htmlFor="med-amount" className="text-sm font-medium text-ink">
                Amount
              </label>
              <Input
                id="med-amount"
                type="number"
                step="0.01"
                min="0"
                value={dosageAmount}
                onChange={(e) => setDosageAmount(e.target.value)}
                placeholder="10"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="med-unit" className="text-sm font-medium text-ink">
                Unit
              </label>
              <select
                id="med-unit"
                value={dosageUnit}
                onChange={(e) => setDosageUnit(e.target.value)}
                className={cn(
                  'flex h-[44px] w-full rounded-xl border border-black/[0.08] bg-surface-elevated',
                  'px-3 py-2 text-sm text-ink',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2'
                )}
              >
                <option value="mg">mg</option>
                <option value="mcg">mcg</option>
                <option value="g">g</option>
                <option value="ml">mL</option>
                <option value="units">units</option>
                <option value="puffs">puffs</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="med-form" className="text-sm font-medium text-ink">
                Form
              </label>
              <select
                id="med-form"
                value={dosageForm}
                onChange={(e) => setDosageForm(e.target.value)}
                className={cn(
                  'flex h-[44px] w-full rounded-xl border border-black/[0.08] bg-surface-elevated',
                  'px-3 py-2 text-sm text-ink',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2'
                )}
              >
                {dosageForms.map((form) => (
                  <option key={form} value={form}>
                    {form.charAt(0).toUpperCase() + form.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Frequency */}
          <div className="space-y-1.5">
            <label htmlFor="med-frequency" className="text-sm font-medium text-ink">
              Frequency
            </label>
            <select
              id="med-frequency"
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className={cn(
                'flex h-[44px] w-full rounded-xl border border-black/[0.08] bg-surface-elevated',
                'px-3 py-2 text-sm text-ink',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2'
              )}
            >
              {frequencies.map((freq) => (
                <option key={freq.value} value={freq.value}>
                  {freq.label}
                </option>
              ))}
            </select>
          </div>

          {/* Instructions */}
          <div className="space-y-1.5">
            <label htmlFor="med-instructions" className="text-sm font-medium text-ink">
              Instructions
            </label>
            <textarea
              id="med-instructions"
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g. Take with food"
              rows={2}
              className={cn(
                'flex w-full rounded-xl border border-black/[0.08] bg-surface-elevated',
                'px-3 py-2 text-sm text-ink',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2',
                'resize-none'
              )}
            />
          </div>

          {/* Reminder Toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={reminderEnabled}
              onChange={(e) => setReminderEnabled(e.target.checked)}
              className="w-4 h-4 rounded border-black/20 text-accent focus:ring-accent"
            />
            <span className="text-sm text-ink">Enable reminders</span>
          </label>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <Button type="button" variant="ghost" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" disabled={!name.trim() || isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isEdit ? (
                'Save Changes'
              ) : (
                'Add Medication'
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
