/**
 * UI-PG-EXPORT (plan section 7.7): HC-UIEXP-001 to HC-UIEXP-004.
 *
 * HC-UIEXP-003 is a pin and is GREEN on the unedited page: every request body below was recorded from the page as it
 * stood before this row, by running it (api mock call log), not by reading the code. Redaction is untouched
 * (`git diff origin/main -- src/frontend/src/services/export.ts src/backend` is empty), so these bodies must not move.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ExportPage } from '@/pages/ExportPage';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiGetRaw: vi.fn(),
  apiPost: vi.fn(),
  ApiError: class ApiError extends Error {},
}));

URL.createObjectURL = vi.fn(() => 'blob:mock-url');
URL.revokeObjectURL = vi.fn();
HTMLAnchorElement.prototype.click = vi.fn();

const documents = [
  { id: 'doc-1', profile_id: 'profile-123', doc_type: 'lab_report', source: 'Quest Diagnostics', status: 'parsed', page_count: 2, collection_date: '2024-01-15', imported_at: '2024-01-16T00:00:00', parsed_at: null, verified_at: null, extraction_confidence: 0.9 },
  { id: 'doc-2', profile_id: 'profile-123', doc_type: 'lab_report', source: 'LabCorp', status: 'parsed', page_count: 1, collection_date: '2024-02-01', imported_at: '2024-02-02T00:00:00', parsed_at: null, verified_at: null, extraction_confidence: 0.9 },
];

const summaryResponse = {
  summary_id: 'summary-123',
  profile_id: 'profile-123',
  generated_at: '2024-01-15T12:00:00Z',
  format: 'text',
  key_findings: ['Hemoglobin A1c: 6.5% (H)', 'Glucose: 95.0 mg/dL (normal)'],
  abnormal_count: 1,
  date_range: 'All time',
};

const questionItems = [
  {
    category: 'abnormal',
    question: 'My hemoglobin A1c was outside the reference range. What might that indicate?',
    context: 'Value: 6.5 %, flagged as H',
    related_analytes: ['hemoglobin_a1c'],
  },
];

const visitPrepResponse = {
  packet_id: 'packet-123',
  profile_id: 'profile-123',
  generated_at: '2024-01-15T12:00:00Z',
  section_titles: ['Current medications', 'Questions for your provider'],
  markdown: '# Visit prep',
  redaction_count: 2,
};

const fhirResponse = {
  export_id: 'fhir-123',
  profile_id: 'profile-123',
  generated_at: '2024-01-15T12:00:00Z',
  resource_counts: { Observation: 3 },
  redaction_count: 1,
};

function rawResponse(contentType: string): Response {
  return {
    headers: new Headers({ 'Content-Type': contentType }),
    text: () => Promise.resolve('csv'),
    blob: () => Promise.resolve(new Blob(['x'], { type: contentType })),
  } as Response;
}

function setupApi({ withDocuments = false, summary = summaryResponse }: { withDocuments?: boolean; summary?: typeof summaryResponse } = {}) {
  vi.mocked(api.apiGet).mockImplementation((url: string) => {
    if (url.startsWith('/documents')) return Promise.resolve(withDocuments ? documents : []);
    if (url.startsWith('/observations')) return Promise.resolve([]);
    if (url === '/export/json') return Promise.resolve('[]');
    return Promise.resolve(null);
  });
  vi.mocked(api.apiGetRaw).mockImplementation(() => Promise.resolve(rawResponse('text/plain')));
  vi.mocked(api.apiPost).mockImplementation((url: string) => {
    if (url === '/export/doctor-summary') return Promise.resolve(summary);
    if (url === '/export/questions') return Promise.resolve(questionItems);
    if (url === '/export/visit-prep') return Promise.resolve(visitPrepResponse);
    if (url === '/export/fhir') return Promise.resolve(fhirResponse);
    return Promise.resolve(null);
  });
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ExportPage />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

/** Every export call the page made, in order: [method, url, ...args]. */
function recorded() {
  return [
    ...vi.mocked(api.apiGet).mock.calls.filter(([url]) => String(url).startsWith('/export')).map((c) => ['GET', ...c]),
    ...vi.mocked(api.apiGetRaw).mock.calls.map((c) => ['RAW', ...c]),
    ...vi.mocked(api.apiPost).mock.calls.map((c) => ['POST', ...c]),
  ];
}

