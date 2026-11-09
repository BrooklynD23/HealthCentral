/**
 * Danger Zone — irreversible profile deletion (PROF-DEL-001).
 *
 * Deliberately hard to trigger by accident: the user must download their data,
 * re-enter their password, and type an exact confirmation phrase.
 *
 * The copy here is load-bearing. Deleting the sealed encryption key is what
 * makes the vault unreadable — we do not claim the bytes are overwritten,
 * because SSD wear-levelling makes that claim false.
 *
 * UI-PG-SECURITY: the steps live in an AlertDialog, in their original order
 * (copy checkbox, password, typed phrase). The dialog and every warning in it
 * are `still` and carry `data-t0` (plan 2.7): no entrance motion on T0 text.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, CardContent, CardHeader, CardTitle, Input } from '@/components/ui';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { Checkbox } from '@/components/ui/Checkbox';
import { useDeleteProfile, PROFILE_DELETE_CONFIRMATION } from '@/services/profiles';
import { useAuthStore } from '@/stores/authStore';
import { useCreateBackup, downloadBackupArchive } from '@/services/backup';

const DELETE_WARNING =
  'This removes your encrypted health record from this device: every ' +
  'document, lab result, medication and note, along with any backups ' +
  'this app is holding for you. Your encryption key is destroyed, which ' +
  'makes the data unreadable. This cannot be undone, and there is no ' +
  'cloud copy to restore from.';

export function DangerZone() {
  const navigate = useNavigate();
  const profileId = useAuthStore((state) => state.profileId);
  const deleteProfile = useDeleteProfile();

  const createBackup = useCreateBackup();

  const [expanded, setExpanded] = useState(false);
  const [exported, setExported] = useState(false);
  const [backupNote, setBackupNote] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [phrase, setPhrase] = useState('');
  const [error, setError] = useState<string | null>(null);

  const canDelete =
    exported && password.length > 0 && phrase === PROFILE_DELETE_CONFIRMATION;

  /**
   * Take a full backup and hand it to the user before anything is destroyed.
   *
   * This replaced a plain `<a href="/export/json" download>`, which had two
   * problems: an anchor does not send the Authorization header, so it simply
   * 401'd; and `/export/json` covers observations only, so it would have
   * handed over a partial copy of a record about to be erased. A backup is the
   * full-fidelity, restorable artifact.
   */
  const handleBackupAndDownload = async () => {
    setError(null);
    setBackupNote(null);
    try {
      const result = await createBackup.mutateAsync();
      await downloadBackupArchive(result.backup_id);
      setExported(true);
      setBackupNote(`Backed up ${result.file_count} file(s) and downloaded the archive.`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Could not create a backup.'
      );
    }
  };

  const closeDialog = () => {
    setExpanded(false);
    setPassword('');
    setPhrase('');
    setError(null);
  };

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
      // RCC-2: a failed delete must not leave the password in the cache.
      deleteProfile.reset();
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
          <p className="text-sm text-ink-secondary mt-1" data-t0="">
            {DELETE_WARNING}
          </p>
        </div>

        <AlertDialog
          open={expanded}
          onOpenChange={(next) => (next ? setExpanded(true) : closeDialog())}
          still
          className="top-8 max-h-[calc(100dvh-4rem)] max-w-lg translate-y-0"
          title="Delete this profile?"
          description={<span data-t0="">{DELETE_WARNING}</span>}
          trigger={<Button variant="secondary">Delete profile…</Button>}
        >
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-ink">1. Take a backup first</p>
              <p className="text-xs text-ink-secondary mb-2" data-t0="">
                Deleting also removes the backups stored on this device, so a
                downloaded copy is the only one that survives. A backup includes
                your documents, results and the key that opens them, and can be
                restored later.
              </p>
              <Button
                size="sm"
                variant="secondary"
                onClick={handleBackupAndDownload}
                disabled={createBackup.isPending}
              >
                {createBackup.isPending
                  ? 'Backing up…'
                  : 'Back up and download'}
              </Button>
              {backupNote && (
                <p className="text-xs text-ink-secondary mt-2">{backupNote}</p>
              )}
              <div className="flex items-start gap-3 mt-3">
                <Checkbox
                  id="danger-exported"
                  checked={exported}
                  onCheckedChange={(checked) => setExported(checked === true)}
                />
                {/* Self-attested: the app cannot verify that a copy was kept,
                    and the wording should not imply otherwise. */}
                <label htmlFor="danger-exported" className="text-sm text-ink">
                  I confirm I have a copy, or I don&apos;t want one
                </label>
              </div>
            </div>

            <Input
              id="danger-password"
              label="2. Confirm your password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <div>
              <label
                htmlFor="danger-phrase"
                className="block text-sm font-medium text-ink mb-1.5"
              >
                3. Type <code className="font-mono">{PROFILE_DELETE_CONFIRMATION}</code>
              </label>
              <Input
                id="danger-phrase"
                type="text"
                value={phrase}
                onChange={(e) => setPhrase(e.target.value)}
                className="font-mono"
                placeholder={PROFILE_DELETE_CONFIRMATION}
              />
            </div>

            {error && (
              <p role="alert" className="text-sm text-status-attention" data-t0="">
                {error}
              </p>
            )}

            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" data-alert-cancel="" onClick={closeDialog}>
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
        </AlertDialog>
      </CardContent>
    </Card>
  );
}
