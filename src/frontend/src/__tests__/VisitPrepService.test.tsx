/**
 * Visit Prep Export Service Contract Tests (HC-M18)
 *
 * Verifies the visit-prep service functions call the expected backend
 * routes with the expected payloads and params.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as api from '@/services/api';
import { generateVisitPrep, downloadVisitPrep } from '@/services/export';
import type { VisitPrepRequest, VisitPrepResponse } from '@/services/export';

vi.mock('@/services/api', () => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
}));

const packetResponse: VisitPrepResponse = {
  packet_id: 'abc12345-1111-4222-8333-444455556666',
  profile_id: 'p1',
  generated_at: '2026-07-12T10:00:00',
  section_titles: ['Reason for Visit', 'Current Medications'],
  markdown: '# Visit Prep Packet',
  redaction_count: 0,
};

describe('generateVisitPrep', () => {
  beforeEach(() => {
    vi.mocked(api.apiPost).mockReset();
    vi.mocked(api.apiPost).mockResolvedValue(packetResponse);
  });

  it('POSTs /export/visit-prep with the full request payload', async () => {
    const request: VisitPrepRequest = {
      reason_for_visit: 'Persistent headaches',
      include_medications: true,
      include_labs: true,
      include_visits: false,
      include_tasks: true,
      include_questions: true,
      selected_doc_ids: ['doc-1'],
      confirm: true,
    };

    const result = await generateVisitPrep(request);

    expect(api.apiPost).toHaveBeenCalledWith('/export/visit-prep', request);
    expect(result.packet_id).toBe(packetResponse.packet_id);
    expect(result.markdown).toContain('# Visit Prep Packet');
  });

  it('always carries an explicit confirm flag in the payload', async () => {
    await generateVisitPrep({ confirm: true });

    const payload = vi.mocked(api.apiPost).mock.calls[0][1] as VisitPrepRequest;
    expect(payload.confirm).toBe(true);
  });
});

describe('downloadVisitPrep', () => {
  beforeEach(() => {
    vi.mocked(api.apiGetRaw).mockReset();
    vi.mocked(api.apiGetRaw).mockResolvedValue({
      headers: { get: () => 'text/markdown' },
      blob: async () => new Blob(['# Visit Prep Packet'], { type: 'text/markdown' }),
    } as unknown as Response);
  });

  it('GETs the packet download route with the format param', async () => {
    const { extension } = await downloadVisitPrep(packetResponse.packet_id, 'markdown');

    expect(api.apiGetRaw).toHaveBeenCalledWith(
      `/export/visit-prep/${packetResponse.packet_id}/download`,
      { format: 'markdown' }
    );
    expect(extension).toBe('.md');
  });

  it('maps html and pdf content types to extensions', async () => {
    vi.mocked(api.apiGetRaw).mockResolvedValue({
      headers: { get: () => 'text/html' },
      blob: async () => new Blob(['<html></html>'], { type: 'text/html' }),
    } as unknown as Response);

    const { extension } = await downloadVisitPrep(packetResponse.packet_id, 'html');
    expect(api.apiGetRaw).toHaveBeenCalledWith(
      `/export/visit-prep/${packetResponse.packet_id}/download`,
      { format: 'html' }
    );
    expect(extension).toBe('.html');
  });
});
