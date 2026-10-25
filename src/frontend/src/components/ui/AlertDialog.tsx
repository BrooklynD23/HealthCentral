import { Modal, type DialogProps } from './Dialog';

/**
 * A Dialog with `role="alertdialog"`: for a decision the user must make, such as a
 * destructive confirmation. An outside click does not dismiss it; Escape does.
 * It has no close button, so the content must offer an explicit action.
 *
 * Focus goes to the first focusable element on open, as in Dialog. Radix's AlertDialog
 * focuses Cancel instead, and this one does not. So put the cancel action first: if a
 * destructive action comes first, it gets focus and Enter confirms it.
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
    />
  );
}
