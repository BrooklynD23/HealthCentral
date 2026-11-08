import { useId } from 'react';
import { Info } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { Popover } from '@/components/ui/Popover';
import { Switch } from '@/components/ui/Switch';
import { useSafetyMode } from '@/hooks/useSafetyMode';
import { cn } from '@/utils/cn';

// Stage 3 of the note (SAFETY-NOTE-WORDING, "Specific, staged"): the owner's words plus the SAFETY-MODE-CITATIONS
// and SAFETY-MODE-VERIFIED-FE clauses. One constant feeds the desktop note and the phone popover. Later rows add one
// sentence each, before the last one.
const SAFETY_MODE_NOTE =
  "On: AI explanations of a single result need more verified support, and values you haven't checked get no explanation. New chat answers show their sources. The Results chart leaves out unchecked values. The standard safety checks always run.";

/**
 * The stricter safety mode switch (plan §3.6, wired by SAFETY-MODE-TOGGLE). It shows the per-profile
 * server value and sends a PATCH when changed. While that value is unknown (loading, a failed load, or a
 * body with no boolean) it is disabled and off, and a click sends nothing. The standard safety checks run
 * in every state; the switch never turns them off.
 *
 * Desktop shows the note beside the switch. Phones show an info button whose
 * popover carries the same copy. The note stays in the DOM for the description.
 */
export function SafetyModeToggle({ className }: { className?: string }) {
  const switchId = useId();
  const noteId = useId();
  const { checked, known, loading, setStrict } = useSafetyMode();

  // The column has a fixed width on desktop (lg:w-96) and the note has a fixed height (lg:h-16: 4 lines of
  // 16 px), so the note's rect does not move while the fonts load (its width came from the text, and the
  // fallback face and Source Sans measure differently). Four lines is the room the plan reserves for the
  // longest staged note (stage 3); the TopBar header (lg:h-24) is sized for it. HC-SMT-005 checks for clipping.
  return (
    <div className={cn('flex flex-col gap-1 lg:w-96', className)}>
      <div className="flex items-center gap-2">
        <Switch
          id={switchId}
          checked={checked}
          disabled={!known}
          aria-busy={loading || undefined}
          onCheckedChange={setStrict}
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
              {SAFETY_MODE_NOTE}
            </p>
            <p data-t0 data-safety-toggle-popover className="text-sm text-ink">
              Asclexis checks every answer for medical advice and against your own records. These checks are always
              on and cannot be turned off. This switch turns on a stricter mode for this profile. It never turns the
              standard checks off.
            </p>
          </div>
        </Popover>
      </div>
      <p
        id={noteId}
        data-t0
        data-safety-toggle-note
        className="hidden text-xs text-ink-secondary lg:block lg:h-16 lg:leading-4"
      >
        {SAFETY_MODE_NOTE}
      </p>
    </div>
  );
}
