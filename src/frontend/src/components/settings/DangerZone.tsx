/**
 * Danger Zone — irreversible profile deletion (PROF-DEL-001).
 *
 * Deliberately hard to trigger by accident: the user must download their data,
 * re-enter their password, and type an exact confirmation phrase.
 *
 * The copy here is load-bearing. Deleting the sealed encryption key is what
 * makes the vault unreadable — we do not claim the bytes are overwritten,
 * because SSD wear-levelling makes that claim false.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useDeleteProfile, PROFILE_DELETE_CONFIRMATION } from '@/services/profiles';
import { useAuthStore } from '@/stores/authStore';
import { getApiBaseUrl } from '@/services/api';

export function DangerZone() {
  const navigate = useNavigate();
  const profileId = useAuthStore((state) => state.profileId);
  const deleteProfile = useDeleteProfile();

  const [expanded, setExpanded] = useState(false);
  const [exported, setExported] = useState(false);
  const [password, setPassword] = useState('');
  const [phrase, setPhrase] = useState('');
  const [error, setError] = useState<string | null>(null);

  const canDelete =
    exported && password.length > 0 && phrase === PROFILE_DELETE_CONFIRMATION;

  const handleDelete = async () => {
    if (!profileId || !canDelete) return;
    setError(null);
    try {
      await deleteProfile.mutateAsync({
        profileId,
        data: {
          password,
          confirmation_phrase: phrase,
          export_acknowledged: true,
        },
      });
      navigate('/');
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Deletion failed. Nothing was removed.'
      );
    }
  };

  return (
    <Card className="border-status-attention/40">
      <CardHeader>
        <CardTitle className="text-status-attention">Danger Zone</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <h3 className="font-semibold">Delete this profile</h3>
          <p className="text-sm text-muted-foreground mt-1">
            This removes your encrypted health record from this device: every
            document, lab result, medication and note. Your encryption key is
            destroyed, which makes the data unreadable. This cannot be undone,
            and there is no cloud copy to restore from.
          </p>
        </div>

        {!expanded ? (
          <Button variant="secondary" onClick={() => setExpanded(true)}>
            Delete profile…
          </Button>
        ) : (
          <div className="space-y-4 rounded-md border border-status-attention/40 p-4">
            <div>
              <p className="text-sm font-medium">1. Download your data first</p>
              <p className="text-xs text-muted-foreground mb-2">
                Once deleted it cannot be recovered, so take a copy while you can.
              </p>
              <a
                href={`${getApiBaseUrl()}/export/json`}
                onClick={() => setExported(true)}
                className="text-sm underline"
                download
              >
                Download my data (JSON)
              </a>
              <label className="flex items-center gap-2 mt-2 text-sm">
                <input
                  type="checkbox"
                  checked={exported}
                  onChange={(e) => setExported(e.target.checked)}
                />
                I have downloaded my data, or I don&apos;t want a copy
              </label>
            </div>

            <div>
              <label
                htmlFor="danger-password"
                className="text-sm font-medium block mb-1"
              >
                2. Confirm your password
              </label>
              <input
                id="danger-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
              />
            </div>

            <div>
              <label htmlFor="danger-phrase" className="text-sm font-medium block mb-1">
                3. Type <code className="font-mono">{PROFILE_DELETE_CONFIRMATION}</code>
              </label>
              <input
                id="danger-phrase"
                type="text"
                value={phrase}
                onChange={(e) => setPhrase(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm font-mono"
                placeholder={PROFILE_DELETE_CONFIRMATION}
              />
            </div>

            {error && (
              <p role="alert" className="text-sm text-status-attention">
                {error}
              </p>
            )}

            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  setExpanded(false);
                  setPassword('');
                  setPhrase('');
                  setError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDelete}
                disabled={!canDelete || deleteProfile.isPending}
              >
                {deleteProfile.isPending
                  ? 'Deleting…'
                  : 'Permanently delete this profile'}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
