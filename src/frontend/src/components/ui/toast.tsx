import { type CSSProperties, useEffect } from 'react';
import { Toaster, toast } from 'sonner';

/**
 * Document event that UI-PRIM-OVERLAYS dispatches when a Dialog, AlertDialog
 * or Sheet opens (HC-UIOV-006). Toasts sit below the modal layer (DF-3), so
 * they step aside when an overlay opens. The name is fixed by the plan.
 */
export const OVERLAY_OPEN_EVENT = 'asclexis:overlay-open';

export interface NotifyOptions {
  message: string;
  action?: { label: string; onClick: () => void };
  /**
   * The message names a value or date (T0). The toast enters with no motion:
   * no transition and no opacity change (M0).
   */
  still?: boolean;
  id?: string | number;
}

// Sonner fades the content wrapper of a non-front toast (`[data-front=false]>*`
// sets opacity 0 with a .4 s transition). A still toast keeps its wrapper steady
// with !important utilities, so a second toast cannot fade its value out.
const STILL_CONTENT = 'opacity-100! transition-none!';

// Sonner's base rule starts every toast at opacity 0 and transform: var(--y) (translateY(100%)) until data-mounted turns
// true, so a toast "enters with no motion" only if that start state is cancelled. This does it for a still toast while it
// is not mounted. --y is left alone: stacking reads it once the toast is mounted. Sonner's CSS is unlayered, so the
// utilities need the ! form.
const STILL_TOAST = 'data-[mounted=false]:opacity-100! data-[mounted=false]:transform-none!';

/** Shows a toast. The text sits in an element with role="status". */
export function notify({ message, action, still = false, id }: NotifyOptions) {
  return toast(
    <span role="status" data-t0={still ? '' : undefined}>
      {message}
    </span>,
    {
      id,
      action,
      style: still ? { transition: 'none' } : undefined,
      classNames: still ? { toast: STILL_TOAST, content: STILL_CONTENT } : undefined,
    }
  );
}

// Layer from globals.css (--z-toast sits under --z-modal). Colours come from
// the tokens, through the variables sonner reads for its own surfaces. The
// body font token keeps toast text in the app's face, not sonner's default.
const TOASTER_STYLE = {
  zIndex: 'var(--z-toast)',
  fontFamily: 'var(--font-body)',
  '--normal-bg': 'var(--surface-1)',
  '--normal-text': 'var(--ink-1)',
  '--normal-border': 'var(--line)',
} as CSSProperties;

/** The app's one toaster. AppLayout mounts it (UI-SHELL). */
export function AppToaster() {
  useEffect(() => {
    const dismissVisible = () => {
      toast.dismiss();
    };
    document.addEventListener(OVERLAY_OPEN_EVENT, dismissVisible);
    return () => document.removeEventListener(OVERLAY_OPEN_EVENT, dismissVisible);
  }, []);

  return <Toaster position="bottom-center" style={TOASTER_STYLE} />;
}
