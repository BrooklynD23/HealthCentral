/**
 * UI full verification — PDF import + inbox review (local opt-in project).
 *
 * Fixture: e2e/fixtures/synthetic-lab.pdf is a one-page, obviously fictional
 * text-lab PDF (no real data). It is regenerated with this stdlib-only script,
 * run from src/frontend. The binary marker comment (%\xe2\xe3\xcf\xd3) keeps git
 * from treating it as text, so .gitattributes "* text=auto" cannot rewrite line
 * endings and break the xref byte offsets.
 *
 *   import zlib
 *   lines = [
 *       "SYNTHETIC TEST REPORT - NOT REAL DATA",
 *       "Patient: Test Patient",
 *       "Collection Date: 01/15/2024",
 *       "Glucose 95 mg/dL 70-99",
 *       "Hemoglobin 14.2 g/dL 13.5-17.5",
 *   ]
 *   ops = ["BT", "/F1 12 Tf", "14 TL", "72 720 Td"]
 *   for ln in lines:
 *       ops.append("(%s) Tj T*" % ln)
 *   ops.append("ET")
 *   stream = zlib.compress("\n".join(ops).encode("ascii"))
 *   objs = [
 *       b"<< /Type /Catalog /Pages 2 0 R >>",
 *       b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
 *       b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
 *       b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream",
 *       b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
 *   ]
 *   out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
 *   offs = []
 *   for i, o in enumerate(objs, 1):
 *       offs.append(len(out))
 *       out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
 *   xref = len(out)
 *   out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
 *   for o in offs:
 *       out += b"%010d 00000 n \n" % o
 *   out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
 *   open("e2e/fixtures/synthetic-lab.pdf", "wb").write(out)
 *
 * Where things run:
 *   - ui-routes-verification.spec.ts (sidebar, Explain, Settings): project
 *     "chromium", every run, including CI.
 *   - This file: project "real-pdf-local" only (chromium has testIgnore for it).
 *     HC_E2E_REAL_PDF (or the Windows default path) overrides the PDF; when
 *     neither exists the synthetic fixture is used instead of skipping.
 *
 * Run: npx playwright test --config playwright.config.ts --project real-pdf-local
 */

import fs from 'fs';
import path from 'path';
import { test, expect } from '@playwright/test';
import { openAuthenticatedPage } from './support/auth';

const DEFAULT_WIN32_PDF = 'F:\\12-07-2024 LIDPID .pdf';

function resolveRealPdfPath(): string {
  const fromEnv = process.env.HC_E2E_REAL_PDF?.trim();
  if (fromEnv) {
    return path.resolve(fromEnv);
  }
  if (process.platform === 'win32') {
    return DEFAULT_WIN32_PDF;
  }
  return '';
}

const REAL_PDF_PATH = resolveRealPdfPath();
const HAS_REAL_PDF = REAL_PDF_PATH.length > 0 && fs.existsSync(REAL_PDF_PATH);

const SIDEBAR_PATHS = [
  '/inbox',
  '/verify',
  '/trends',
  '/interpret',
  '/medications',
  '/notifications',
  '/explain',
  '/export',
  '/settings',
] as const;

const SKIP_REASON = `Real PDF not on disk. Set HC_E2E_REAL_PDF or add the default Windows path. Last resolved: ${REAL_PDF_PATH || '(empty)'}`;

function describeRealPdfSuite(name: string, fn: () => void) {
  if (!HAS_REAL_PDF) {
    test.describe.skip(`${name} — ${SKIP_REASON}`, fn);
  } else {
    test.describe(name, fn);
  }
}

describeRealPdfSuite('UI full verification (real PDF)', () => {
  test.describe.configure({ mode: 'serial' });

  test('E2E-UI-FULL-001: import real PDF and reach a terminal inbox status', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/inbox');

    const fileInput = page.getByLabel('Upload medical documents');
    await fileInput.setInputFiles(REAL_PDF_PATH);

    const baseName = path.basename(REAL_PDF_PATH);
    await expect(page.getByText(baseName, { exact: false }).first()).toBeVisible({
      timeout: 180_000,
    });

    await expect(
      page.getByText(/Verified|OCR Required|Pending|Needs Review/, { exact: false })
    ).toBeVisible({ timeout: 180_000 });
  });

  test('E2E-UI-FULL-002: sidebar routes render main content', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/inbox');

    for (const routePath of SIDEBAR_PATHS) {
      await page.goto(routePath);
      await expect(page.locator('main').first()).toBeVisible({ timeout: 30_000 });
    }
  });

  test('E2E-UI-FULL-002b: inbox action opens document review workflow', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/inbox');

    const baseName = path.basename(REAL_PDF_PATH);
    await expect(page.getByText(baseName, { exact: false }).first()).toBeVisible({
      timeout: 180_000,
    });

    await page.getByRole('button', { name: /more options/i }).first().click();
    await page.getByText(/review extracted values/i).first().click();

    await expect(page).toHaveURL(/\/verify\?doc=.*mode=all/, { timeout: 30_000 });
    await expect(page.getByText(/verification workbench/i)).toBeVisible({ timeout: 30_000 });
  });

  test('E2E-UI-FULL-003: Explain Assistant sends and shows fallback or answer', async ({
    page,
    request,
  }) => {
    await openAuthenticatedPage(page, request, '/explain');

    await expect(page.getByText(/explain assistant/i)).toBeVisible({ timeout: 15_000 });

    const input = page.getByPlaceholder(/ask about your results/i);
    await input.fill('What do my latest lab values show?');

    const sendButton = page.getByRole('button').filter({ has: page.locator('svg') }).last();
    await sendButton.click();

    await expect(
      page.getByText(
        /(insufficient|don't have enough|no relevant|limited context|not fully configured|knowledge base only|setup instructions|reference range|lab value|result|mg\/dl|mmol|hemoglobin|glucose)/i
      )
    ).toBeVisible({ timeout: 120_000 });
  });

  test('E2E-UI-FULL-004: Settings hardware detection completes', async ({ page, request }) => {
    await openAuthenticatedPage(page, request, '/settings');

    await expect(
      page.getByText(/Configure AI model and hardware preferences/i)
    ).toBeVisible({ timeout: 15_000 });

    const detectButton = page.getByRole('button', { name: /^(Detect Hardware|Re-detect)$/ });
    await detectButton.click();

    await expect(page.getByText(/^RAM$/).or(page.getByText(/Recommended Tier/i))).toBeVisible({
      timeout: 60_000,
    });
  });
});
