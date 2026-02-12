/**
 * Medication–Observation Correlation Utility (UX-001)
 *
 * Heuristic: A medication is "active during" an observation when:
 *   med.started_at <= obs.collected_at AND
 *   (med.ended_at IS NULL OR med.ended_at >= obs.collected_at)
 *
 * This is a frontend-only temporal overlay — no backend changes needed.
 */

import type {
  Medication,
  Observation,
  MedicationOverlayPeriod,
  CorrelationContext,
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

/**
 * Build correlation context for an observation.
 */
export function buildCorrelationContext(
  observation: Observation,
  medications: Medication[]
): CorrelationContext {
  return {
    observation,
    activeMedications: findActiveMedications(observation, medications),
  };
}

/**
 * Find observations that fall within a medication's active period.
 */
export function findObservationsDuringMedication(
  medication: Medication,
  observations: Observation[]
): Observation[] {
  const startDate = new Date(medication.started_at).getTime();
  const endDate = medication.ended_at
    ? new Date(medication.ended_at).getTime()
    : null;

  return observations.filter((obs) => {
    if (!obs.collected_at) return false;
    const obsDate = new Date(obs.collected_at).getTime();
    if (obsDate < startDate) return false;
    if (endDate !== null && obsDate > endDate) return false;
    return true;
  });
}
