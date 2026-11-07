/**
 * Recover a profile with its one-time recovery code (SEC-RECOV-001).
 *
 * This is the "Forgot password?" path. Before this existed, a forgotten
 * password meant permanent, unrecoverable loss of the entire health record —
 * local-first means there is no server-side reset to fall back on.
 *
 * On success the code is *rotated*: the old one stops working and a new one is
 * shown once. Rotation rather than plain invalidation keeps the invariant
 * "there is always exactly one valid recovery code" — invalidating would leave
 * the user with no recovery at all until they remembered to generate one.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
} from '@/components/ui';
import { RecoveryCodeCard } from '@/components/profile/RecoveryCodeCard';
import { useProfiles, useRecoverProfile } from '@/services';

export function RecoverProfile() {
  const navigate = useNavigate();
  const { data: profiles, isLoading } = useProfiles();
  const recover = useRecoverProfile();

  const [profileId, setProfileId] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [rotatedCode, setRotatedCode] = useState<string | null>(null);

  const recoverable = (profiles ?? []).filter((p) => p.has_recovery_code);
  const canSubmit =
    profileId !== '' && code.trim() !== '' && newPassword.length >= 8;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const result = await recover.mutateAsync({
        profileId,
        data: { recovery_code: code, new_password: newPassword },
      });
      // RCC-2: the old code and the new password have done their job.
      recover.reset();
      setCode('');
      setNewPassword('');
      setRotatedCode(result.recovery_code);
    } catch (err) {
      recover.reset();
      setError(
        err instanceof Error ? err.message : 'That recovery code is not valid.'
      );
    }
  };

  if (rotatedCode) {
    return (
      <div className="min-h-screen bg-surface px-4 py-10 sm:px-6 sm:py-16">
        <div className="mx-auto w-full max-w-md space-y-4">
          <p className="text-sm text-ink-secondary text-center">
            Your password has been reset and your records are unlocked.
          </p>
          <RecoveryCodeCard
            code={rotatedCode}
            title="Your new recovery code"
            acknowledgeLabel="Continue to my records"
            onAcknowledge={() => navigate('/overview')}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface px-4 py-10 sm:px-6 sm:py-16">
      <div className="mx-auto w-full max-w-md">
        <Card>
          <CardHeader>
            <CardTitle>Recover your profile</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-sm text-ink-secondary">Loading profiles…</p>
            ) : recoverable.length === 0 ? (
              <div className="space-y-4">
                <p className="text-sm text-ink-secondary">
                  None of the profiles on this device has a recovery code. A
                  recovery code can only be created while you can still sign in,
                  so there is no way to unlock a profile without its password.
                </p>
                <p className="text-sm text-ink-secondary">
                  If you can still sign in to a profile, create one now under
                  Settings → Recovery code, before you need it.
                </p>
                <Link to="/setup" className="text-sm text-ink underline underline-offset-4">
                  Back
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-5">
                <p className="text-sm text-ink-secondary">
                  Use your saved recovery code to choose a new password.
                </p>
                <div>
                  <label
                    htmlFor="recover-profile"
                    className="block text-sm font-medium text-ink mb-1.5"
                  >
                    Profile
                  </label>
                  <select
                    id="recover-profile"
                    value={profileId}
                    onChange={(e) => setProfileId(e.target.value)}
                    className="h-11 w-full rounded-xl border border-[var(--line-strong)] bg-surface-elevated px-4 py-2 text-ink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:border-accent"
                  >
                    <option value="">Select a profile…</option>
                    {recoverable.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <Input
                  id="recover-code"
                  type="text"
                  label="Recovery code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                  autoComplete="off"
                  hint="Spacing and capitalisation don't matter."
                  className="font-mono"
                />

                <Input
                  id="recover-password"
                  type="password"
                  label="New password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  hint="At least 8 characters, with an uppercase letter, a lowercase letter and a digit."
                />

                {error && (
                  <p
                    role="alert"
                    data-t0=""
                    className="text-sm text-status-critical"
                  >
                    {error}
                  </p>
                )}

                <Button
                  type="submit"
                  disabled={!canSubmit || recover.isPending}
                  className="w-full"
                >
                  {recover.isPending ? 'Unlocking…' : 'Unlock my records'}
                </Button>

                <Link to="/setup" className="text-sm text-ink underline underline-offset-4 block text-center">
                  Back
                </Link>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default RecoverProfile;
