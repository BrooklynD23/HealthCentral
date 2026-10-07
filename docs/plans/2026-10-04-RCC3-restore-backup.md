# RCC-3 — Restore Password Out of the Mutation Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Every new test is observed FAILING before the fix. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** approved by the owner on 2026-10-04 (gate RCC-3 in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 3, L1-B.
**Source:** RCC-2 PR #42 code review, out-of-scope MAJOR: `useRestoreBackup` is the 5th mutation that carries a password, and the only one left unfixed (recurring-failures §9).
**Architectural:** no. No Codex review. Reviews: `code-reviewer` + `security-reviewer`.

**Goal:** Once a backup restore settles, whether it succeeds or fails, the restore password is gone from both the TanStack mutation cache and React state.

**Architecture:** Apply the same fix as [RCC](2026-10-04-RCC-recovery-code-cache.md) and [RCC-2](2026-10-04-RCC2-secret-retention.md). `useRestoreBackup` gets `gcTime: 0`. `BackupCard.handleRestore` calls `restoreBackup.reset()` once `mutateAsync` settles, on both success and error. The component already clears its `password` state on success (`BackupCard.tsx:122`) and whenever the target changes (`:64-67`).

**Tech Stack:** React 18, TypeScript, `@tanstack/react-query` 5.90.14, vitest 4.

## Global Constraints

- Owner gate RCC-3 (2026-10-04), verbatim: "Same small fix as RCC-2, done by L1-B." L0 scope note: "useRestoreBackup (services/backup.ts:173, BackupCard.tsx:113) — gcTime 0 + reset() on settle, clear any password component state; test-first with positive control; break-it."
- Out of scope, per the owner: AUTH-401-LOGOUT ("registered for later; do not touch") and `useLogin`/`useUnlockProfile` ("leave").
- **Base:** #37 and #42 are not merged, so this branch is cut from #42's head `dd8edb6`. It reuses #42's `__tests__/support/secretRetention.ts`. After #37 and #42 merge, merge `origin/main` and re-run Task 3.
- Frontend only, run from **Windows**. Backend collected count stays at **1346**. Explicit pathspecs. Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Defect (measured at `dd8edb6`)

| Where | What stays in memory |
|---|---|
| `src/frontend/src/services/backup.ts:172-200` `useRestoreBackup`: no `gcTime` | `variables.data.password` stays in the mutation cache for 5 min after the observer detaches. While `BackupCard` is mounted, the observer is attached, so the entry has no time limit. |
| `src/frontend/src/components/settings/BackupCard.tsx:108-134` `handleRestore`: no `reset()` | **Failure:** the cache entry above. **Success:** `onSuccess` runs `queryClient.clear()`, which empties the cache, but the observer's result snapshot keeps `variables` (with the password) in the `useMutation` hook state until a reset. |

Component `password` state is already cleared on success (`:122`) and on a target change (`:64-67`). After a failure it stays in the input on purpose so the user can retry, the same as RCC and RCC-2. Nothing to add there.

## Files (the complete list)

| File | Change |
|---|---|
| `src/frontend/src/__tests__/BackupRestoreFlow.test.tsx` | `renderCard()` also returns `queryClient`. Add FE-RCC3-001 (failure, then retry) and FE-RCC3-002 (success, state). |
| `src/frontend/src/services/backup.ts` | `useRestoreBackup`: `gcTime: 0` with a 2-line comment. |
| `src/frontend/src/components/settings/BackupCard.tsx` | `handleRestore`: `restoreBackup.reset();` right after `mutateAsync` resolves, and as the first line of `catch`. |
| `docs/plans/2026-10-04-RCC3-restore-backup.md`, `docs/INDEX.md`, `docs/_link_graph.json` | This plan and the regenerated index. |

## Review Focus

1. **The success path clears the cache anyway.** `queryClient.clear()` means a cache-only test cannot fail on success. FE-RCC3-002 therefore asserts on **React state** (`reactStateContains`), with a positive control taken before submit.
2. **The restore notice and sign-out still happen.** FE-BKUP-002 must stay green. `reset()` runs after `onSuccess`, so the notice and `clearAuth()` are unaffected.
3. **Retry after failure.** FE-RCC3-001 retries and then checks the cache again.

---

### Task 0: Preconditions (STOP on any failure)

- [ ] `git -C ../hc-rcc3 log --oneline -1` → `dd8edb6`. `grep -n '^| RCC-3 ' /mnt/c/Users/DangT/Documents/GitHub/hc-l0-docs/docs/capstone-report/owner-decisions-2026-09-27.md` must print the row (L0 records it; if it is absent, STOP).
- [ ] Windows: `powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc3\src\frontend; npm ci; npx vitest run src/__tests__/BackupRestoreFlow.test.tsx"`. Expected: 2 passed.

### Task 1: Failing tests (RED)

**Files:** `src/frontend/src/__tests__/BackupRestoreFlow.test.tsx`

- [ ] **Step 1.** Import the helpers and make `renderCard` return its client:

```tsx
import {
  cachedMutationsContaining,
  watchCacheFor,
  reactStateContains,
} from './support/secretRetention';
```

```tsx
function renderCard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BackupCard />
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...utils, queryClient };
}
```

