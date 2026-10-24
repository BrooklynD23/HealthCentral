/**
 * Typed page.route fixtures for the UI-GATES harness.
 *
 * installMockApi answers every /api/v1 request the page makes, from the
 * fixtures below. A request with no fixture is recorded in `unmocked` and
 * answered with 599, so it fails the page and the guard. Nothing reaches the
 * backend. Fixture data is typed from fe/services/types.ts (src/frontend/src/services/types.ts).
 *
 * The owner's name is never used: the person in every fixture is FIXTURE_PERSON.
 */

import type { Page, Request, Route } from '@playwright/test';
import type { Document, Profile, TrendData, TrendPoint } from '../../src/services/types';

/** UI-FIXTURE-NAME: the only person name the harness uses. */
export const FIXTURE_PERSON = 'Alex Rivera';
export const FIXTURE_PROFILE_ID = '6f1c2a7e-0b3d-4c5e-9a8f-1d2e3f4a5b6c';
export const FIXTURE_TOKEN = 'mock-token-alex-rivera';
const SESSION_TTL_SECONDS = 60 * 60;

/** Seeded lab values (UI review): glucose 92/104/118/101 against 70-99 mg/dL, LDL 142, HbA1c 6.1. */
export const SEEDED = {
  glucoseValues: [92, 104, 118, 101] as const,
  glucoseRange: { low: 70, high: 99 },
  ldl: 142,
  hba1c: 6.1,
} as const;

export const profileFixtures: Profile[] = [
  {
    id: FIXTURE_PROFILE_ID,
    display_name: FIXTURE_PERSON,
    is_locked: false,
    created_at: '2026-01-05T09:00:00Z',
    last_accessed_at: '2026-10-20T08:30:00Z',
    has_recovery_code: false,
  },
];

/** GET /pinboards/ (type Pinboard lives in services/pinboards.ts). The inbox only needs it empty. */
export const pinboardFixtures: [] = [];

export const documentFixtures: Document[] = [
  {
    id: 'doc-fixture-0001',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_report',
    source: `${FIXTURE_PERSON} lab report, March`,
    status: 'verified',
    page_count: 2,
    collection_date: '2026-03-14',
    imported_at: '2026-03-15T10:12:00Z',
    parsed_at: '2026-03-15T10:12:04Z',
    verified_at: '2026-03-16T18:02:00Z',
    extraction_confidence: 0.94,
  },
  {
    id: 'doc-fixture-0002',
    profile_id: FIXTURE_PROFILE_ID,
    doc_type: 'lab_report',
    source: `${FIXTURE_PERSON} lipid panel, August`,
    status: 'needs_review',
    page_count: 1,
    collection_date: '2026-08-02',
    imported_at: '2026-08-03T07:41:00Z',
    parsed_at: '2026-08-03T07:41:03Z',
    verified_at: null,
    extraction_confidence: 0.71,
  },
];

/** Built from a fixed list so every point carries its user_verified flag (I-13). */
function trendPoints(
  rows: Array<{ date: string; value: number; flag: string | null; abnormal: boolean; verified: boolean; docId: string }>,
  unit: string
): TrendPoint[] {
  return rows.map((row) => ({
    date: row.date,
    value: row.value,
    unit,
    is_abnormal: row.abnormal,
    flag: row.flag,
    doc_id: row.docId,
    extraction_confidence: 0.9,
    original_value: null,
    original_unit: null,
    user_verified: row.verified,
  }));
}

