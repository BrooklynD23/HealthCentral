/**
 * KEPT-FLAG-DISAGREES (frontend half): the Results page says, under "Latest value", that the flag printed on the
 * report and the printed range disagree, when the trend route says the latest point's own report does.
 * Owner answer "Say they disagree (Recommended)", sentence verbatim. Plan: docs/plans/2026-11-06-owner-answers-rows-plan.md.
 *
 * HC-KFD-010 the sentence shows under "Latest value" when the latest point has flag_range_disagree === true
 * HC-KFD-011 it is absent when the field is false or missing, or only an earlier point has it
 * HC-KFD-012 the badges and the ribbon's own words are unchanged beside it
 *
 * Only the network is mocked; the page and the ribbon are the real ones. A new file, so BADGE-STYLE-MAP's edits to
 * ui-results.test.tsx stay disjoint.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import type { TrendData, TrendPoint } from '@/services/types';
import { ResultsPage } from '@/pages/ResultsPage';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public statusText: string,
      message: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  },
}));

const SENTENCE =
  'The flag printed on your report and the printed range disagree for this value. Ask your clinician or the lab which applies.';
const CONFLICT_WORDS = "The report's flag and this chart's range disagree";

const OBSERVATIONS = [
  {
    id: 'o-hgb',
    profile_id: 'profile-123',
    doc_id: 'doc-1',
    analyte_canonical: 'hemoglobin',
    analyte_raw: 'Hemoglobin',
    value: 14.2,
    value_text: null,
    unit: 'g/dL',
    ref_low: 12,
    ref_high: 17.5,
    ref_range_text: null,
    flag: null,
    is_abnormal: false,
    collected_at: '2026-04-10T00:00:00',
    user_verified: true,
    extraction_confidence: 0.9,
    source_page: 1,
    source_bbox_json: null,
  },
];

function point(date: string, value: number, extra: Partial<TrendPoint> = {}): TrendPoint {
  return {
    date,
    value,
    unit: 'g/dL',
    is_abnormal: false,
    flag: null,
    doc_id: 'doc-1',
    extraction_confidence: null,
    user_verified: true,
    ...extra,
  };
}

function trend(points: TrendPoint[], over: Partial<TrendData> = {}): TrendData {
  return {
    analyte_canonical: 'hemoglobin',
    analyte_display_name: 'HEMOGLOBIN',
    unit: 'g/dL',
    ref_low: 12,
    ref_high: 17.5,
    data_points: points,
    summary: 'HEMOGLOBIN summary.',
    ...over,
  };
}

async function open(data: TrendData) {
  vi.mocked(api.apiGet).mockImplementation(async (url: string) => {
    if (url === '/observations/') return OBSERVATIONS;
    if (/^\/observations\/trends\//.test(url)) return data;
    if (url === '/medications/') return [];
    if (url === '/settings/model/external-api') {
      return { use_external_api: false, provider: '', model: '', api_key_configured: false };
    }
    if (url.includes('/interpretation')) throw new api.ApiError(404, 'Not Found', 'not found');
    if (url === '/assistant/safety-mode') return { strict_safety_mode: false };
    throw new Error(`unmocked ${url}`);
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/results']}>
        <Routes>
          <Route path="/results" element={<ResultsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
  await screen.findByRole('slider', {}, { timeout: 8000 });
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('HC-KFD-010 the sentence under Latest value', () => {
  it('HC-KFD-010: shows the exact sentence, after the Latest value line, when the latest point disagrees', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2, { flag: 'L', is_abnormal: true, flag_range_disagree: true })]));
    const latest = await screen.findByText(/Latest value: 14.2/);
    const sentence = await screen.findByText(SENTENCE);
    expect(screen.getAllByText(SENTENCE)).toHaveLength(1);
    expect(latest.compareDocumentPosition(sentence) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // in the same block as the Latest value line, and before the trend summary
    const block = latest.closest('div.bg-surface-muted');
    expect(block).not.toBeNull();
    expect(block?.contains(sentence)).toBe(true);
    const summary = await screen.findByText('HEMOGLOBIN summary.');
    expect(sentence.compareDocumentPosition(summary) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('HC-KFD-010: shows it for a printed normal word against a value outside the band too', async () => {
    await open(trend([point('2026-04-10T00:00:00', 30, { flag: 'N', is_abnormal: false, flag_range_disagree: true })]));
    expect(await screen.findByText(SENTENCE)).toBeInTheDocument();
  });

  it('HC-KFD-010: reads the latest point, so a disagreeing latest point shows it after an agreeing earlier one', async () => {
    await open(
      trend([
        point('2026-01-10T00:00:00', 13.5),
        point('2026-04-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true, flag_range_disagree: true }),
      ])
    );
    expect(await screen.findByText(SENTENCE)).toBeInTheDocument();
  });
});

describe('HC-KFD-011 the sentence is absent', () => {
  it('HC-KFD-011: absent when the field is false', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true, flag_range_disagree: false })]));
    await screen.findByText(/Latest value: 14.2/);
    expect(screen.queryByText(SENTENCE)).toBeNull();
  });

  it('HC-KFD-011: absent when the field is missing (an older response)', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true })]));
    await screen.findByText(/Latest value: 14.2/);
    expect(screen.queryByText(SENTENCE)).toBeNull();
  });

  it('HC-KFD-011: absent when only an earlier point disagrees', async () => {
    await open(
      trend([
        point('2026-01-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true, flag_range_disagree: true }),
        point('2026-04-10T00:00:00', 14.0, { flag_range_disagree: false }),
      ])
    );
    await screen.findByText(/Latest value: 14/);
    expect(screen.queryByText(SENTENCE)).toBeNull();
  });

  it('HC-KFD-011: absent for a truthy value that is not the boolean true', async () => {
    const odd = { flag_range_disagree: 'true' } as unknown as Partial<TrendPoint>;
    await open(trend([point('2026-04-10T00:00:00', 14.2, odd)]));
    await screen.findByText(/Latest value: 14.2/);
    expect(screen.queryByText(SENTENCE)).toBeNull();
  });
});

describe('HC-KFD-012 badges and ribbon words are unchanged', () => {
  it('HC-KFD-012: a flagged value inside the band keeps "Flagged on the report" and shows the sentence', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true, flag_range_disagree: true })]));
    expect(await screen.findByText('Flagged on the report')).toBeInTheDocument();
    expect(await screen.findByText(SENTENCE)).toBeInTheDocument();
    expect(screen.queryByText('Outside Range')).toBeNull();
    expect(screen.queryByText('Normal Range')).toBeNull();
  });

  it('HC-KFD-012: a value outside the band keeps "Outside Range" alone and shows the sentence', async () => {
    await open(trend([point('2026-04-10T00:00:00', 30, { flag: 'N', is_abnormal: false, flag_range_disagree: true })]));
    expect(await screen.findByText('Outside Range')).toBeInTheDocument();
    expect(await screen.findByText(SENTENCE)).toBeInTheDocument();
    expect(screen.queryByText('Normal Range')).toBeNull();
    expect(screen.queryByText('Flagged on the report')).toBeNull();
  });

  it('HC-KFD-012: an unflagged value inside the band keeps "Normal Range", and the sentence stays off', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2)]));
    expect(await screen.findByText('Normal Range')).toBeInTheDocument();
    expect(screen.queryByText(SENTENCE)).toBeNull();
  });

  it('HC-KFD-012: the ribbon still prints its own conflict words, and they are not the new sentence', async () => {
    await open(trend([point('2026-04-10T00:00:00', 14.2, { flag: 'H', is_abnormal: true, flag_range_disagree: true })], {
      ref_low: 12,
      ref_high: 17.5,
    }));
    await screen.findByText(SENTENCE);
    expect(screen.getAllByText(CONFLICT_WORDS).length).toBeGreaterThan(0);
    expect(CONFLICT_WORDS).not.toBe(SENTENCE);
  });
});
