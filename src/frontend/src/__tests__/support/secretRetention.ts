/**
 * Test helpers for secret retention (RCC, RCC-2).
 *
 * A password or recovery code must not outlive the request that needed it:
 * not in the TanStack mutation cache, and not in the page's React state.
 */
import type { QueryClient } from '@tanstack/react-query';

function holds(value: unknown, needle: string): boolean {
  if (typeof value === 'string') return value.includes(needle);
  if (value && typeof value === 'object') {
    try {
      return (JSON.stringify(value) ?? '').includes(needle);
    } catch {
      // Effect hooks hold circular lists; they never hold user input.
      return false;
    }
  }
  return false;
}

/** Mutations in this client's cache whose variables or result contain `needle`. */
export function cachedMutationsContaining(queryClient: QueryClient, needle: string): number {
  return queryClient
    .getMutationCache()
    .getAll()
    .filter((m) => holds({ v: m.state.variables, d: m.state.data }, needle)).length;
}

/**
 * Positive control: records whether the cache ever held `needle`, so a
 * "nothing cached" assertion cannot pass because nothing was ever cached.
 */
export function watchCacheFor(
  queryClient: QueryClient,
  needle: string
): { seen: { value: boolean }; unsubscribe: () => void } {
  const seen = { value: false };
  const unsubscribe = queryClient.getMutationCache().subscribe((event) => {
    const m = event.mutation;
    if (m && holds({ v: m.state.variables, d: m.state.data }, needle)) seen.value = true;
  });
  return { seen, unsubscribe };
}

// React fiber tags whose memoizedState is a hook list.
const HOOK_FIBER_TAGS = new Set([0, 11, 15]); // FunctionComponent, ForwardRef, SimpleMemoComponent

/**
 * True if any hook state in the committed React tree under `container`
 * contains `needle`. Walks React 18 internals (`__reactContainer$…` →
 * FiberRoot.current); callers must assert a positive control first.
 * Limits: reads hook state of function/forwardRef/memo components only (not
 * class state, context values or props); values with a cycle, or Error
 * objects, are skipped by JSON.stringify; the alternate fiber is not read.
 */
export function reactStateContains(container: HTMLElement, needle: string): boolean {
  const key = Object.keys(container).find((k) => k.startsWith('__reactContainer$'));
  if (!key) throw new Error('reactStateContains: container is not a React root');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hostRoot = (container as any)[key];
  let found = false;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const visit = (fiber: any): void => {
    for (let f = fiber; f && !found; f = f.sibling) {
      let hook = HOOK_FIBER_TAGS.has(f.tag) ? f.memoizedState : null;
      while (hook && !found) {
        if (holds(hook.memoizedState, needle)) found = true;
        hook = hook.next;
      }
      if (f.child && !found) visit(f.child);
    }
  };
  visit(hostRoot.stateNode.current);
  return found;
}
