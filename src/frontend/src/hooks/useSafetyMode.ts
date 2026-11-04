import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { notify } from '@/components/ui/toast';
import { getSafetyMode, setSafetyMode, type SafetyModeResponse } from '@/services/assistant';

// Same shape as ['assistant', 'memory-settings'] (services/assistant.ts). The app's query defaults apply
// (staleTime 5 min, retry 1): every GET writes an audit row, so the staleTime is not shortened here.
const SAFETY_MODE_KEY = ['assistant', 'safety-mode'] as const;

/**
 * The per-profile stricter safety mode. `checked` is the server's value once it is known. Until then
 * (loading, a failed load, or a body with no boolean) `known` is false and `checked` is false, so the
 * caller keeps the switch disabled and a click sends nothing.
 *
 * The value is per profile. The lock flow's queryClient.clear() drops it, and it loads again after unlock.
 */
export function useSafetyMode() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: SAFETY_MODE_KEY, queryFn: getSafetyMode });

  // typeof, not coercion: a string or null from a broken body is "unknown", never "off".
  const serverValue = query.data?.strict_safety_mode;
  const value = typeof serverValue === 'boolean' ? serverValue : undefined;

  // One toast per failure streak. With no data, each refetch puts the query back to pending and then to
  // error again (isError goes false, then true), so an effect keyed on isError alone fires on every
  // window-focus refetch. The ref remembers the toast and is cleared only once a real value is known.
  const loadFailed = query.isError;
  const loadFailureShown = useRef(false);
  useEffect(() => {
    if (!loadFailed) {
      if (value !== undefined) loadFailureShown.current = false;
      return;
    }
    if (loadFailureShown.current) return;
    loadFailureShown.current = true;
    notify({ message: "Couldn't load the stricter safety mode setting." });
  }, [loadFailed, value]);

  // A ref, not mutation.isPending: a second click before React re-renders must still be ignored.
  const inFlight = useRef(false);

  const mutation = useMutation({
    mutationFn: setSafetyMode,
    onMutate: async (next: boolean) => {
      await queryClient.cancelQueries({ queryKey: SAFETY_MODE_KEY });
      const previous = queryClient.getQueryData<SafetyModeResponse>(SAFETY_MODE_KEY);
      queryClient.setQueryData<SafetyModeResponse>(SAFETY_MODE_KEY, { strict_safety_mode: next });
      return { previous };
    },
    onError: (_error, _next, context) => {
      // The query is gone after queryClient.clear() (lock flow): a late write would hand the old
      // profile's value to the next one.
      if (queryClient.getQueryState(SAFETY_MODE_KEY)) {
        if (context?.previous) queryClient.setQueryData(SAFETY_MODE_KEY, context.previous);
        // The PATCH may have committed before it failed (the audit commit comes after the flag's), so the
        // snapshot can be wrong. Read the server's value back instead of trusting it for the whole staleTime.
        void queryClient.invalidateQueries({ queryKey: SAFETY_MODE_KEY });
      }
      notify({ message: "Couldn't change the stricter safety mode setting." });
    },
    onSuccess: (response) => {
      if (!queryClient.getQueryState(SAFETY_MODE_KEY)) return; // cleared by the lock flow, see onError
      queryClient.setQueryData(SAFETY_MODE_KEY, response);
      // Nothing shown under the old mode stays cached under the new one. The literals are the private
      // QUERY_KEY constants of services/interpretations.ts (:17) and services/observations.ts (:11).
      // Explanations are reset, not invalidated: under the stricter mode the refetch of an unverified value
      // is refused (409), and an invalidated query keeps its last good data through a failed refetch.
      void queryClient.resetQueries({ queryKey: ['interpretations'] });
      void queryClient.invalidateQueries({ queryKey: ['observations', 'trends'] });
    },
    onSettled: () => {
      inFlight.current = false;
    },
  });

  function setStrict(next: boolean) {
    if (value === undefined || inFlight.current) return;
    inFlight.current = true;
    mutation.mutate(next);
  }

  return {
    /** The server's value, or false while it is unknown. */
    checked: value ?? false,
    /** True once the server's value is a real boolean. */
    known: value !== undefined,
    /** True only while the first GET is pending. */
    loading: query.isPending,
    setStrict,
  };
}
