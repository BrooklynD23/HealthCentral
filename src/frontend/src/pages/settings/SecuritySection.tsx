/**
 * Profile & security section (UI-PG-SETTINGS): the landing section of /settings.
 *
 * UI-PG-SECURITY: the three cards sit on the ui primitives, and the restore and delete
 * confirmations are AlertDialogs (BackupCard, DangerZone). The warnings, the recovery code and the
 * error texts carry `data-t0`; none of them animates.
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
