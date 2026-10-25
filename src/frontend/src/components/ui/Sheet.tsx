import { useEffect, useState } from 'react';
import { Modal, type DialogProps, type ModalVariant } from './Dialog';

// Plan §3.2: the sidebar appears at >= 1024 px. Below that, More opens a bottom sheet.
const DESKTOP_QUERY = '(min-width: 1024px)';

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
 * A panel that slides in from the bottom below 1024 px and from the right at 1024 px and
 * up (M5). Dismissal, focus trap and the overlay-open event are the Dialog's.
 */
export function Sheet(props: DialogProps) {
  const isDesktop = useIsDesktop();
  const variant: ModalVariant = isDesktop ? 'sheet-side' : 'sheet-bottom';
  return <Modal {...props} name="Sheet" variant={variant} />;
}
