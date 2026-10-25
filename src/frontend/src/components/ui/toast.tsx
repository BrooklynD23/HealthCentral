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
}

/** Shows a toast. The text sits in an element with role="status". */
export function notify({ message, action, still = false }: NotifyOptions) {
  return toast(
    <span role="status" data-t0={still ? '' : undefined}>
      {message}
    </span>,
    {
      action,
      style: still ? { transition: 'none', opacity: 1 } : undefined,
    }
  );
}

// Layer from globals.css (--z-toast sits under --z-modal). Colours come from
// the tokens, through the variables sonner reads for its own surfaces.
const TOASTER_STYLE = {
  zIndex: 'var(--z-toast)',
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
