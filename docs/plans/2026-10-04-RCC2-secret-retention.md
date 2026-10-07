# RCC-2 — Password and Recovery-Code Retention in Create, Recover and Delete Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Every new test is observed FAILING before the fix. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** owner-approved 2026-10-04 (gate RCC-2 in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 3, L1-B.
**Source:** RCC (PR #37) security review, out-of-scope findings HIGH 1-2 and MEDIUM 1-3. Follows [2026-10-04-RCC-recovery-code-cache.md](2026-10-04-RCC-recovery-code-cache.md), which fixed the same defect in `useIssueRecoveryCode`.
**Architectural:** no. No Codex review. `code-reviewer` + `security-reviewer` required.

**Goal:** After profile creation, recovery or a failed deletion settles, neither the TanStack mutation cache nor the page's React state still holds the password, the recovery code the user typed, or the recovery code the server returned. The one exception is the code being displayed, which stays in its one display state until the user leaves.

**Architecture:** The RCC fix again, applied to 3 more hooks. Each hook gets `gcTime: 0`, and each caller calls the mutation's `reset()` once `mutateAsync` settles. The pages also clear their own secret `useState` values on success.

**Tech Stack:** React 18, TypeScript, `@tanstack/react-query` 5.90.14, vitest 4, Testing Library.

**Spec:** the owner gate text below plus the PR #37 security-review findings. There is no separate spec.

## Global Constraints

- Owner gate RCC-2 (2026-10-04), verbatim: "Plan RCC-2 with the same fix (gcTime 0 + reset) and tests in all 3 hooks, plus clearing component state. One PR."
- L0 scope note (2026-10-04): `useCreateProfile` (`services/profiles.ts:120`, `pages/ProfileSetup.tsx:136`), `useRecoverProfile` (`:241`, `pages/RecoverProfile.tsx:45-49`), component state at `RecoverProfile.tsx:32-33` and `ProfileSetup.tsx:92`, and the `useDeleteProfile` password after a failed delete. "Do not touch backend auth code."
- Frontend only. No backend file. No dependency change. `useLogin` and `useUnlockProfile` have 0 callers and stay out of scope.
- **Base:** PR #37 was not merged when this phase started, so the branch is cut from #37's head `7113db5`. It needs #37's `useIssueRecoveryCode` pattern, and it touches the same files (`services/profiles.ts`, docs index). After #37 merges, merge `origin/main` and re-run Task 4.
- Frontend commands run from **Windows** (`powershell.exe`).
- Backend collected count stays **1346**.
- Explicit pathspecs. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Defects (measured at `7113db5`)

| # | Where | What stays in memory |
|---|---|---|
| 1 | `services/profiles.ts:116-133` `useCreateProfile`; caller `pages/ProfileSetup.tsx:136` `mutateAsync({display_name, password})` | Mutation `variables.password`; `data.recovery_code` and `data.access_token`. The default `gcTime` is 5 min, and the clock only starts once the observer detaches. The observer stays attached while ProfileSetup is mounted, which covers the whole code-display step. |
| 2 | `ProfileSetup.tsx:92` `password` state | Never cleared after creation. |
| 3 | `services/profiles.ts:238-258` `useRecoverProfile`; caller `pages/RecoverProfile.tsx:45-48` | `variables.data.recovery_code` (the old code) and `variables.data.new_password`; `data.recovery_code` (the rotated code) and the token. |
| 4 | `RecoverProfile.tsx:32-33` `code`, `newPassword` state | Never cleared after success. |
| 5 | `services/profiles.ts:212-231` `useDeleteProfile`; caller `components/settings/DangerZone.tsx:64` | After a **failed** delete, `variables.data.password` stays in the cache. On success, `queryClient.clear()` already empties it. |

The mechanism is unchanged from RCC: `reset()` alone leaves the entry for 5 min, and `gcTime: 0` alone leaves it while the observer is attached. Both halves are needed.

## Files (the complete list)

| File | Change |
|---|---|
| `src/frontend/src/__tests__/support/secretRetention.ts` (new) | Test helpers: `cachedMutationsContaining`, `watchCacheFor`, `reactStateContains`. It is not a test file: vitest `include` is `src/**/*.{test,spec}.{ts,tsx}`. |
| `src/frontend/src/__tests__/ProfileSetup.test.tsx` | `renderWithProviders` returns `queryClient` too; add FE-RCC2-001 and FE-RCC2-002. |
| `src/frontend/src/__tests__/RecoverProfile.test.tsx` (new) | FE-RCC2-003 and FE-RCC2-004. |
| `src/frontend/src/__tests__/DangerZone.test.tsx` (new) | FE-RCC2-005. |
| `src/frontend/src/services/profiles.ts` | `gcTime: 0` plus a 2-line comment in `useCreateProfile`, `useRecoverProfile` and `useDeleteProfile`. Nothing else. |
| `src/frontend/src/pages/ProfileSetup.tsx` | After `mutateAsync` resolves: `createProfile.reset(); setPassword('');`. In `catch`: `createProfile.reset();`. |
| `src/frontend/src/pages/RecoverProfile.tsx` | After `mutateAsync` resolves: `recover.reset(); setCode(''); setNewPassword('');`. In `catch`: `recover.reset();`. |
| `src/frontend/src/components/settings/DangerZone.tsx` | In the `handleDelete` `catch`: `deleteProfile.reset();`. |
| `docs/plans/2026-10-04-RCC2-secret-retention.md`, `docs/INDEX.md`, `docs/_link_graph.json` | This plan plus the regenerated index. |

On error, the typed password and code stay in the **inputs** on purpose, so the user can retry. This matches PR #37's settings card. Only the cache copy is dropped.

## Review Focus

1. **A state check that cannot fail.** `reactStateContains` walks React's fiber tree, which is an internal API. If the walk finds nothing, every "not contains" assertion passes vacuously. Each state test therefore asserts `true` **before** submit (positive control), and Task 1 Step 2 fails the run if any positive control fails.
2. **The code must still be shown.** Success paths assert the returned code is on screen after the cache and state checks.
3. **Retry after error.** FE-RCC2-002 and FE-RCC2-004 retry with a success response after the error, then check that the cache is clean again.
4. **Delete success.** `queryClient.clear()` already handles it, and adding `gcTime` does not change that. It is not separately tested.
5. **The fiber alternate.** React keeps a previous-render copy of state on the alternate fiber. The helper walks only `root.current`. That is the state the app can read back; the alternate is overwritten on the next render. This limit is accepted and named here.

---

### Task 0: Preconditions (STOP on any failure)

**Files:** none.

- [ ] **Step 1: Worktree, gate, base**

```bash
set -o pipefail
cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral && git fetch origin
git worktree add ../hc-rcc2 -b fix/rcc2-secret-retention 7113db5   # #37 head; use origin/main once #37 is merged
W=/mnt/c/Users/DangT/Documents/GitHub/hc-rcc2
git -C "$W" log --oneline -1                                      # 7113db5
grep -n '^| RCC-2 ' /mnt/c/Users/DangT/Documents/GitHub/hc-l0-docs/docs/capstone-report/owner-decisions-2026-09-27.md
```

- [ ] **Step 2: Windows baseline**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc2\src\frontend; npm ci; npx vitest run 2>&1 | Select-Object -Last 5"
```

Expected: `Test Files 32 passed (32)`, `Tests 188 passed (188)`. That matches L1's measurement at `7113db5` for PR #37.

### Task 1: Test helpers and failing tests (RED)

**Files:**
- Create: `src/frontend/src/__tests__/support/secretRetention.ts`
- Modify: `src/frontend/src/__tests__/ProfileSetup.test.tsx`
- Create: `src/frontend/src/__tests__/RecoverProfile.test.tsx`, `src/frontend/src/__tests__/DangerZone.test.tsx`

**Interfaces:**
- Produces: `cachedMutationsContaining(queryClient: QueryClient, needle: string): number`; `watchCacheFor(queryClient: QueryClient, needle: string): { seen: { value: boolean }; unsubscribe: () => void }`; `reactStateContains(container: HTMLElement, needle: string): boolean`.

- [ ] **Step 1: Helpers** (`src/__tests__/support/secretRetention.ts`)

```ts
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
export function watchCacheFor(queryClient: QueryClient, needle: string) {
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
```

- [ ] **Step 2: ProfileSetup tests.** In `ProfileSetup.test.tsx`, change `renderWithProviders` to return `{ ...render(...), queryClient }`. The existing callers ignore the return value. Add this import:

```tsx
import {
  cachedMutationsContaining,
  watchCacheFor,
  reactStateContains,
} from './support/secretRetention';
```

Then add a new `describe` at the end of the top-level `describe('ProfileSetup')`:

```tsx
  describe('RCC-2: no password or recovery code left behind', () => {
    const PASSWORD = 'SecurePass123';
    const CODE = 'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV';
    const created = {
      access_token: 'test-jwt-token-123',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-uuid-123',
      profile_name: 'My Health Profile',
      recovery_code: CODE,
    };

    async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
      await user.type(screen.getByLabelText('Profile Name'), 'My Health Profile');
      await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
      await user.click(screen.getByRole('button', { name: /create your profile/i }));
    }

    it('FE-RCC2-001: after creation neither the cache nor page state keeps the password or code', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockResolvedValueOnce(created);
      const { queryClient, container } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, PASSWORD);
      const code = watchCacheFor(queryClient, CODE);

      await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
      expect(reactStateContains(container, PASSWORD)).toBe(true); // positive control
      await user.clear(screen.getByPlaceholderText('Create a secure password'));
      await fillAndSubmit(user);

      expect(await screen.findByTestId('recovery-code')).toHaveTextContent(CODE);
      expect(pw.seen.value).toBe(true);
      expect(code.seen.value).toBe(true);
      pw.unsubscribe();
      code.unsubscribe();

      await waitFor(() => {
        expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0);
        expect(cachedMutationsContaining(queryClient, CODE)).toBe(0);
      });
      expect(reactStateContains(container, PASSWORD)).toBe(false);
      // The code itself is still displayed: it lives in its one display state.
      expect(screen.getByTestId('recovery-code')).toHaveTextContent(CODE);
    });

    it('FE-RCC2-002: a failed creation leaves no password in the cache, and a retry is clean too', async () => {
      const user = userEvent.setup();
      vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Server unavailable'));
      const { queryClient } = renderWithProviders(<ProfileSetup />);
      const pw = watchCacheFor(queryClient, PASSWORD);

      await fillAndSubmit(user);
      expect(await screen.findByText(/server unavailable/i)).toBeInTheDocument();
      expect(pw.seen.value).toBe(true);
      pw.unsubscribe();
      await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0));

      vi.mocked(api.apiPost).mockResolvedValueOnce(created);
      await user.click(screen.getByRole('button', { name: /create your profile/i }));
      expect(await screen.findByTestId('recovery-code')).toHaveTextContent(CODE);
      await waitFor(() => {
        expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0);
        expect(cachedMutationsContaining(queryClient, CODE)).toBe(0);
      });
    });
  });
