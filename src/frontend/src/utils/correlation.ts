/**
 * Medication overlay for a selected observation (UX-001).
 *
 * The temporal overlap rule is:
 *   med.started_at <= obs.collected_at AND
 *   (med.ended_at IS NULL OR med.ended_at >= obs.collected_at)
 *
 * MED-CORR-002 note on where this rule lives. The *observation-listing*
 * direction — "which results fall inside this medication's window" — is owned
 * by the backend (`GET /medications/{id}/correlations`, MED-CORR-001), and
 * MedicationDetail consumes it directly. That is the direction where a second
 * implementation could drift on something that matters: the endpoint returns
 * verified observations only, and the removed frontend copy did not.
 *
 * What remains here is the *inverse* projection — "which medications were
 * active when this result was collected" — which TrendsDashboard needs for the
 * chart overlay and which no endpoint serves. It filters medications, not
 * observations, so the verified-only rule has nothing to apply to. If a
 * `GET /observations/{id}/medications` endpoint ever exists, this should go the
 * same way `findObservationsDuringMedication` did.
 */

import type {
  Medication,
  Observation,
  MedicationOverlayPeriod,
} from '@/services/types';

/**
 * Convert a Medication to a MedicationOverlayPeriod for display.
 */
function toOverlayPeriod(med: Medication): MedicationOverlayPeriod {
  const dosageLabel =
    med.dosage_amount != null && med.dosage_unit
      ? `${med.dosage_amount}${med.dosage_unit}`
      : null;

  return {
    medicationId: med.id,
    medicationName: med.name,
    startedAt: med.started_at,
    endedAt: med.ended_at,
    dosageLabel,
  };
}

/**
 * Find medications that were active at the time an observation was collected.
 *
 * Returns an empty array if the observation has no collected_at date.
 */
export function findActiveMedications(
  observation: Observation,
  medications: Medication[]
): MedicationOverlayPeriod[] {
  if (!observation.collected_at) return [];

  const obsDate = new Date(observation.collected_at).getTime();

  return medications
    .filter((med) => {
      const startDate = new Date(med.started_at).getTime();
      if (startDate > obsDate) return false;

      if (med.ended_at) {
        const endDate = new Date(med.ended_at).getTime();
        if (endDate < obsDate) return false;
      }

      return true;
    })
    .map(toOverlayPeriod);
}
