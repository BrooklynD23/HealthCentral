# Browser MCP — manual UI verification playbook

Use this with Cursor’s **browser automation MCP** (or any MCP that exposes navigate, snapshot, click, type, file upload, and screenshot). Tool names differ by Cursor version; map each step to your client’s equivalents.

## Prerequisites

1. Start the stack from the repo root (ports may differ if 3000/8000 are busy — **read the script output**):
   - PowerShell: `.\dev.ps1`
2. Note the **frontend base URL** (for example `http://127.0.0.1:3000` or another port).
3. Confirm the PDF exists at the path you will use (default below).

## Testing profile

Use a display name that **starts with** `Playwright E2E` so non-production builds can call `POST /api/v1/profiles/test/reset` if you need a clean vault (see [`profiles.py`](../../backend/api/profiles.py)).

**Option A — UI**

1. Open `{baseURL}/setup`.
2. Create a profile, e.g. display name `Playwright E2E Manual Verify`, with a password you can reuse.

**Option B — Match Playwright E2E helpers**

- Default automation profile: `Playwright E2E Profile` / password `SecurePass123` (see [`support/auth.ts`](./support/auth.ts)). Create it once via API or UI so it matches.

## Real PDF path

- Default verification file (Windows): `F:\12-07-2024 LIDPID .pdf` (note the **space** before `.pdf`).
- To override in Playwright: set `HC_E2E_REAL_PDF`.

## Upload (Inbox)

1. Navigate to `{baseURL}/inbox` (authenticated).
2. Set the hidden file input labeled **“Upload medical documents”** (or use **Import Document** / **Browse Files** to focus it) to the PDF path above.

Wait until the row appears in **Recent Documents** and a status badge shows (for example **Verified**, **Needs Review**, **Pending**, or **OCR Required**).

## Systematic UI sweep

For **every** step, record a row in your report (see schema below).

### Main navigation (Sidebar)

Routes under **Main navigation** (see [`Sidebar.tsx`](../src/components/layout/Sidebar.tsx)):

| Label   | Path            |
|---------|-----------------|
| Inbox   | `/inbox`        |
| Verify  | `/verify`       |
| Trends  | `/trends`       |
| Interpret | `/interpret`  |
| Meds    | `/medications`  |
| Alerts  | `/notifications` |
| Explain | `/explain`      |
| Export  | `/export`       |
| Settings| `/settings`     |

For each: navigate, confirm the main content loads (no blank error surface), primary controls respond to click/focus.

### Top bar

- **Search** field (“Search tests, terms…” / `aria-label="Search tests and terms"`).
- **Safety Mode** toggle (`aria-label` like `Safety mode enabled` / `disabled`).
- **Profile and settings** → `/settings`.

### Document Inbox (after import)

- **Import Document**, **Browse Files**, drag-and-drop zone.
- Row actions: **View document** (`aria-label="View document"`), **More options** → **Open in Verify**, **Delete…** (cancel if you must keep data).

### Verify

- Open from inbox row or `/verify` (optionally `?doc=<id>`).
- Exercise verify / edit controls and any overlays (see Verification Workbench).

### Explain Assistant

- Category filter (`combobox` **Document Category**), date/analyte filters if visible.
- Suggested question buttons, message input, send control.
- Expect either a normal reply **or** a documented fallback (insufficient context, model not configured, knowledge-base-only messaging).

### Settings

- **Detect Hardware** / **Re-detect** — confirm hardware grid or recommended tier appears after success.
- Tier cards — optional: select tier **without** starting a long download unless you intend to wait.
- **Do not** enter real third-party API keys; use dummy values or skip save.

### Lazy-loaded routes

`/trends`, `/interpret`, `/medications`, `/notifications`, `/export` load chunks on first visit — wait for skeletons to clear and confirm a heading or main landmark.

## Report schema (required fields)

For each interaction:

| Field | Description |
|-------|-------------|
| **Area** | Where in the app (e.g. `Sidebar > Explain`, `Inbox > row actions`). |
| **Intent** | What the user tried to do. |
| **Result** | `PASS`, `FAIL`, or `BLOCKED` (environment prerequisite missing). |
| **Locator evidence** | From accessibility snapshot: **role + accessible name**, or stable CSS selector. Prefer **not** raw `div` text alone. |
| **URL** | Full URL when the result was observed. |
| **Evidence** | On **FAIL** / **BLOCKED**: screenshot path or attachment; optional **console** excerpt if a JS error occurred. |

On failure, name the exact control (e.g. `button "Detect Hardware"`, `combobox "Document Category"`) so developers can locate it quickly.

## Optional: MCP snapshot → “highlight” narrative

If your MCP provides an accessibility tree snapshot, cite the **node ref** or **selector** from the snapshot as the locator evidence. For visual emphasis on failure, attach a **screenshot** and quote the control’s accessible name in the report.

## Related automation

- Playwright regression (local PDF, optional project **`real-pdf-local`**): [`ui-full-verification.spec.ts`](./ui-full-verification.spec.ts).
