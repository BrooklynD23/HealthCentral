import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Circle,
  Info,
  Minus,
  UserCheck,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/utils/cn';

export type StatusChipState =
  | 'in-range'
  | 'above-range'
  | 'below-range'
  | 'not-checked'
  | 'checked-by-you'
  | 'caution'
  | 'info';

// Every state shows an icon and words. The words never say "normal" or
// "abnormal": a range is a range, and a value outside it is above or below the
// report's range (plan §2.2). In range is neutral, not the verified green, so it
// does not read as a verdict; only checked by you takes the verified token.
const STATES: Record<StatusChipState, { label: string; Icon: LucideIcon; tone: string }> = {
  'in-range': {
    label: 'In range',
    Icon: Minus,
    tone: 'bg-surface-sunken text-ink',
  },
  'above-range': {
    label: "Above the report's range",
    Icon: ArrowUp,
    tone: 'bg-status-attention-subtle text-status-attention',
  },
  'below-range': {
    label: "Below the report's range",
    Icon: ArrowDown,
    tone: 'bg-status-attention-subtle text-status-attention',
  },
  'not-checked': {
    label: 'Not yet checked',
    Icon: Circle,
    tone: 'bg-surface-muted text-ink-secondary',
  },
  'checked-by-you': {
    label: 'Checked by you',
    Icon: UserCheck,
    tone: 'bg-status-verified-subtle text-status-verified',
  },
  caution: {
    label: 'Caution',
    Icon: AlertTriangle,
    tone: 'bg-status-caution-subtle text-status-caution',
  },
  info: {
    label: 'Info',
    Icon: Info,
    tone: 'bg-status-info-subtle text-status-info',
  },
};

/** Range and verification words. The chip is T0 content, so it never animates (data-t0). */
export function StatusChip({ state, className }: { state: StatusChipState; className?: string }) {
  const { label, Icon, tone } = STATES[state];

  return (
    <span
      data-t0=""
      data-state={state}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        tone,
        className
      )}
    >
      <Icon aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
      {label}
    </span>
  );
}
