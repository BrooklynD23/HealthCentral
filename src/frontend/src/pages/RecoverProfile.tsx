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
      setRotatedCode(result.recovery_code);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'That recovery code is not valid.'
      );
    }
  };

  if (rotatedCode) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-4">
          <p className="text-sm text-ink-secondary text-center">
            Your password has been reset and your records are unlocked.
          </p>
          <RecoveryCodeCard
            code={rotatedCode}
            title="Your new recovery code"
            acknowledgeLabel="Continue to my records"
            onAcknowledge={() => navigate('/inbox')}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="w-full max-w-md">
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
                <Link to="/setup" className="text-sm underline">
                  Back
                </Link>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label
                    htmlFor="recover-profile"
                    className="text-sm font-medium block mb-1"
                  >
                    Profile
                  </label>
                  <select
                    id="recover-profile"
                    value={profileId}
                    onChange={(e) => setProfileId(e.target.value)}
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  >
                    <option value="">Select a profile…</option>
                    {recoverable.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label
                    htmlFor="recover-code"
                    className="text-sm font-medium block mb-1"
                  >
                    Recovery code
                  </label>
                  <input
                    id="recover-code"
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX"
                    autoComplete="off"
                    className="w-full rounded-md border px-3 py-2 text-sm font-mono"
                  />
                  <p className="text-xs text-ink-secondary mt-1">
                    Spacing and capitalisation don&apos;t matter.
                  </p>
                </div>

                <div>
                  <label
                    htmlFor="recover-password"
                    className="text-sm font-medium block mb-1"
                  >
                    New password
                  </label>
                  <input
                    id="recover-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                    className="w-full rounded-md border px-3 py-2 text-sm"
                  />
                  <p className="text-xs text-ink-secondary mt-1">
                    At least 8 characters, with an uppercase letter, a lowercase
                    letter and a digit.
                  </p>
                </div>

                {error && (
                  <p role="alert" className="text-sm text-status-attention">
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

                <Link to="/setup" className="text-sm underline block text-center">
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