```

- [ ] **Step 3: RecoverProfile tests** (`src/__tests__/RecoverProfile.test.tsx`, new)

```tsx
/**
 * RCC-2: recovery (SEC-RECOV-001) must not leave the old recovery code, the
 * new password, or the rotated code in the mutation cache, nor the typed code
 * and password in page state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecoverProfile } from '@/pages/RecoverProfile';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import {
  cachedMutationsContaining,
  watchCacheFor,
  reactStateContains,
} from './support/secretRetention';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const OLD_CODE = 'AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GGGG-HHHH';
const NEW_PASSWORD = 'NewPass123';
const ROTATED = 'R0TA-TEDC-0DEX-YZ12-3456-7890-ABCD-EFGH';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RecoverProfile />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...utils, queryClient };
}

async function fill(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(await screen.findByLabelText('Profile'), 'profile-1');
  await user.type(screen.getByLabelText('Recovery code'), OLD_CODE);
  await user.type(screen.getByLabelText('New password'), NEW_PASSWORD);
}

describe('RCC-2: RecoverProfile secret retention', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().clearAuth();
    vi.mocked(api.apiGet).mockResolvedValue([
      {
        id: 'profile-1',
        display_name: 'Test',
        has_password: true,
        has_recovery_code: true,
        created_at: '2026-01-01T00:00:00',
      },
    ]);
  });

  it('FE-RCC2-003: after recovery nothing keeps the old code, the new password or the rotated code', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-1',
      profile_name: 'Test',
      recovery_code: ROTATED,
    });
    const { queryClient, container } = renderPage();
    const oldCode = watchCacheFor(queryClient, OLD_CODE);
    const pw = watchCacheFor(queryClient, NEW_PASSWORD);
    const rotated = watchCacheFor(queryClient, ROTATED);

    await fill(user);
    expect(reactStateContains(container, OLD_CODE)).toBe(true); // positive control
    expect(reactStateContains(container, NEW_PASSWORD)).toBe(true); // positive control
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));

    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(ROTATED);
    expect(oldCode.seen.value).toBe(true);
    expect(pw.seen.value).toBe(true);
    expect(rotated.seen.value).toBe(true);
    [oldCode, pw, rotated].forEach((w) => w.unsubscribe());

    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, NEW_PASSWORD)).toBe(0);
      expect(cachedMutationsContaining(queryClient, ROTATED)).toBe(0);
    });
    expect(reactStateContains(container, OLD_CODE)).toBe(false);
    expect(reactStateContains(container, NEW_PASSWORD)).toBe(false);
    expect(screen.getByTestId('recovery-code')).toHaveTextContent(ROTATED);
  });

  it('FE-RCC2-004: a rejected code leaves nothing in the cache, and a retry is clean too', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('That recovery code is not valid.'));
    const { queryClient } = renderPage();
    const oldCode = watchCacheFor(queryClient, OLD_CODE);

    await fill(user);
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/not valid/i);
    expect(oldCode.seen.value).toBe(true);
    oldCode.unsubscribe();
    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, NEW_PASSWORD)).toBe(0);
    });

    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'tok',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: 'profile-1',
      profile_name: 'Test',
      recovery_code: ROTATED,
    });
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));
    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(ROTATED);
    await waitFor(() => {
      expect(cachedMutationsContaining(queryClient, OLD_CODE)).toBe(0);
      expect(cachedMutationsContaining(queryClient, ROTATED)).toBe(0);
    });
  });
});
```

- [ ] **Step 4: DangerZone test** (`src/__tests__/DangerZone.test.tsx`, new)

```tsx
/**
 * RCC-2: a failed profile deletion (PROF-DEL-001) must not leave the
 * password in the mutation cache. Success already calls queryClient.clear().
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DangerZone } from '@/components/settings/DangerZone';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { PROFILE_DELETE_CONFIRMATION } from '@/services/profiles';
import { cachedMutationsContaining, watchCacheFor } from './support/secretRetention';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(public status: number, public statusText: string, message: string) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const PASSWORD = 'DeleteMe123';

describe('RCC-2: DangerZone secret retention', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ profileId: 'profile-1' });
  });

  it('FE-RCC2-005: a failed delete leaves no password in the mutation cache', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiDelete).mockRejectedValueOnce(new Error('Incorrect password'));
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DangerZone />
        </MemoryRouter>
      </QueryClientProvider>
    );
    const pw = watchCacheFor(queryClient, PASSWORD);

    await user.click(screen.getByRole('button', { name: /delete profile/i }));
    await user.click(screen.getByLabelText(/i confirm i have a copy/i));
    await user.type(screen.getByLabelText(/confirm your password/i), PASSWORD);
    await user.type(screen.getByPlaceholderText(PROFILE_DELETE_CONFIRMATION), PROFILE_DELETE_CONFIRMATION);
    await user.click(screen.getByRole('button', { name: /permanently delete this profile/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect password/i);
    expect(pw.seen.value).toBe(true);
    pw.unsubscribe();
    await waitFor(() => expect(cachedMutationsContaining(queryClient, PASSWORD)).toBe(0));
  });
});
```

- [ ] **Step 5: Run and paste the FAIL**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc2\src\frontend; npx vitest run src/__tests__/ProfileSetup.test.tsx src/__tests__/RecoverProfile.test.tsx src/__tests__/DangerZone.test.tsx"
```

Expected: the existing ProfileSetup tests pass, and **all 5 FE-RCC2 tests FAIL** in a cache `waitFor` (`expected 1 to be +0`) or at a `reactStateContains(...) toBe(false)`. STOP and report if:
- any FE-RCC2 test passes, or
- any test fails at a positive control (`seen.value` or `reactStateContains(...) toBe(true)`), or
- a query cannot find its element. Report the exact error; do not change a label in product code.

### Task 2: Fix (GREEN) and commit

**Files:** `services/profiles.ts`, `pages/ProfileSetup.tsx`, `pages/RecoverProfile.tsx`, `components/settings/DangerZone.tsx`.

- [ ] **Step 1: `gcTime: 0` in the 3 hooks.** Put this in each `useMutation({...})` of `useCreateProfile`, `useDeleteProfile` and `useRecoverProfile`, directly after `mutationFn`:

```ts
    // Variables carry the password (and recovery code); drop the mutation
    // from the cache as soon as nothing observes it (RCC-2).
    gcTime: 0,
```

- [ ] **Step 2: ProfileSetup.** Replace the `mutateAsync` block (`:136-139`) and add a reset to the `catch`:

```tsx
      const created = await createProfile.mutateAsync({
        display_name: displayName.trim() || 'My Health Profile',
        password,
      });
      // RCC-2: the password has done its job. Detach the mutation (gcTime 0
      // then removes it, with the password and code) and clear the field.
      createProfile.reset();
      setPassword('');
```

At the top of the existing `catch (err) {` block, add `createProfile.reset();` as its first line.

- [ ] **Step 3: RecoverProfile.** Replace the `try` body (`:45-49`) and add a reset to the `catch`:

```tsx
      const result = await recover.mutateAsync({
        profileId,
        data: { recovery_code: code, new_password: newPassword },
      });
      // RCC-2: the old code and the new password have done their job.
      recover.reset();
      setCode('');
      setNewPassword('');
      setRotatedCode(result.recovery_code);
```

At the top of the existing `catch (err) {` block, add `recover.reset();` as its first line.

- [ ] **Step 4: DangerZone.** At the top of the `catch (err) {` block in `handleDelete` (`:73`), add:

```tsx
      // RCC-2: a failed delete must not leave the password in the cache.
      deleteProfile.reset();
```

- [ ] **Step 5: Run and paste the PASS**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc2\src\frontend; npx vitest run src/__tests__/ProfileSetup.test.tsx src/__tests__/RecoverProfile.test.tsx src/__tests__/DangerZone.test.tsx; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE"
```

Expected: all pass (ProfileSetup's 5 existing tests + 2, RecoverProfile 2, DangerZone 1), `tsc=0`, `lint=0` with 0 errors. The helper's 2 `eslint-disable-next-line` comments keep `no-explicit-any` silent.

- [ ] **Step 6: Commit** (2 commits: tests with helper, then fix. Both are made after GREEN; the RED output pasted in Task 1 is the evidence.)

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/hc-rcc2
T="src/frontend/src/__tests__/support/secretRetention.ts src/frontend/src/__tests__/ProfileSetup.test.tsx src/frontend/src/__tests__/RecoverProfile.test.tsx src/frontend/src/__tests__/DangerZone.test.tsx"
F="src/frontend/src/services/profiles.ts src/frontend/src/pages/ProfileSetup.tsx src/frontend/src/pages/RecoverProfile.tsx src/frontend/src/components/settings/DangerZone.tsx"
git add -- $T && git commit -m "test(profiles): RCC-2 secret-retention tests for create, recover and delete" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- $T
git add -- $F && git commit -m "fix(profiles): keep passwords and recovery codes out of mutation cache and page state" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- $F
git status --short   # clean
```

### Task 3: Break it on purpose (L1, at the PR head)

For each line below: delete it by line number (`grep -n` first), run the 3 test files on Windows, then `git checkout -- <file>`.

| Removed line | Must turn red |
|---|---|
| `gcTime: 0` in `useCreateProfile` | FE-RCC2-001, 002 |
| `createProfile.reset();` after `mutateAsync` (ProfileSetup) | FE-RCC2-001 |
| `setPassword('');` (ProfileSetup) | FE-RCC2-001 (state) |
| `gcTime: 0` in `useRecoverProfile` | FE-RCC2-003, 004 |
| `recover.reset();` after `mutateAsync` (RecoverProfile) | FE-RCC2-003 |
| `setCode('');` (RecoverProfile) | FE-RCC2-003 (state) |
| `gcTime: 0` in `useDeleteProfile` | FE-RCC2-005 |
| `deleteProfile.reset();` (DangerZone) | FE-RCC2-005 |

A row that stays green is a finding. Report it; do not weaken the test. (`setNewPassword('')` shares FE-RCC2-003's state assertion with `setCode('')`. Removing it alone must also fail on the `NEW_PASSWORD` state check.) The `catch` resets in ProfileSetup and RecoverProfile are each covered by 002 and 004.

### Task 4: Verification (L1) and PR

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc2\src\frontend; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build; echo build=\$LASTEXITCODE; npx vitest run"
cd /mnt/c/Users/DangT/Documents/GitHub/hc-rcc2
git diff --name-only 7113db5...HEAD      # only the files in the table
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check
```

Expected: all rc 0. vitest **34 files, 193 tests** (188 + 5). The PR body states the base (`7113db5`, PR #37's head, while #37 is unmerged), the gate, the commands and outputs, and the break-it table. Reviews: `code-reviewer` and `security-reviewer` (opus).

## Stop gates

- Any file outside the table, any backend file, any dependency change.
- An FE-RCC2 test passes before Task 2, or fails at a positive control.
- A break-it row stays green.
- vitest total other than 193 at the PR head on this base.

## Rollback

One PR: `git revert <merge sha>`. In-memory behaviour only; nothing is persisted.

## Out of scope

- `useLogin` and `useUnlockProfile` (`services/profiles.ts:135`, `:153`): 0 callers today. They would need the same `gcTime: 0` if they are ever used.
- The 401 sign-out on a wrong password at the settings recovery card (`services/api.ts:65-68`), and the issue-while-navigating-away case. Both are owner items from PR #37.