/**
 * The toggle for a section. Today these are buttons named 'Include X' / 'Exclude X'; after UI-PG-EXPORT they are
 * checkboxes named X. Either role is accepted so the same pin runs on both.
 */
function toggle(label: string): HTMLElement {
  const box = screen.queryByRole('checkbox', { name: label });
  if (box) return box;
  return screen.getByRole('button', { name: new RegExp(`^(Include|Exclude) ${label}$`) });
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  useAuthStore.getState().setAuth({ token: 'test-token', profileId: 'profile-123', profileName: 'Test Profile' });
});

/** What goes over the wire: a JSON round trip drops `undefined` keys exactly as the request does. */
const wire = (body: unknown) => JSON.parse(JSON.stringify(body));

const postsTo = (url: string) => vi.mocked(api.apiPost).mock.calls.filter(([u]) => u === url);

/** The two consent boxes carry the same copy; the packet's comes first in the DOM, the bundle's second. */
const consentBoxes = () => screen.getAllByRole('checkbox', { name: /I understand/i });

async function generateSummary(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /generate summary/i }));
  await screen.findByRole('button', { name: /download summary/i });
}

// Bodies below were recorded by running the unedited page (see the file comment).
const SUMMARY_DEFAULTS = { include_trends: true, include_questions: false, format: 'text' };
const SUMMARY_TRENDS_OFF_QUESTIONS_ON = { include_trends: false, include_questions: true, format: 'text' };
const VISIT_PREP_DEFAULTS = {
  include_medications: true,
  include_labs: true,
  include_visits: true,
  include_tasks: true,
  include_questions: true,
  confirm: true,
};
const VISIT_PREP_CUSTOM = {
  reason_for_visit: 'Headaches',
  include_medications: false,
  include_labs: true,
  include_visits: true,
  include_tasks: true,
  include_questions: true,
  selected_doc_ids: ['doc-1'],
  confirm: true,
};