export const trendFixtures: Record<string, TrendData> = {
  glucose: {
    analyte_canonical: 'glucose',
    analyte_display_name: 'Glucose',
    unit: 'mg/dL',
    ref_low: SEEDED.glucoseRange.low,
    ref_high: SEEDED.glucoseRange.high,
    summary: 'Glucose readings rose across the year; the last three are above the 70-99 mg/dL range.',
    data_points: trendPoints(
      [
        { date: '2026-01-10', value: 92, flag: null, abnormal: false, verified: true, docId: 'doc-fixture-0001' },
        { date: '2026-03-14', value: 104, flag: 'H', abnormal: true, verified: true, docId: 'doc-fixture-0001' },
        { date: '2026-06-02', value: 118, flag: 'H', abnormal: true, verified: false, docId: 'doc-fixture-0002' },
        { date: '2026-08-02', value: 101, flag: 'H', abnormal: true, verified: true, docId: 'doc-fixture-0002' },
      ],
      'mg/dL'
    ),
  },
  ldl: {
    analyte_canonical: 'ldl',
    analyte_display_name: 'LDL cholesterol',
    unit: 'mg/dL',
    ref_low: null,
    ref_high: 100,
    summary: 'LDL cholesterol is above the 100 mg/dL reference.',
    data_points: trendPoints(
      [{ date: '2026-08-02', value: SEEDED.ldl, flag: 'H', abnormal: true, verified: true, docId: 'doc-fixture-0002' }],
      'mg/dL'
    ),
  },
  hba1c: {
    analyte_canonical: 'hba1c',
    analyte_display_name: 'HbA1c',
    unit: '%',
    ref_low: null,
    ref_high: 5.6,
    summary: 'HbA1c is above the 5.6 % reference.',
    data_points: trendPoints(
      [{ date: '2026-08-02', value: SEEDED.hba1c, flag: 'H', abnormal: true, verified: false, docId: 'doc-fixture-0002' }],
      '%'
    ),
  },
};

export interface MockApi {
  /** Requests answered from a fixture, as "METHOD /api/v1/path". */
  readonly served: string[];
  /** Requests with no fixture, as "METHOD /api/v1/path?query". Must stay empty. */
  readonly unmocked: string[];
}

/**
 * Routes every /api/v1 request on `page` to the fixtures. Call before the
 * first navigation. Returns the lists the guard reads.
 */
export async function installMockApi(page: Page): Promise<MockApi> {
  const served: string[] = [];
  const unmocked: string[] = [];

  await page.route(/\/api\/v1\//, async (route: Route, request: Request) => {
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '').replace(/\/+$/, '') || '/';
    const label = `${request.method()} /api/v1${path}${url.search}`;
    const json = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (request.method() === 'GET') {
      if (path === '/profiles') {
        served.push(label);
        return json(profileFixtures);
      }
      if (path === '/documents') {
        served.push(label);
        return json(documentFixtures);
      }
      if (path === '/documents/highlights/summary') {
        served.push(label);
        return json([]);
      }
      if (path === '/pinboards') {
        served.push(label);
        return json(pinboardFixtures);
      }
      const trend = /^\/observations\/trends\/([^/]+)$/.exec(path);
      if (trend && trendFixtures[trend[1]]) {
        served.push(label);
        return json(trendFixtures[trend[1]]);
      }
    }

    unmocked.push(label);
    return json({ detail: 'UI-GATES mock: no fixture for this request' }, 599);
  });

  return { served, unmocked };
}

/**
 * Seeds the zustand auth store (key `healthcentral-auth`) so ProtectedRoute
 * lets the page through without calling /profiles/login. The token is a mock.
 */
export async function seedMockSession(page: Page, name: string = FIXTURE_PERSON): Promise<void> {
  await page.addInitScript(
    ({ token, profileId, profileName, ttlSeconds }) => {
      try {
        window.localStorage.setItem(
          'healthcentral-auth',
          JSON.stringify({
            state: {
              token,
              profileId,
              profileName,
              expiresAt: Date.now() + ttlSeconds * 1000,
              isAuthenticated: true,
            },
            version: 0,
          })
        );
      } catch {
        // Storage can be blocked; the page then shows the sign-in route.
      }
    },
    { token: FIXTURE_TOKEN, profileId: FIXTURE_PROFILE_ID, profileName: name, ttlSeconds: SESSION_TTL_SECONDS }
  );
}
