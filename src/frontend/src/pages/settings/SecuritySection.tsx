/**
 * Profile & security section (UI-PG-SETTINGS): the landing section of /settings.
 *
 * It renders the three cards as they are. Their restyle belongs to UI-PG-SECURITY.
 */

import { RecoveryCodeCard } from '@/components/settings/RecoveryCodeCard';
import { BackupCard } from '@/components/settings/BackupCard';
import { DangerZone } from '@/components/settings/DangerZone';

export function SecuritySection() {
  return (
    <div className="space-y-6">
      {/* Recovery code (SEC-RECOV-002) — grouped with backup because both
          answer "what happens if I lose access", and both must be done while
          the user can still sign in. */}
      <RecoveryCodeCard />

      {/* Backup & restore (BKUP-UX-001) — sits directly above the danger
          zone, since taking a backup is the step before deleting anything. */}
      <BackupCard />

      {/* Irreversible profile deletion (PROF-DEL-001) */}
      <DangerZone />
    </div>
  );
}
