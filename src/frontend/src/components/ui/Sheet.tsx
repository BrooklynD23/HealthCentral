import { useEffect, useState } from 'react';
import { Modal, type DialogProps, type ModalVariant } from './Dialog';

const DESKTOP_QUERY = '(min-width: 768px)';

function readIsDesktop(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia(DESKTOP_QUERY).matches
  );
}

/** Synchronous first read, so the first render already has the right side. */
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(readIsDesktop);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia(DESKTOP_QUERY);
    setIsDesktop(query.matches);

    const handleChange = (event: MediaQueryListEvent) => setIsDesktop(event.matches);
    query.addEventListener('change', handleChange);
    return () => query.removeEventListener('change', handleChange);
  }, []);

  return isDesktop;
}

/**
 * A panel that slides in from the bottom on phones and from the right on desktop
 * (M5). Dismissal, focus trap and the overlay-open event are the Dialog's.
 */
export function Sheet(props: DialogProps) {
  const isDesktop = useIsDesktop();
  const variant: ModalVariant = isDesktop ? 'sheet-side' : 'sheet-bottom';
  return <Modal {...props} name="Sheet" variant={variant} />;
}
