/**
 * Recovery code management (SEC-RECOV-002).
 *
 * SEC-RECOV-001 shipped the backend and the `useIssueRecoveryCode` hook, and
 * nothing ever called it — so a code was issued only at profile creation, and a
 * profile made before the feature existed could never get one. RecoverProfile
 * tells the user a code "can only be created while you can still sign in";
 * this is the signed-in surface that makes that instruction followable.
 *
 * The code seals a second copy of the profile's DEK. It is therefore shown
 * exactly once, held only in component state, and never written to the query
 * cache, a store, or localStorage — anywhere the app could read it back, an
 * attacker with the same access could too, which would defeat sealing it.
 * The mutation that fetched it is reset once it settles and has gcTime 0, so
 * the TanStack mutation cache does not keep the code or the password either.
 */

import { useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
} from '@/components/ui';
import { useProfiles, useIssueRecoveryCode } from '@/services/profiles';
import { useAuthStore } from '@/stores/authStore';

export function RecoveryCodeCard() {
  const { profileId } = useAuthStore();
  // `has_recovery_code` is on ProfileListResponse (`GET /profiles/`), not on
  // ProfileResponse (`GET /profiles/{id}`) — so the flag comes from the list,
  // not from `useProfile`. An e2e run caught this: the unit test had mocked the
  // field onto the single-profile response, where the API never returns it.
  const { data: profiles } = useProfiles();
  const profile = profiles?.find((p) => p.id === profileId);
  const issueRecoveryCode = useIssueRecoveryCode();

  const [password, setPassword] = useState('');
  const [code, setCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasCode = profile?.has_recovery_code ?? false;
  const actionLabel = hasCode ? 'Replace recovery code' : 'Create recovery code';

  const handleIssue = () => {
    if (!profileId || !password) return;
    setError(null);
    issueRecoveryCode.mutate(
      { profileId, password },
      {
        onSuccess: (result) => {
          setCode(result.recovery_code);
          // The password has done its job; holding it serves nothing.
          setPassword('');
        },
        onError: (err) =>
          setError(
            err instanceof Error
              ? err.message
              : 'Could not create a recovery code.'
          ),
        // Detach from the mutation so its gcTime of 0 removes it, with the
        // password in its variables and the code in its data, from the cache.
        onSettled: () => issueRecoveryCode.reset(),
      }
    );
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          Recovery code
          {hasCode && <Badge variant="verified">Active</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-ink-secondary">
          A recovery code unlocks this profile if you forget your password.
          Without one, a forgotten password means the health record in this
          profile cannot be recovered by anyone — including us.
        </p>

        {hasCode && (
          <p
            className="text-sm text-status-attention"
            data-testid="recovery-code-replace-warning"
          >
            This profile already has a recovery code. Creating a new one
            immediately invalidates the old one, so any copy you have written
            down will stop working.
          </p>
        )}

        {code ? (
          <div className="space-y-2">
            <p
              className="font-mono text-lg tracking-wide select-all"
              data-testid="recovery-code-value"
            >
              {code}
            </p>
            <p
              className="text-sm text-status-attention"
              data-testid="recovery-code-once-warning"
            >
              Write this down and store it somewhere safe. It will not be shown
              again — we cannot display it a second time, only replace it.
            </p>
            <Button variant="secondary" onClick={() => setCode(null)}>
              I have saved it
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label
                htmlFor="recovery-code-password"
                className="text-sm font-medium block mb-1"
              >
                Confirm your password
              </label>
              <input
                id="recovery-code-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>
            <Button
              onClick={handleIssue}
              disabled={!password || issueRecoveryCode.isPending}
            >
              {issueRecoveryCode.isPending ? 'Creating…' : actionLabel}
            </Button>
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-status-attention">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
