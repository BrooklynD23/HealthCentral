import { useEffect, useRef } from 'react';

type RefetchFn = () => void | Promise<unknown>;

export function useAutoRefresh(
  refetch: RefetchFn,
  intervalMs = 30_000,
  enabled = true
): void {
  const refetchRef = useRef(refetch);

  useEffect(() => {
    refetchRef.current = refetch;
  }, [refetch]);

  useEffect(() => {
    if (!enabled || intervalMs <= 0) {
      return;
    }

    const timerId = window.setInterval(() => {
      void refetchRef.current();
    }, intervalMs);

    return () => {
      window.clearInterval(timerId);
    };
  }, [enabled, intervalMs]);
}
