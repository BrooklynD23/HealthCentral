/**
 * UX-001 Phase 5: Correlation Contract Tests
 *
 * Tests the temporal overlap rule as applied to the medication-overlay
 * direction ("which medications were active when this result was collected"):
 *   med.started_at <= obs.collected_at AND
 *   (med.ended_at IS NULL OR med.ended_at >= obs.collected_at)
 *
 * MED-CORR-002 removed the inverse (`findObservationsDuringMedication`) and its
 * cases here: that direction is now the backend's, covered by the
 * HC-MCORR-001..010 endpoint tests and FE-MCORR-001..004.
 */

import { describe, it, expect } from 'vitest';
import { findActiveMedications } from '@/utils/correlation';
import type { Medication, Observation } from '@/services/types';

// Factory helpers — only include fields used by the correlation logic
function makeObservation(overrides: Partial<Observation> = {}): Observation {
  return {
    id: 'obs-1',
    profile_id: 'profile-1',
    doc_id: 'doc-1',
    analyte_canonical: 'hemoglobin',
    analyte_raw: 'Hemoglobin',
    value: 14.2,
    value_text: null,
    unit: 'g/dL',
    ref_low: 12.0,
    ref_high: 17.5,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2025-06-15T00:00:00',
    user_verified: true,
    extraction_confidence: 0.95,
    source_page: null,
    source_bbox_json: null,
    ...overrides,
  };
}

function makeMedication(overrides: Partial<Medication> = {}): Medication {
  return {
    id: 'med-1',
    profile_id: 'profile-1',
    name: 'Metformin',
    generic_name: null,
    dosage_amount: 500,
    dosage_unit: 'mg',
    dosage_form: 'tablet',
    frequency: 'twice_daily',
    instructions: null,
    is_active: true,
    reminder_enabled: false,
    started_at: '2025-01-01T00:00:00',
    ended_at: null,
    created_at: '2025-01-01T00:00:00',
    updated_at: '2025-01-01T00:00:00',
    schedules: [],
    ...overrides,
  };
}

describe('Correlation Contract (UX-001)', () => {
  describe('findActiveMedications', () => {
    it('returns medications active at observation date (ongoing, no end date)', () => {
      const obs = makeObservation({ collected_at: '2025-06-15T00:00:00' });
      const meds = [
        makeMedication({
          id: 'med-1',
          name: 'Metformin',
          started_at: '2025-01-01T00:00:00',
          ended_at: null,
        }),
      ];

      const result = findActiveMedications(obs, meds);

      expect(result).toHaveLength(1);
      expect(result[0].medicationId).toBe('med-1');
      expect(result[0].medicationName).toBe('Metformin');
      expect(result[0].dosageLabel).toBe('500mg');
    });

    it('excludes medications that ended before observation date', () => {
      const obs = makeObservation({ collected_at: '2025-06-15T00:00:00' });
      const meds = [
        makeMedication({
          id: 'med-1',
          started_at: '2025-01-01T00:00:00',
          ended_at: '2025-03-01T00:00:00', // ended before June
        }),
      ];

      const result = findActiveMedications(obs, meds);

      expect(result).toHaveLength(0);
    });

    it('excludes medications that started after observation date', () => {
      const obs = makeObservation({ collected_at: '2025-06-15T00:00:00' });
      const meds = [
        makeMedication({
          id: 'med-1',
          started_at: '2025-09-01T00:00:00', // started after June
          ended_at: null,
        }),
      ];

      const result = findActiveMedications(obs, meds);

      expect(result).toHaveLength(0);
    });

    it('returns empty array when observation has no collected_at date', () => {
      const obs = makeObservation({ collected_at: null });
      const meds = [makeMedication()];

      const result = findActiveMedications(obs, meds);

      expect(result).toHaveLength(0);
    });
  });

});
