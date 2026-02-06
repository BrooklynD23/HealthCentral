import { ShieldAlert } from 'lucide-react';
import { cn } from '@/utils/cn';

interface DisclaimerBannerProps {
  className?: string;
}

export function DisclaimerBanner({ className }: DisclaimerBannerProps) {
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl',
        'bg-status-caution-subtle border border-status-caution/20',
        className
      )}
    >
      <ShieldAlert className="w-5 h-5 text-status-caution flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-medium text-ink">
          For informational purposes only
        </p>
        <p className="text-xs text-ink-secondary mt-1 leading-relaxed">
          AI-generated interpretations are not medical advice. Always consult
          your healthcare provider before making decisions based on lab results.
          Critical or unexpected values should be reviewed by a physician.
        </p>
      </div>
    </div>
  );
}
