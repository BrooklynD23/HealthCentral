/**
 * DEMO-E2E-REAL: the investor demo path against the REAL backend, in the CI `chromium` project.
 *
 * Four steps had no real-backend coverage in CI: /verify, /medications (create + dose + detail), /export (visit-prep)
 * and /results (a trend). ui-full-verification.spec.ts is excluded from chromium and ui-export.spec.ts is mock-only.
 * Interpretation success is out of scope: it needs a local LLM.
 *
 * Isolation: every test resets the shared E2E profile BEFORE it seeds (so a CI retry never meets the first attempt's
 * rows) and AFTER it (so later specs find the vault as global-setup left it). Data is synthetic. No sleeps: every wait
 * is a web-first assertion or an expect.poll on the API.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { expect, test, type APIRequestContext } from '@playwright/test';
import {
  E2E_API_URL,
  ensureE2EProfile,
  openAuthenticatedPage,
  resetE2EProfile,
} from './support/auth';

const SYNTHETIC_LAB_PDF = path.join(path.dirname(fileURLToPath(import.meta.url)), 'fixtures', 'synthetic-lab.pdf');
const CSV_HEADER = 'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n';
// Dates and values are fictional. 118 is flagged H against 70-99, so it is an abnormal verified lab for the packet.
const GLUCOSE_CSV =
  CSV_HEADER + '2026-01-10,Glucose,92,mg/dL,70,99,\n' + '2026-04-10,Glucose,118,mg/dL,70,99,H\n';

interface Observation {
  id: string;
  analyte_raw: string;
  analyte_canonical: string;
  user_verified: boolean;
}

type Headers = { Authorization: string };

async function freshVault(request: APIRequestContext): Promise<Headers> {
  const { access_token: token } = await ensureE2EProfile(request);
  await resetE2EProfile(request, token);
  // The strict safety flag hides unchecked points on /results; an earlier spec may have left it on.
  const flag = await request.patch(`${E2E_API_URL}/assistant/safety-mode`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { strict_safety_mode: false },
  });
  expect(flag.ok(), await flag.text()).toBeTruthy();
  return { Authorization: `Bearer ${token}` };
}

async function importFile(
  request: APIRequestContext,
  headers: Headers,
  name: string,
  mimeType: string,
  buffer: Buffer
): Promise<void> {
  const imported = await request.post(`${E2E_API_URL}/documents/import`, {
    headers,
    multipart: { file: { name, mimeType, buffer } },
  });
  expect(imported.ok(), `import ${name}: ${imported.status()} ${await imported.text()}`).toBeTruthy();
}

async function listObservations(request: APIRequestContext, headers: Headers): Promise<Observation[]> {
  const response = await request.get(`${E2E_API_URL}/observations/`, { headers });
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as Observation[];
}

async function verifyAll(request: APIRequestContext, headers: Headers): Promise<void> {
  for (const observation of await listObservations(request, headers)) {
    const verified = await request.post(`${E2E_API_URL}/observations/${observation.id}/verify`, { headers, data: {} });
    expect(verified.ok(), await verified.text()).toBeTruthy();
  }
}

test.describe('DEMO-E2E-REAL demo path on the real backend', () => {
  test.beforeEach(async ({ request }) => {
    await freshVault(request);
  });

  test.afterEach(async ({ request }) => {
    const { access_token: token } = await ensureE2EProfile(request);
    await resetE2EProfile(request, token);
  });

  test('DEMO-E2E-REAL-001: /verify checks one extracted value from an uploaded document and it stays checked', async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);
    const headers = await freshVault(request);
    await importFile(request, headers, 'synthetic-lab.pdf', 'application/pdf', fs.readFileSync(SYNTHETIC_LAB_PDF));

    // Extraction ran inside the import call; poll anyway so a slower box fails on a clear message, not a missing row.
    await expect
      .poll(async () => (await listObservations(request, headers)).length, { timeout: 60_000 })
      .toBeGreaterThanOrEqual(1);
    const glucose = (await listObservations(request, headers)).find((o) => /glucose/i.test(o.analyte_raw));
    expect(glucose, 'the synthetic report yields a Glucose value').toBeTruthy();
    expect(glucose!.user_verified, 'the extracted value starts unchecked').toBe(false);

    await openAuthenticatedPage(page, request, '/verify');
    // Scoped to this row, so another value's button or chip cannot satisfy the assertions.
    const row = page.locator(`#observation-row-${glucose!.id}`);
    await expect(row).toBeVisible({ timeout: 30_000 });
    await expect(row).toContainText('Not yet checked');
    const verifyPosted = page.waitForResponse(
      (response) => response.request().method() === 'POST' && /\/observations\/[^/]+\/verify$/.test(new URL(response.url()).pathname)
    );
    await row.getByRole('button', { name: 'Verify observation' }).click();
    expect((await verifyPosted).ok()).toBeTruthy();
    await expect(row).toContainText('Checked by you', { timeout: 30_000 });

    // The server agrees, not just the screen.
    await expect
      .poll(async () => {
        const saved = (await listObservations(request, headers)).find((o) => o.id === glucose!.id);
        return saved?.user_verified;
      })
      .toBe(true);

    // A reload: the default list holds only unchecked values, so the checked row is gone (it was only held on screen).
    await page.reload();
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator(`#observation-row-${glucose!.id}`)).toHaveCount(0);
  });

  test('DEMO-E2E-REAL-002: /medications creates a medication, logs one dose, and the detail page shows it', async ({
    page,
    request,
  }) => {
    const medName = 'Demo Testamine';
    await openAuthenticatedPage(page, request, '/medications');

    await page.getByRole('button', { name: 'Add Medication' }).first().click();
    await page.locator('#med-name').fill(medName);
    await page.locator('#med-amount').fill('25');
    await page.locator('#med-frequency').selectOption('once_daily');
    const created = page.waitForResponse(
      (response) => response.request().method() === 'POST' && /\/medications\/?$/.test(new URL(response.url()).pathname)
    );
    await page.getByRole('button', { name: 'Add Medication' }).last().click();
    expect((await created).status()).toBe(201);

    const card = page.locator('a[href^="/medications/"]').filter({ hasText: medName });
    await expect(card).toHaveCount(1, { timeout: 15_000 });

    // One dose, through the card's quick-log dialog.
    await page.getByRole('button', { name: 'Log', exact: true }).first().click();
    const dialog = page.getByRole('dialog', { name: 'Log Dose' });
    await expect(dialog).toBeVisible();
    await dialog.getByLabel('Notes (optional)').fill('demo dose');
    const logged = page.waitForResponse(
      (response) => response.request().method() === 'POST' && /\/medications\/[^/]+\/doses\/?$/.test(new URL(response.url()).pathname)
    );
    await dialog.getByRole('button', { name: 'Log as Taken' }).click();
    expect((await logged).ok()).toBeTruthy();
    await expect(dialog).toHaveCount(0);

    // Detail page, reached by the link.
    await card.click();
    await expect(page).toHaveURL(/\/medications\/[^/]+$/);
    await expect(page.getByRole('heading', { name: medName, level: 1 })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText('Dose History')).toBeVisible();
    await expect(page.getByText('demo dose')).toBeVisible({ timeout: 15_000 });
    // Scoped to the dose's own row: the adherence panel also has a "Taken" label.
    await expect(
      page.getByText('demo dose').locator('xpath=ancestor::div[contains(@class,"justify-between")][1]').getByText('Taken', { exact: true })
    ).toBeVisible();
    await expect(page.getByText('No doses logged yet')).toHaveCount(0);
  });

  test('DEMO-E2E-REAL-003: /export visit-prep has its sections and no literal None', async ({ page, request }) => {
    const headers = await freshVault(request);
    const medName = 'Demo Exportamine';
    const med = await request.post(`${E2E_API_URL}/medications/`, {
      headers,
      data: { name: medName, dosage_amount: 10, dosage_unit: 'mg', frequency: 'once_daily' },
    });
    expect(med.ok(), await med.text()).toBeTruthy();
    await importFile(request, headers, 'demo-export-glucose.csv', 'text/csv', Buffer.from(GLUCOSE_CSV));
    await verifyAll(request, headers);

    // The route itself, with the markdown the patient would download.
    const packetResponse = await request.post(`${E2E_API_URL}/export/visit-prep`, {
      headers,
      data: { reason_for_visit: 'Routine follow-up', confirm: true },
    });
    expect(packetResponse.ok(), await packetResponse.text()).toBeTruthy();
    const packet = (await packetResponse.json()) as { section_titles: string[]; markdown: string };
    expect(packet.section_titles).toEqual(
      expect.arrayContaining([
        'Reason for Visit',
        'Current Medications',
        'Recent Abnormal Lab Results (verified)',
        'Recent Visits and Diagnoses (verified)',
        'Open Follow-up Items',
        'Questions for Your Provider',
      ])
    );
    expect(packet.markdown).toContain(medName);
    expect(packet.markdown).toMatch(/glucose/i);
    // "None recorded." is the packet's honest wording for an empty section; any other "None" is a Python None leaking.
    const leaked = packet.markdown.replace(/None recorded\./g, '');
    expect(leaked, 'no literal None in the packet').not.toMatch(/\bNone\b/);
    expect(leaked).not.toMatch(/\b(null|undefined)\b/);

    // The page: confirm, generate, and the ready line names the sections.
    await openAuthenticatedPage(page, request, '/export');
    await page.getByLabel(/Reason for visit/i).fill('Routine follow-up');
    await page.getByLabel(/I understand this creates an exportable file/i).first().check();
    await page.getByRole('button', { name: 'Generate Packet' }).click();
    const ready = page.getByText('Packet ready');
    await expect(ready).toBeVisible({ timeout: 30_000 });
    const sections = page.getByText(/^Sections:/);
    await expect(sections).toContainText('Current Medications');
    await expect(sections).toContainText('Recent Abnormal Lab Results (verified)');
    await expect(sections).not.toContainText(/\bNone\b/);
    await expect(page.getByText('Failed to generate the packet')).toHaveCount(0);
  });

  test('DEMO-E2E-REAL-004: /results shows a trend for one analyte with two observations', async ({ page, request }) => {
    const headers = await freshVault(request);
    await importFile(request, headers, 'demo-trend-glucose.csv', 'text/csv', Buffer.from(GLUCOSE_CSV));
    await verifyAll(request, headers);

    const trend = await request.get(`${E2E_API_URL}/observations/trends/glucose`, { headers });
    expect(trend.ok(), await trend.text()).toBeTruthy();
    expect(((await trend.json()) as { data_points: unknown[] }).data_points).toHaveLength(2);

    await openAuthenticatedPage(page, request, '/results?analyte=glucose');
    await expect(page.getByText(/GLUCOSE has increased by [\d.]+% over 2 dated measurements\./)).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/Latest value: 118/)).toBeVisible();
    await expect(page.locator('svg[role="slider"]')).toBeVisible();
  });
});
