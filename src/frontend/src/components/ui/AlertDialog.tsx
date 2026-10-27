import { Modal, type DialogProps } from './Dialog';

/**
 * A Dialog with `role="alertdialog"`: for a decision the user must make, such as a
 * destructive confirmation. An outside click does not dismiss it; Escape does.
 * It has no close button, so the content must offer an explicit action.
 *
 * On open, focus moves to the cancel action: the element with `data-alert-cancel` inside
 * the content. Caller order does not matter, so a destructive action may come first in the
 * DOM without taking focus, and Enter on the open dialog cancels. With no such element the
 * default focus stays, and an error is logged.
 */
export function AlertDialog(props: DialogProps) {
  return (
    <Modal
      {...props}
      name="AlertDialog"
      variant="dialog"
      role="alertdialog"
      dismissOnOutsideClick={false}
      showClose={false}
      onOpenAutoFocus={focusCancelOnOpen}
    />
  );
}

/** Radix calls this once per open. Without a cancel element it logs and keeps the default focus. */
function focusCancelOnOpen(event: Event) {
  const content = event.currentTarget as HTMLElement | null;
  const cancel = content?.querySelector<HTMLElement>('[data-alert-cancel]');
  if (!cancel) {
    console.error(
      '`AlertDialog` has no cancel action: mark one with `data-alert-cancel` so it gets focus on open.'
    );
    return;
  }
  event.preventDefault();
  cancel.focus();
}