- [ ] **Step 2.** Add these 2 tests inside `describe('FE-BKUP: restore flow')`, after FE-BKUP-002:

```tsx
  async function fillRestoreForm(user: ReturnType<typeof userEvent.setup>, password: string) {
    const buttons = await screen.findAllByRole('button', { name: /restore…/i });
    await user.click(buttons[0]);
    await user.type(screen.getByLabelText(/confirm your password/i), password);
    await user.type(
      screen.getByPlaceholderText(BACKUP_RESTORE_CONFIRMATION),
      BACKUP_RESTORE_CONFIRMATION
    );
  }

  it('FE-RCC3-001: a failed restore leaves no password in the mutation cache, and a retry is clean too', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Incorrect password'));
    const { queryClient } = renderCard();
    const pw = watchCacheFor(queryClient, 'WrongHorse1');

    await fillRestoreForm(user, 'WrongHorse1');
    await user.click(screen.getByRole('button', { name: /restore this backup/i }));
    expect(await screen.findByText(/incorrect password/i)).toBeInTheDocument();
    expect(pw.seen.value).toBe(true); // positive control
    pw.unsubscribe();
    await waitFor(() => expect(cachedMutationsContaining(queryClient, 'WrongHorse1')).toBe(0));

    // The typed password stays in the field for a retry; the retry is cleaned up too.
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Incorrect password'));
    await user.click(screen.getByRole('button', { name: /restore this backup/i }));
    await waitFor(() => expect(api.apiPost).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(cachedMutationsContaining(queryClient, 'WrongHorse1')).toBe(0));
  });

  it('FE-RCC3-002: after a successful restore no React state keeps the password', async () => {
    const user = userEvent.setup();
    vi.mocked(api.apiPost).mockResolvedValueOnce({ files_restored: 5, safety_copy_count: 5 });
    const { container } = renderCard();

    await fillRestoreForm(user, 'CorrectHorse1');
    expect(reactStateContains(container, 'CorrectHorse1')).toBe(true); // positive control
    await user.click(screen.getByRole('button', { name: /restore this backup/i }));

    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false));
    await waitFor(() => expect(reactStateContains(container, 'CorrectHorse1')).toBe(false));
  });
```

- [ ] **Step 3.** Run the file and paste the FAIL.

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc3\src\frontend; npx vitest run src/__tests__/BackupRestoreFlow.test.tsx"
```

Expected: FE-BKUP-001 and FE-BKUP-002 pass. FE-RCC3-001 fails with `expected 1 to be +0`. FE-RCC3-002 fails with `expected true to be false`. STOP if any of these happens:
- FE-RCC3-001 or FE-RCC3-002 passes before the fix;
- a positive control fails;
- a query cannot find its element. Report the error; do not change product labels.

### Task 2: Fix (GREEN) and commit

- [ ] **Step 1.** In `services/backup.ts`, inside `useRestoreBackup`'s `useMutation({...})`, put this directly after `mutationFn`:

```ts
    // Variables hold the profile password. Drop the mutation from the cache
    // as soon as nothing observes it (RCC-3).
    gcTime: 0,
```

- [ ] **Step 2.** In `BackupCard.tsx` `handleRestore`, add a reset directly after the `mutateAsync` call (before `setMessage`):

```tsx
      // RCC-3: detach the mutation so neither the cache nor the hook's
      // result keeps the password.
      restoreBackup.reset();
```

Also add `restoreBackup.reset();` as the first line of the `catch (err) {` block.

- [ ] **Step 3.** Run the file plus tsc and lint; paste the PASS.

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rcc3\src\frontend; npx vitest run src/__tests__/BackupRestoreFlow.test.tsx; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE"
```

Expected: 4 passed, `tsc=0`, `lint=0` (0 errors).

- [ ] **Step 4.** Make 2 commits with explicit pathspecs:
  - `test(backup): RCC-3 restore password retention tests` covering `src/frontend/src/__tests__/BackupRestoreFlow.test.tsx`;
  - `fix(backup): keep the restore password out of the mutation cache and hook state` covering `src/frontend/src/services/backup.ts` and `src/frontend/src/components/settings/BackupCard.tsx`.

  End each with the Co-Authored-By line.

### Task 3: Break it on purpose (L1), then verify

| Removed line (find its number with `grep -n` first) | Must turn red |
|---|---|
| `gcTime: 0` in `useRestoreBackup` | FE-RCC3-001 |
| `restoreBackup.reset();` in `catch` | FE-RCC3-001 |
| `restoreBackup.reset();` after `mutateAsync` | FE-RCC3-002 |

After each break, restore with `git checkout -- <file>`. Then run on Windows: tsc, lint, build, and the full `npx vitest run`. Expected vitest result: **34 files, 195 tests** (193 + 2; no new test file). Finally run the docs gates and get both reviews.

## Stop gates

- Any file outside the table. Any edit to `services/api.ts`, which belongs to AUTH-401-LOGOUT.
- A new test passes before the fix, or a positive control fails.
- A break-it row stays green.
- vitest total is not 195 at the PR head on this base.

## Rollback

One PR: `git revert -m 1 <merge sha>`. In-memory behaviour only.
