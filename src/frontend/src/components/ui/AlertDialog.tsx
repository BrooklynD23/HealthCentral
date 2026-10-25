import { Modal, type DialogProps } from './Dialog';

/**
 * A Dialog with `role="alertdialog"`: for a decision the user must make, such as a
 * destructive confirmation. An outside click does not dismiss it; Escape does.
 * It has no close button, so the content must offer an explicit action.
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
