/**
 * Backup & restore (BKUP-UX-001).
 *
 * `scripts/backup.py` has worked for a while, but only as a developer CLI —
 * no patient was ever going to run it, so losing a device meant losing the
 * whole record. This is the surface that makes it real.
 *
 * Restore is destructive and treated like it: password re-auth, an exact typed
 * phrase, and honest copy about what changes afterwards.
 */

import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
} from '@/components/ui';
import {
  useBackups,
  useCreateBackup,
  useVerifyBackup,
  useRestoreBackup,
  useBackupSchedule,
  useSaveBackupSchedule,
  downloadBackupArchive,
  BACKUP_RESTORE_CONFIRMATION,
  type BackupFrequency,
} from '@/services/backup';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatWhen(iso: string | null): string {
  if (!iso) return 'never';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? 'never' : date.toLocaleString();
}

export function BackupCard() {
  const { data: listing, isLoading } = useBackups();
  const { data: schedule } = useBackupSchedule();
  const createBackup = useCreateBackup();
  const verifyBackup = useVerifyBackup();
  const restoreBackup = useRestoreBackup();
  const saveSchedule = useSaveBackupSchedule();

  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [phrase, setPhrase] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // FE-03: one password/phrase pair serves the whole list, so opening restore
  // on a second backup used to inherit whatever was typed for the first — a
  // pre-filled destructive form pointing at the wrong snapshot. Switching
  // targets (or closing the form) starts clean, and the password does not sit
  // in component state past the moment it is needed.
  useEffect(() => {
    setPassword('');
    setPhrase('');
  }, [restoringId]);

  const backups = listing?.backups ?? [];
  const canRestore =
    password.length > 0 && phrase === BACKUP_RESTORE_CONFIRMATION;

  const handleCreate = async () => {
    setError(null);
    setMessage(null);
    try {
      const result = await createBackup.mutateAsync();
      setMessage(`Backed up ${result.file_count} file(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Backup failed.');
    }
  };

  const handleVerify = async (backupId: string) => {
    setError(null);
    setMessage(null);
    try {
      const result = await verifyBackup.mutateAsync(backupId);
      setMessage(
        result.valid
          ? `Checked ${result.files_checked} file(s) — all intact.`
          : `This backup is damaged: ${result.errors.length} problem(s) found.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed.');
    }
  };

  const handleDownload = async (backupId: string) => {
    setError(null);
    try {
      await downloadBackupArchive(backupId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed.');
    }
  };

  const handleRestore = async () => {
    if (!restoringId || !canRestore) return;
    setError(null);
    setMessage(null);
    try {
      const result = await restoreBackup.mutateAsync({
        backupId: restoringId,
        data: { password, confirmation_phrase: phrase },
      });
      setMessage(
        `Restored ${result.files_restored} file(s). ` +
          `${result.safety_copy_count} safety copy/copies of the replaced files were kept.`
      );
      setRestoringId(null);
      setPassword('');
      setPhrase('');
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Restore failed. Nothing was changed.'
      );
    }
  };

  const handleScheduleChange = (frequency: BackupFrequency) => {
    saveSchedule.mutate({
      enabled: frequency !== 'off',
      frequency,
      retention_days: schedule?.retention_days ?? 30,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Backup &amp; restore</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <p className="text-sm text-ink-secondary">
          A backup is a complete, restorable copy of this profile — your
          documents, results, medications and the encryption key that opens
          them. Everything stays on this device unless you download it. Keep a
          downloaded copy somewhere safe: it is the only thing that survives
          losing this machine.
        </p>

        {/* Schedule */}
        <div>
          <h3 className="text-sm font-medium mb-2">Automatic backups</h3>
          <div className="flex flex-wrap gap-2">
            {(['off', 'daily', 'weekly'] as BackupFrequency[]).map((freq) => (
              <Button
                key={freq}
                size="sm"
                variant={
                  (schedule?.frequency ?? 'off') === freq ? 'primary' : 'secondary'
                }
                onClick={() => handleScheduleChange(freq)}
                disabled={saveSchedule.isPending}
              >
                {freq === 'off' ? 'Off' : freq === 'daily' ? 'Daily' : 'Weekly'}
              </Button>
            ))}
          </div>
          <p className="text-xs text-ink-secondary mt-2">
            Last run: {formatWhen(schedule?.last_run_at ?? null)}
            {schedule?.last_result === 'skipped_locked' && (
              <>
                {' — '}
                <span className="text-status-caution">
                  a backup was due while this profile was locked. Automatic
                  backups only run while you are signed in.
                </span>
              </>
            )}
            {schedule?.last_result === 'failed' && (
              <>
                {' — '}
                <span className="text-status-attention">the last attempt failed.</span>
              </>
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleCreate} disabled={createBackup.isPending}>
            {createBackup.isPending ? 'Backing up…' : 'Back up now'}
          </Button>
        </div>

        {message && (
          <p role="status" className="text-sm text-ink-secondary">
            {message}
          </p>
        )}
        {error && (
          <p role="alert" className="text-sm text-status-attention">
            {error}
          </p>
        )}

        {/* Backup list */}
        <div>
          <h3 className="text-sm font-medium mb-2">Your backups</h3>
          {isLoading ? (
            <p className="text-sm text-ink-secondary">Loading…</p>
          ) : backups.length === 0 ? (
            <p className="text-sm text-ink-secondary">
              No backups yet. &ldquo;Back up now&rdquo; creates one.
            </p>
          ) : (
            <ul className="space-y-2">
              {backups.map((backup) => (
                <li
                  key={backup.backup_id}
                  className="rounded-md border border-black/[0.08] p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">
                        {formatWhen(backup.created_at)}
                      </p>
                      <p className="text-xs text-ink-secondary">
                        {backup.file_count} file(s) · {formatBytes(backup.size_bytes)}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleDownload(backup.backup_id)}
                      >
                        Download
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleVerify(backup.backup_id)}
                        disabled={verifyBackup.isPending}
                      >
                        Check
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setRestoringId(backup.backup_id);
                          setMessage(null);
                          setError(null);
                        }}
                      >
                        Restore…
                      </Button>
                    </div>
                  </div>

                  {restoringId === backup.backup_id && (
                    <div className="mt-3 space-y-3 rounded-md border border-status-attention/40 p-3">
                      <div>
                        <Badge className="mb-2">This replaces your current data</Badge>
                        <p className="text-xs text-ink-secondary">
                          Restoring rolls this profile back to how it was at{' '}
                          {formatWhen(backup.created_at)}. Anything added since
                          then is replaced. Your password and recovery code also
                          revert to the ones that were in use when this backup
                          was made — if you have changed either since, the old
                          ones are what will work afterwards. You will be
                          signed out when it finishes, because the keys this
                          session is holding are replaced too.
                        </p>
                      </div>

                      <div>
                        <label
                          htmlFor={`restore-password-${backup.backup_id}`}
                          className="text-sm font-medium block mb-1"
                        >
                          Confirm your password
                        </label>
                        <input
                          id={`restore-password-${backup.backup_id}`}
                          type="password"
                          autoComplete="current-password"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="w-full rounded-md border px-3 py-2 text-sm"
                        />
                      </div>

                      <div>
                        <label
                          htmlFor={`restore-phrase-${backup.backup_id}`}
                          className="text-sm font-medium block mb-1"
                        >
                          Type{' '}
                          <code className="font-mono">
                            {BACKUP_RESTORE_CONFIRMATION}
                          </code>
                        </label>
                        <input
                          id={`restore-phrase-${backup.backup_id}`}
                          type="text"
                          value={phrase}
                          onChange={(e) => setPhrase(e.target.value)}
                          placeholder={BACKUP_RESTORE_CONFIRMATION}
                          className="w-full rounded-md border px-3 py-2 text-sm font-mono"
                        />
                      </div>

                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setRestoringId(null);
                            setPassword('');
                            setPhrase('');
                          }}
                        >
                          Cancel
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={handleRestore}
                          disabled={!canRestore || restoreBackup.isPending}
                        >
                          {restoreBackup.isPending ? 'Restoring…' : 'Restore this backup'}
                        </Button>
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {listing?.backup_directory && (
          <p className="text-xs text-ink-secondary break-all">
            Stored in <code>{listing.backup_directory}</code>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
