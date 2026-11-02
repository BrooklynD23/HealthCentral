import { useId } from 'react';
import { Info } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { Popover } from '@/components/ui/Popover';
import { Switch } from '@/components/ui/Switch';
import { cn } from '@/utils/cn';

/**
 * The relabelled safety toggle (plan §3.6, until SAFETY-MODE-TOGGLE wires real
 * behaviour). It is a disabled, off switch: it changes no state anywhere.
 *
 * Desktop shows the note beside the switch. Phones show an info button whose
 * popover carries the same copy. The note stays in the DOM for the description.
 */
export function SafetyModeToggle({ className }: { className?: string }) {
  const switchId = useId();
  const noteId = useId();

  // The column has a fixed width on desktop. Its auto width came from the note's text, and that text
  // measured 376.8 px in the fallback face and 307 px once Source Sans loaded, so the note moved
  // while the page settled. 384 px holds the fallback on one line, so the note's rect stays put.
  return (
    <div className={cn('flex flex-col gap-1 lg:w-96', className)}>
      <div className="flex items-center gap-2">
        <Switch
          id={switchId}
          checked={false}
          disabled
          aria-disabled="true"
          aria-describedby={noteId}
        />
        <label
          htmlFor={switchId}
          data-t0
          data-safety-toggle-label
          className="inline-flex min-h-target items-center whitespace-nowrap text-sm font-medium text-ink lg:min-h-0"
        >
          Stricter safety mode
        </label>
        <Popover
          label="About the stricter safety mode"
          still
          trigger={
            <IconButton variant="ghost" aria-label="About the stricter safety mode" className="lg:hidden">
              <Info className="h-4 w-4" aria-hidden="true" />
            </IconButton>
          }
        >
          {/* Phones have no visible note (it is lg-only below), so the note opens the popover, above the long text. */}
          <div className="max-w-xs space-y-2">
            <p data-t0 data-safety-toggle-popover-note className="text-sm font-medium text-ink">
              Not available yet. The standard safety checks always run.
            </p>
            <p data-t0 data-safety-toggle-popover className="text-sm text-ink">
              Asclexis checks every answer for medical advice and against your own records. These checks are always
              on and cannot be turned off. A stricter mode is being designed; this switch will turn it on when it is
              ready.
            </p>
          </div>
        </Popover>
      </div>
      <p id={noteId} data-t0 data-safety-toggle-note className="hidden text-xs text-ink-secondary lg:block">
        Not available yet. The standard safety checks always run.
      </p>
    </div>
  );
}