describe('HC-UIEXP-003: request bodies equal the recorded ones (pin, green on the unedited page)', () => {
  // Blind spot: the api module is mocked, so this pins what the page hands to apiGet/apiGetRaw/apiPost, not what
  // services/export.ts or the backend do with it. Both are untouched by this row (the diff is pasted in the PR).
  // jsdom applies no CSS, so it also cannot see whether a toggle is visible: it reads the same bodies either way.

  it('CSV is a raw GET with no filters, JSON a GET with no filters', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(screen.getByRole('button', { name: /download csv/i }));
    await user.click(screen.getByRole('button', { name: /download json/i }));

    await waitFor(() => expect(api.apiGet).toHaveBeenCalledWith('/export/json', {}));
    expect(api.apiGetRaw).toHaveBeenCalledWith('/export/csv', {});
    expect(recorded()).toEqual([
      ['GET', '/export/json', {}],
      ['RAW', '/export/csv', {}],
    ]);
  });

  it('Generate Summary on the defaults posts trends on and questions off, and asks for no questions', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await generateSummary(user);

    expect(vi.mocked(api.apiPost).mock.calls.map(([url]) => url)).toEqual(['/export/doctor-summary']);
    expect(wire(postsTo('/export/doctor-summary')[0][1])).toStrictEqual(SUMMARY_DEFAULTS);
  });

  it('trends off and questions on posts both flags, then asks for the questions with no body', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(toggle('Trend Analysis'));
    await user.click(toggle('Questions for Clinician'));
    await generateSummary(user);
    await waitFor(() => expect(postsTo('/export/questions')).toHaveLength(1));

    expect(wire(postsTo('/export/doctor-summary')[0][1])).toStrictEqual(SUMMARY_TRENDS_OFF_QUESTIONS_ON);
    expect(vi.mocked(api.apiPost).mock.calls.map(([url]) => url)).toEqual(['/export/doctor-summary', '/export/questions']);
    expect(postsTo('/export/questions')[0]).toEqual(['/export/questions']);
  });

  it('Results Summary and Flagged Values change nothing in the request (reported, not fixed)', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(toggle('Results Summary'));
    await user.click(toggle('Flagged Values'));
    await generateSummary(user);

    expect(wire(postsTo('/export/doctor-summary')[0][1])).toStrictEqual(SUMMARY_DEFAULTS);
  });

  it.each([
    ['Plain Text (.txt)', 'text'],
    ['HTML (.html)', 'html'],
    ['PDF (.pdf)', 'pdf'],
  ])('Download Summary with %s asks for format %s', async (label, format) => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await generateSummary(user);
    await user.click(screen.getByText(label));
    await user.click(screen.getByRole('button', { name: /download summary/i }));

    await waitFor(() =>
      expect(api.apiGetRaw).toHaveBeenCalledWith('/export/doctor-summary/summary-123/download', { format })
    );
    expect(vi.mocked(api.apiGetRaw).mock.calls).toHaveLength(1);
  });

  it('Generate Packet on the defaults sends every section on, no reason and no documents, with confirm', async () => {
    const user = userEvent.setup();
    setupApi({ withDocuments: true });
    renderPage();

    await user.click(consentBoxes()[0]);
    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');

    expect(postsTo('/export/visit-prep')).toHaveLength(1);
    expect(wire(postsTo('/export/visit-prep')[0][1])).toStrictEqual(VISIT_PREP_DEFAULTS);
  });

  it('Generate Packet with a toggled section, a trimmed reason and a chosen document sends them', async () => {
    const user = userEvent.setup();
    setupApi({ withDocuments: true });
    renderPage();

    await user.click(toggle('Current medications'));
    await user.type(screen.getByLabelText(/reason for visit/i), '  Headaches  ');
    await user.click(await screen.findByRole('checkbox', { name: /Quest Diagnostics/ }));
    await user.click(consentBoxes()[0]);
    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');

    expect(wire(postsTo('/export/visit-prep')[0][1])).toStrictEqual(VISIT_PREP_CUSTOM);
  });

  it('two chosen documents are sent in the order they were chosen, and a reason of spaces is left out', async () => {
    const user = userEvent.setup();
    setupApi({ withDocuments: true });
    renderPage();

    await user.type(screen.getByLabelText(/reason for visit/i), '   ');
    await user.click(await screen.findByRole('checkbox', { name: /LabCorp/ }));
    await user.click(screen.getByRole('checkbox', { name: /Quest Diagnostics/ }));
    await user.click(consentBoxes()[0]);
    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');

    expect(wire(postsTo('/export/visit-prep')[0][1])).toStrictEqual({
      ...VISIT_PREP_DEFAULTS,
      selected_doc_ids: ['doc-2', 'doc-1'],
    });
  });

  it.each([
    ['Plain Text (.txt)', 'markdown'],
    ['HTML (.html)', 'html'],
    ['PDF (.pdf)', 'pdf'],
  ])('Download Packet with %s asks for format %s (text maps to markdown)', async (label, format) => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(screen.getByText(label));
    await user.click(consentBoxes()[0]);
    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await user.click(await screen.findByRole('button', { name: /download packet/i }));

    await waitFor(() =>
      expect(api.apiGetRaw).toHaveBeenCalledWith('/export/visit-prep/packet-123/download', { format })
    );
  });

  it('Generate Bundle posts only confirm: true, and Download Bundle fetches the bundle with no params', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(consentBoxes()[1]);
    await user.click(screen.getByRole('button', { name: /generate bundle/i }));
    await screen.findByText('Bundle ready');
    await user.click(screen.getByRole('button', { name: /download bundle/i }));

    expect(postsTo('/export/fhir')).toHaveLength(1);
    expect(wire(postsTo('/export/fhir')[0][1])).toStrictEqual({ confirm: true });
    await waitFor(() => expect(api.apiGetRaw).toHaveBeenCalledWith('/export/fhir/fhir-123/download'));
    expect(vi.mocked(api.apiGetRaw).mock.calls[0]).toEqual(['/export/fhir/fhir-123/download']);
  });

  it('no visit-prep or FHIR request goes out before its consent box is ticked', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    const prep = screen.getByRole('button', { name: /generate packet/i });
    const bundle = screen.getByRole('button', { name: /generate bundle/i });
    expect(prep).toBeDisabled();
    expect(bundle).toBeDisabled();
    await user.click(prep);
    await user.click(bundle);
    expect(postsTo('/export/visit-prep')).toHaveLength(0);
    expect(postsTo('/export/fhir')).toHaveLength(0);

    // Ticking one box frees only its own button, and clearing it locks the button again.
    await user.click(consentBoxes()[0]);
    expect(prep).toBeEnabled();
    expect(bundle).toBeDisabled();
    await user.click(consentBoxes()[0]);
    expect(prep).toBeDisabled();
    await user.click(prep);
    expect(vi.mocked(api.apiPost).mock.calls).toHaveLength(0);
  });
});

