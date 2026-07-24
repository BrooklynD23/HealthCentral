/**
 * FHIR R4 Export Service Contract Tests (HC-M22)
 *
 * Verifies the FHIR export service functions call the expected backend
 * routes with the expected payloads and params. Mirrors
 * VisitPrepService.test.tsx.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '@/services/api';
import { generateFhirExport, downloadFhirExport } from '@/services/export';
import type { FhirExportRequest, FhirExportResponse } from '@/services/export';

vi.mock('@/services/api', () => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
}));

const exportResponse: FhirExportResponse = {
  export_id: 'abc12345-1111-4222-8333-444455556666',
  profile_id: 'p1',
  generated_at: '2026-07-17T10:00:00Z',
  resource_counts: { Patient: 1, Observation: 3, MedicationStatement: 2 },
  redaction_count: 0,
};

describe('generateFhirExport', () => {
  beforeEach(() => {
    vi.mocked(api.apiPost).mockReset();
    vi.mocked(api.apiPost).mockResolvedValue(exportResponse);
  });

  it('POSTs /export/fhir with the full request payload', async () => {
    const request: FhirExportRequest = {
      confirm: true,
      include_documents: true,
      include_medications: true,
      include_observations: true,
      include_conditions: false,
      include_care_plan: true,
      include_encounters: false,
      include_reports: true,
    };

    const result = await generateFhirExport(request);

    expect(api.apiPost).toHaveBeenCalledWith('/export/fhir', request);
    expect(result.export_id).toBe(exportResponse.export_id);
    expect(result.resource_counts.Observation).toBe(3);
  });

  it('always carries an explicit confirm flag in the payload', async () => {
    await generateFhirExport({ confirm: true });

    const payload = vi.mocked(api.apiPost).mock.calls[0][1] as FhirExportRequest;
    expect(payload.confirm).toBe(true);
  });
});

describe('downloadFhirExport', () => {
  beforeEach(() => {
    vi.mocked(api.apiGetRaw).mockReset();
    vi.mocked(api.apiGetRaw).mockResolvedValue({
      headers: { get: () => 'application/fhir+json' },
      blob: async () => new Blob(['{"resourceType":"Bundle"}'], { type: 'application/fhir+json' }),
    } as unknown as Response);
  });

  it('GETs the export download route and returns a .json extension', async () => {
    const { extension, contentType } = await downloadFhirExport(exportResponse.export_id);

    expect(api.apiGetRaw).toHaveBeenCalledWith(
      `/export/fhir/${exportResponse.export_id}/download`
    );
    expect(extension).toBe('.json');
    expect(contentType).toBe('application/fhir+json');
  });
});
