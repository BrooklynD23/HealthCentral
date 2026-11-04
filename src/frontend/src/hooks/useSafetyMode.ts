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

  // Keyed on the error state, so a repeat failed refetch does not stack toasts.
  const loadFailed = query.isError;
  useEffect(() => {
    if (loadFailed) notify({ message: "Couldn't load the stricter safety mode setting." });
  }, [loadFailed]);

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
      if (context?.previous) queryClient.setQueryData(SAFETY_MODE_KEY, context.previous);
      notify({ message: "Couldn't change the stricter safety mode setting." });
    },
    onSuccess: (response) => {
      queryClient.setQueryData(SAFETY_MODE_KEY, response);
      // Nothing shown under the old mode stays cached under the new one. The literals are the private
      // QUERY_KEY constants of services/interpretations.ts (:17) and services/observations.ts (:11).
      void queryClient.invalidateQueries({ queryKey: ['interpretations'] });
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