describe('UI-PG-EXPORT keeps behaviour: what clears a generated file (green today)', () => {
  // Blind spot: pins the enabled/disabled state of Download Packet and Download Bundle, which is how the page shows
  // that a generated file was dropped. It cannot see the page's internal state.
  it('a visit-prep section or document toggle drops the packet; its consent box does not', async () => {
    const user = userEvent.setup();
    setupApi({ withDocuments: true });
    renderPage();

    await user.click(consentBoxes()[0]);
    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');
    const download = screen.getByRole('button', { name: /download packet/i });
    expect(download).toBeEnabled();

    await user.click(toggle('Open follow-up items'));
    expect(screen.queryByText('Packet ready')).not.toBeInTheDocument();
    expect(download).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');
    await user.click(await screen.findByRole('checkbox', { name: /LabCorp/ }));
    expect(screen.queryByText('Packet ready')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /generate packet/i }));
    await screen.findByText('Packet ready');
    await user.click(consentBoxes()[0]);
    expect(screen.getByText('Packet ready')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /download packet/i })).toBeEnabled();
  });

  it('un-ticking the FHIR consent box drops the bundle', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(consentBoxes()[1]);
    await user.click(screen.getByRole('button', { name: /generate bundle/i }));
    await screen.findByText('Bundle ready');
    await user.click(consentBoxes()[1]);
    expect(screen.queryByText('Bundle ready')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /download bundle/i })).toBeDisabled();
  });
});

const REDACTION_COPY =
  'Redaction level: strict. Personal identifiers that match known patterns are removed before this summary is saved or downloaded. CSV and JSON downloads are your own full copy and are not redacted. The question lines shown in this preview, and in text copied with Copy Text, are not redacted.';

describe('HC-UIEXP-001: Full Preview opens a Sheet with the summary', () => {
  // Blind spot: jsdom applies no CSS and runs no motion, so this cannot see the sheet's size, its slide, or that it
  // sits above the page; e2e/ui-export.spec.ts checks those in a real browser. The inline-style check below catches a
  // missing `still` only because framer writes a sheet's initial transform inline.
  it('is disabled until a summary exists', () => {
    setupApi();
    renderPage();

    expect(screen.getByRole('button', { name: /full preview/i })).toBeDisabled();
  });

  it('opens a dialog named by its title that holds the summary values, and Escape closes it', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await generateSummary(user);
    await user.click(screen.getByRole('button', { name: /full preview/i }));

    const dialog = await screen.findByRole('dialog', { name: 'Full summary preview' });
    expect(within(dialog).getByText('Health Summary Report')).toBeInTheDocument();
    expect(within(dialog).getByText('All time')).toBeInTheDocument();
    expect(within(dialog).getByText(/1 abnormal/)).toBeInTheDocument();
    expect(within(dialog).getByText('Hemoglobin A1c: 6.5% (H)')).toBeInTheDocument();
    expect(within(dialog).getByText('Glucose: 95.0 mg/dL (normal)')).toBeInTheDocument();
    expect(within(dialog).getByText(/This is not medical advice/)).toBeInTheDocument();

    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('shows the clinician questions in the sheet when they were asked for', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await user.click(toggle('Questions for Clinician'));
    await generateSummary(user);
    await user.click(screen.getByRole('button', { name: /full preview/i }));

    const dialog = await screen.findByRole('dialog', { name: 'Full summary preview' });
    expect(within(dialog).getByText(questionItems[0].question)).toBeInTheDocument();
  });

  it('is still (M0): the sheet carries no inline opacity or transform', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await generateSummary(user);
    await user.click(screen.getByRole('button', { name: /full preview/i }));

    const dialog = await screen.findByRole('dialog', { name: 'Full summary preview' });
    expect(dialog.style.opacity).toBe('');
    expect(dialog.style.transform).toBe('');
  });
});

