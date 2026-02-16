# Sprint 04 Security Audit (Delta Review)

Date: 2026-02-16  
Branch: `sprint/04-data-interoperability`  
Scope: sprint files listed in review request (export, documents external import, Apple Health importer, search/export frontend updates, and related tests).

## Executive Summary

I found 4 security issues in the new sprint changes:

- 2 High severity
- 2 Medium severity

The highest-risk items are HTML injection in summary exports and an incomplete spreadsheet formula-injection guard that is still bypassable with control characters.

## Remediation Status (2026-02-16)

All 4 findings in this report have been addressed in code on `sprint/04-data-interoperability`:

- SBP-001: fixed by HTML escaping untrusted template and summary fields in export rendering.
- SBP-002: fixed by hardening formula sanitization to detect leading whitespace/control-char bypasses.
- SBP-003: fixed by `redirect_uri` allowlist validation and OAuth start-state persistence scaffolding.
- SBP-004: fixed by changing search persistence to session scope by default with explicit opt-in device persistence.

## High Findings

### SBP-001 (High): HTML injection/XSS in summary export templating

- Rule ID: `REACT-XSS-002` / output-encoding baseline
- Severity: High
- Location:
  - `src/backend/api/export.py:338`
  - `src/backend/api/export.py:339`
  - `src/backend/modules/export.py:674`
  - `src/backend/modules/export.py:677`
  - `src/backend/modules/export.py:678`
- Evidence:
  - `brand_name` and `brand_tagline` are taken from query params and inserted into HTML via f-string interpolation.
  - The values are not HTML-escaped before use in `<title>`, `<h1>`, and `<p>`.
- Impact:
  - An attacker-controlled value can inject arbitrary HTML/JS into exported HTML summaries. If that file is opened in a browser, script can execute in that context.
- Fix:
  - Escape all untrusted fields before HTML interpolation (`html.escape(...)`), including branding, section titles/content, findings, questions, and chart alt text.
  - Prefer templating with automatic escaping instead of manual f-strings.
- Mitigation:
  - Add tests that assert `<script>` and event-handler payloads are escaped in HTML output.
- False positive notes:
  - This is exploitable even if values are length-limited; length limits do not neutralize HTML/JS payloads.

### SBP-002 (High): Spreadsheet formula injection bypass remains possible

- Rule ID: spreadsheet injection hardening
- Severity: High
- Location:
  - `src/backend/modules/export.py:18`
  - `src/backend/modules/export.py:29`
  - `src/backend/api/documents.py:898`
- Evidence:
  - Sanitization only checks first character against `("=", "+", "-", "@")`.
  - User-controlled analyte values are imported and later exported; leading control characters like tab/CR are not neutralized.
- Impact:
  - Malicious imported values can still become executable formulas in CSV/Excel workflows in some spreadsheet tools, creating client-side code execution/phishing risk when exports are opened.
- Fix:
  - Expand sanitization to include leading `\t`, `\r`, and optionally leading whitespace normalization before prefix checks.
  - Apply the same hardened sanitizer consistently across CSV and XLSX cells.
- Mitigation:
  - Add regression tests for payloads like `"\t=HYPERLINK(...)"` and `"\r=cmd|..."`.
- False positive notes:
  - Existing mitigation blocks common direct prefixes, but does not fully cover known bypass patterns.

## Medium Findings

### SBP-003 (Medium): OAuth scaffolding accepts arbitrary `redirect_uri`

- Rule ID: OAuth redirect validation
- Severity: Medium
- Location:
  - `src/backend/api/documents.py:786`
  - `src/backend/api/documents.py:813`
  - `src/backend/api/documents.py:818`
- Evidence:
  - `redirect_uri` is accepted from query input and copied into returned `auth_url` without allowlist validation.
- Impact:
  - Enables open-ended callback targets in the OAuth start contract; this becomes a practical token/code leakage risk once full OAuth exchange is implemented.
- Fix:
  - Enforce a strict allowlist of approved callback origins/paths per environment and reject all others.
  - Bind generated `state` to server-side session storage for future callback verification.
- Mitigation:
  - Keep endpoint clearly marked as scaffold and block production rollout until redirect/state validation exists.
- False positive notes:
  - Risk is partially latent because token exchange is not implemented yet, but the insecure contract is being established now.

### SBP-004 (Medium): Sensitive search history persisted in `localStorage`

- Rule ID: frontend sensitive data storage
- Severity: Medium
- Location:
  - `src/frontend/src/pages/SearchPage.tsx:21`
  - `src/frontend/src/pages/SearchPage.tsx:27`
  - `src/frontend/src/pages/SearchPage.tsx:38`
  - `src/frontend/src/pages/SearchPage.tsx:63`
  - `src/frontend/src/pages/SearchPage.tsx:104`
- Evidence:
  - Search queries and saved searches are written to persistent `localStorage` keys (`hc.search.history.v1`, `hc.search.saved.v1`) automatically.
- Impact:
  - Medical-related query terms can persist indefinitely on shared devices and are exposed to any script running in-page (including future XSS).
- Fix:
  - Default to `sessionStorage` or explicit user opt-in with retention controls (TTL, clear-on-logout, “private mode”).
  - Avoid persisting raw sensitive search strings unless product/legal requirements explicitly approve it.
- Mitigation:
  - Provide UI controls to disable persistence and purge stored search data.
- False positive notes:
  - Not remote-code-execution by itself, but a meaningful confidentiality/privacy risk in a health-data context.

## Positive Security Changes Observed

- `src/frontend/src/components/SearchResults.tsx` removed `dangerouslySetInnerHTML`, which closes the prior direct XSS sink for snippets.
- `src/backend/modules/importers/apple_health.py` now fails closed if `defusedxml` is unavailable.
- `src/backend/api/documents.py` now enforces bounded upload reads before parsing.

## Verification

- Backend: `/mnt/c/Users/DangT/Documents/GitHub/HealthCentral/.venv/Scripts/python.exe -m pytest -q src/backend` → `249 passed`.
- Frontend: `npx vitest run` (in `src/frontend`) → `13 files, 95 passed`.
- Frontend: `npx tsc --noEmit` and `npx eslint src/pages/SearchPage.tsx src/__tests__/SearchPage.test.tsx` passed.