describe('HC-UIEXP-002: no native unstyled checkbox on the page', () => {
  // Blind spot: counts DOM nodes and roles. It cannot see that a Checkbox is drawn, that it has a visible focus
  // ring, or that the row's hit area is large enough; the dark axe pass and the screenshots in e2e do.
  it('has no visible native checkbox input, and every checkbox row is a Checkbox button', async () => {
    setupApi({ withDocuments: true });
    const { container } = renderPage();
    await screen.findByRole('checkbox', { name: /Quest Diagnostics/ });

    const native = container.querySelectorAll('input[type="checkbox"]:not([aria-hidden="true"])');
    expect(native.length).toBe(0);

    // 4 export sections + 5 packet sections + 2 attachable documents + 2 consent boxes.
    const boxes = screen.getAllByRole('checkbox');
    expect(boxes).toHaveLength(13);
    expect(boxes.every((box) => box.tagName === 'BUTTON')).toBe(true);
  });

  it('the Include Sections rows are named checkboxes that report their state', async () => {
    setupApi();
    renderPage();

    expect(screen.getByRole('checkbox', { name: 'Results Summary' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Trend Analysis' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Flagged Values' })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'Questions for Clinician' })).not.toBeChecked();
  });

  it('clicking a row label toggles its checkbox, and the two "questions" sections stay separate', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    const exportQuestions = screen.getByRole('checkbox', { name: 'Questions for Clinician' });
    const packetQuestions = screen.getByRole('checkbox', { name: 'Questions for your provider' });
    await user.click(screen.getByText('Questions for Clinician'));
    expect(exportQuestions).toBeChecked();
    expect(packetQuestions).toBeChecked();
    await user.click(screen.getByText('Questions for your provider'));
    expect(exportQuestions).toBeChecked();
    expect(packetQuestions).not.toBeChecked();
  });

  it('every id is unique and every label points at an element that exists', async () => {
    setupApi({ withDocuments: true });
    const { container } = renderPage();
    await screen.findByRole('checkbox', { name: /Quest Diagnostics/ });

    const ids = Array.from(container.querySelectorAll('[id]')).map((el) => el.id);
    expect(ids.filter((id, i) => ids.indexOf(id) !== i)).toEqual([]);
    const dangling = Array.from(container.querySelectorAll('label[for]'))
      .map((label) => label.getAttribute('for') as string)
      .filter((id) => !container.querySelector(`[id="${id}"]`));
    expect(dangling).toEqual([]);
  });
});

describe('HC-UIEXP-004: the redaction level is shown as read-only text', () => {
  // Blind spot: jsdom checks that the text exists, carries data-t0 and sits in no control. It cannot prove the
  // sentence is true: strict is pattern-based, the CSV and JSON exports are exempt (D3), and the question lines
  // from POST /export/questions are not redacted, which is why the copy says so. The stillness probe in e2e
  // covers the data-t0 behaviour.
  it('is present before any summary exists, with data-t0, in no control', () => {
    setupApi();
    renderPage();

    const text = screen.getByText(REDACTION_COPY);
    expect(text).toHaveAttribute('data-t0');
    expect(text.closest('input, select, textarea, button, form, [role]')).toBeNull();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('says CSV and JSON are not redacted', () => {
    setupApi();
    renderPage();

    expect(screen.getByText(/CSV and JSON downloads are your own full copy and are not redacted\./)).toBeInTheDocument();
  });

  it('says the question lines and Copy Text are not redacted', () => {
    setupApi();
    renderPage();

    expect(
      screen.getByText(/The question lines shown in this preview, and in text copied with Copy Text, are not redacted\./)
    ).toBeInTheDocument();
  });

  it('is repeated in the Full Preview sheet', async () => {
    const user = userEvent.setup();
    setupApi();
    renderPage();

    await generateSummary(user);
    await user.click(screen.getByRole('button', { name: /full preview/i }));

    const dialog = await screen.findByRole('dialog', { name: 'Full summary preview' });
    expect(within(dialog).getByText(REDACTION_COPY)).toHaveAttribute('data-t0');
  });
});
