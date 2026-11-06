/**
 * UI-ABOUT (HC-UIABT-001 .. 004): the public About page at /about.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md, section UI-ABOUT, §4.2 About row, §2.6 S1-S4, §2.7.
 * The page is rendered through App's own route, so a route that sits behind ProtectedRoute (and redirects a visitor
 * with no profile to /setup) fails here. jsdom runs no CSS animation and lays out no boxes: the browser half of each
 * id (a real request log, the stillness probe through S1, axe, G6) is e2e/ui-about.spec.ts.
 *
 * What these tests would not notice:
 * - a request made by a third-party module the page does not import itself (the e2e request log sees it);
 * - the S1 entrance really moving or the ribbon really drawing (jsdom plays no animation; HC-UIABT-002 e2e measures);
 * - a remote asset pulled in by CSS or a font (the source audit reads AboutPage.tsx only; HC-UIABT-004 e2e watches the
 *   network).
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import App from '@/App';
import { MotionProvider } from '@/motion/MotionProvider';
import { ProfileMenu } from '@/components/layout/ProfileMenu';
import { useAuthStore } from '@/stores/authStore';

// The library draws on a canvas, which jsdom does not provide: a stub stands in, as in ui-showcase.test.tsx.
vi.mock('thinking-orbs', async () => {
  const React = await import('react');
  return {
    ThinkingOrb: () => React.createElement('canvas', { 'data-testid': 'orb' }),
  };
});

/** The page's source, read once. Empty when the file does not exist yet, which the audit test below rejects. */
function readAboutSource(): string {
  try {
    return readFileSync(join(resolve(__dirname, '../pages'), 'AboutPage.tsx'), 'utf8');
  } catch {
    return '';
  }
}
const ABOUT_SOURCE = readAboutSource();
const EXAMPLE_LABEL = 'Example data, not yours';

/** Every request the page makes: fetch (the API client) and XMLHttpRequest. */
let requests: string[] = [];
const realFetch = globalThis.fetch;
const realXhrOpen = XMLHttpRequest.prototype.open;

beforeEach(() => {
  requests = [];
  globalThis.fetch = vi.fn((input: RequestInfo | URL) => {
    requests.push(String(input instanceof Request ? input.url : input));
    return Promise.reject(new Error('no network in this test'));
  }) as typeof fetch;
  XMLHttpRequest.prototype.open = function (this: XMLHttpRequest, _method: string, url: string | URL) {
    requests.push(String(url));
    // eslint-disable-next-line prefer-rest-params
    return (realXhrOpen as (...args: unknown[]) => void).apply(this, arguments as unknown as unknown[]);
  } as typeof XMLHttpRequest.prototype.open;
  window.sessionStorage.clear();
  window.localStorage.clear();
  useAuthStore.getState().clearAuth();
});

afterEach(() => {
  globalThis.fetch = realFetch;
  XMLHttpRequest.prototype.open = realXhrOpen;
  window.history.pushState({}, '', '/');
});

const T0_SELECTORS = ['[data-about-safety]', '[data-about-not-advice]', '[data-about-local-first]', '[data-about-example-label]'];

/** App's own router reads window.location, so the route is the real one. Resolves at the page's first render. */
async function renderAboutFirst() {
  window.history.pushState({}, '', '/about');
  const view = render(
    <MotionProvider>
      <App />
    </MotionProvider>
  );
  await screen.findByRole('heading', { level: 1 });
  return view;
}

/** The whole page: the first render, then the part that mounts after the first paint (the ribbon onwards). */
async function renderAbout() {
  const view = await renderAboutFirst();
  await screen.findByRole('slider');
  return view;
}

describe('HC-UIABT-001: /about renders without a profile and makes no API request', () => {
  it('HC-UIABT-001: a visitor with no profile stays on /about and sees one h1', async () => {
    await renderAbout();
    expect(window.location.pathname).toBe('/about');
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('HC-UIABT-001: no request of any kind is made, signed out or signed in', async () => {
    const signedOut = await renderAbout();
    // Let the lazy orb chunk and any effect settle before counting.
    await screen.findByTestId('orb');
    await new Promise((resolveWait) => setTimeout(resolveWait, 50));
    expect(requests).toEqual([]);
    signedOut.unmount();

    useAuthStore.getState().setAuth({
      token: 'live-token',
      profileId: 'profile-about-1',
      profileName: 'Test profile',
      expiresIn: 3600,
    });
    await renderAbout();
    await screen.findByTestId('orb');
    await new Promise((resolveWait) => setTimeout(resolveWait, 50));
    expect(window.location.pathname).toBe('/about');
    expect(requests).toEqual([]);
    // No shell: a visitor who is signed in still gets the bare page.
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull();
  });

  it('HC-UIABT-001: AboutPage.tsx imports no service, no auth store, no query hook, and names no remote asset', () => {
    expect(ABOUT_SOURCE.length, 'AboutPage.tsx exists and is not empty').toBeGreaterThan(0);
    // A type-only import is erased at build time and loads nothing: the TrendData type for the example is allowed.
    const imports = ABOUT_SOURCE.split('\n')
      .filter((line) => /^\s*import\b/.test(line) || /\bfrom\s+['"]/.test(line))
      .filter((line) => !/^\s*import\s+type\b/.test(line));
    const forbidden = imports.filter((line) => /services|authStore|react-query|stores\//.test(line));
    expect(forbidden).toEqual([]);
    expect(ABOUT_SOURCE).not.toMatch(/\bfetch\s*\(|XMLHttpRequest|axios/);
    // All assets local: no URL with a scheme, no image, frame, embed or CSS url().
    expect(ABOUT_SOURCE).not.toMatch(/https?:\/\//);
    expect(ABOUT_SOURCE).not.toMatch(/<(img|iframe|embed|object|video|audio|source|link)\b/);
    expect(ABOUT_SOURCE).not.toMatch(/url\(|@import/);
  });
});

describe('HC-UIABT-002: the T0 statements sit outside every S1 wrapper', () => {
  it('HC-UIABT-002: the safety, not-advice and local-first statements carry data-t0 and no ancestor opacity or transform', async () => {
    await renderAbout();
    const selectors = ['[data-about-safety]', '[data-about-not-advice]', '[data-about-local-first]', '[data-about-example-label]'];
    for (const selector of selectors) {
      const node = document.querySelector<HTMLElement>(selector);
      expect(node, selector).not.toBeNull();
      expect(node!.hasAttribute('data-t0'), `${selector} data-t0`).toBe(true);
      expect(node!.textContent?.trim().length ?? 0, `${selector} has text`).toBeGreaterThan(5);
      for (let el: HTMLElement | null = node; el; el = el.parentElement) {
        expect(el.style.opacity, `${selector} ancestor ${el.tagName} opacity`).toBe('');
        expect(el.style.transform, `${selector} ancestor ${el.tagName} transform`).toBe('');
      }
    }
  });

  it('HC-UIABT-002: the S1 groups are really wrapped (a first visit starts them hidden), so the guard above can fail', async () => {
    await renderAbout();
    const groups = Array.from(document.querySelectorAll<HTMLElement>('[data-about-group]'));
    expect(groups.length).toBeGreaterThanOrEqual(2);
    expect(groups.length).toBeLessThanOrEqual(6);
    for (const group of groups) {
      const wrapper = group.parentElement as HTMLElement;
      // ShowcaseReveal's group wrapper starts at opacity 0 on the first visit per session.
      expect(wrapper.style.opacity, group.getAttribute('data-about-group') ?? '').toBe('0');
      // None of them holds T0 content.
      expect(group.querySelector('[data-t0]')).toBeNull();
    }
  });
});

describe('HC-UIABT-006: a light first render (G10 first visit)', () => {
  it('HC-UIABT-006: the first render holds the four T0 statements but not the ribbon or the S1 sections, which mount after the first paint', async () => {
    await renderAboutFirst();
    // First render: the T0 text is there at once.
    const first = T0_SELECTORS.map((selector) => document.querySelector<HTMLElement>(selector));
    T0_SELECTORS.forEach((selector, index) => {
      expect(first[index], `${selector} in the first render`).not.toBeNull();
      expect(first[index]!.hasAttribute('data-t0'), `${selector} data-t0`).toBe(true);
    });
    // The heavy part is not: no ribbon, no S1 group, no orb, no call to action.
    // Booleans and counts, not elements: a failure message then names the check instead of printing an svg.
    expect(screen.queryByRole('slider') === null, 'no ribbon in the first render').toBe(true);
    expect(document.querySelectorAll('[data-about-group]').length, 'S1 groups in the first render').toBe(0);
    expect(screen.queryByRole('status') === null, 'no orb status in the first render').toBe(true);
    expect(screen.queryByRole('link', { name: 'Open Asclexis' }) === null, 'no call to action in the first render').toBe(true);
    // The labelled region is already there, holding the ribbon's place.
    const region = screen.getByRole('region', { name: EXAMPLE_LABEL });
    expect(region.querySelector('[data-about-ribbon-slot]') !== null, 'ribbon slot in the first render').toBe(true);

    // After the first paint: the ribbon in the labelled region, then S1 and the call to action.
    expect(await within(region).findByRole('slider')).toBeInTheDocument();
    expect(region.querySelector('[data-about-ribbon-slot]') === null, 'slot gone once the ribbon is in').toBe(true);
    expect(document.querySelectorAll('[data-about-group]').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole('link', { name: 'Open Asclexis' })).toBeInTheDocument();
    // The T0 nodes were not remounted: the same elements, so a probe baseline taken at the first render still holds.
    T0_SELECTORS.forEach((selector, index) => {
      expect(document.querySelector(selector) === first[index], `${selector} is the same node`).toBe(true);
    });
  });
});

describe('HC-UIABT-003: the example chart is labelled as example data, in text', () => {
  it('HC-UIABT-003: the exact label is visible DOM text, outside any svg, once', async () => {
    await renderAbout();
    const matches = screen.getAllByText(EXAMPLE_LABEL, { exact: true });
    expect(matches).toHaveLength(1);
    const label = matches[0];
    expect(label.closest('svg')).toBeNull();
    expect(label.hasAttribute('aria-hidden')).toBe(false);
    expect(label.closest('[aria-hidden="true"]')).toBeNull();
  });

  it('HC-UIABT-003: the label names the region that holds the ribbon, and comes before it', async () => {
    await renderAbout();
    const region = screen.getByRole('region', { name: EXAMPLE_LABEL });
    const ribbon = within(region).getByRole('slider');
    expect(ribbon.getAttribute('aria-label')).toBe('Example analyte: results over time');
    const label = within(region).getByText(EXAMPLE_LABEL, { exact: true });
    // Label first, ribbon after: the label is adjacent to what it labels.
    expect(label.compareDocumentPosition(ribbon) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // The only ribbon on the page is this one.
    expect(screen.getAllByRole('slider')).toHaveLength(1);
  });

  it('HC-UIABT-003: the ribbon sits outside ShowcaseReveal and has no opacity, transform or clip-path wrapper', async () => {
    await renderAbout();
    const ribbon = screen.getByRole('slider');
    expect(ribbon.closest('[data-about-group]')).toBeNull();
    for (let el: Element | null = ribbon; el && el !== document.body; el = el.parentElement) {
      const style = (el as HTMLElement).style;
      if (!style) continue;
      expect(style.opacity, `${el.tagName} opacity`).toBe('');
      expect(style.transform, `${el.tagName} transform`).toBe('');
      expect(style.clipPath, `${el.tagName} clip-path`).toBe('');
    }
  });

  it('HC-UIABT-003: the example names no real test and no person', async () => {
    await renderAbout();
    const region = screen.getByRole('region', { name: EXAMPLE_LABEL });
    expect(region.textContent).toMatch(/Example analyte/);
    expect(region.textContent).not.toMatch(/glucose|a1c|cholesterol|hemoglobin|creatinine|tsh|ldl|hdl/i);
    expect(ABOUT_SOURCE).toMatch(/doc_id:\s*'example'/);
  });
});

describe('HC-UIABT-005: the example data does not say the visitor checked it', () => {
  it('HC-UIABT-005: every example point reads "Not yet checked", and "Checked by you" appears nowhere on the page', async () => {
    await renderAbout();
    const cells = Array.from(document.querySelectorAll('td')).filter((td) => /checked/i.test(td.textContent ?? ''));
    expect(cells).toHaveLength(4);
    for (const cell of cells) expect(cell.textContent).toBe('Not yet checked');
    expect(document.body.textContent ?? '').not.toContain('Checked by you');
  });
});

describe('HC-UIABT-004: content, copy and the showcase pieces (G7 itself is e2e)', () => {
  it('HC-UIABT-004: says what it is and is not, local-first, and how it works', async () => {
    await renderAbout();
    const text = document.body.textContent ?? '';
    expect(text).toMatch(/not medical advice/i);
    expect(text).toMatch(/not a medical device/i);
    expect(text).toMatch(/your records stay on this device/i);
    expect(text).toMatch(/capstone/i);
    const steps = screen.getByRole('list', { name: 'How it works' });
    expect(within(steps).getAllByRole('listitem')).toHaveLength(4);
    expect(steps.textContent).toMatch(/import/i);
    expect(steps.textContent).toMatch(/review/i);
    expect(steps.textContent).toMatch(/results/i);
    expect(steps.textContent).toMatch(/ask/i);
    expect(steps.textContent).toMatch(/sources/i);
  });

  it('HC-UIABT-004: no "AI-powered", no "abnormal", no claim to diagnose or to set doses', async () => {
    await renderAbout();
    // On the About page itself: a redirect to /setup would pass the copy checks below by saying nothing.
    expect(window.location.pathname).toBe('/about');
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('About Asclexis');
    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/ai-powered|abnormal/i);
    expect(text).not.toMatch(/\b(you have|this means you|take \d)/i);
  });

  it('HC-UIABT-004: one orb in the how-it-works part, with its status as the only line; one beam round the single call to action', async () => {
    await renderAbout();
    expect(await screen.findAllByTestId('orb')).toHaveLength(1);
    const status = screen.getByRole('status');
    expect(status.textContent).toBe('How it reads a report');
    expect(status.closest('[data-about-group="how-it-works"]')).not.toBeNull();
    // The words are not repeated next to the orb.
    expect(screen.getAllByText('How it reads a report')).toHaveLength(1);

    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(1);
    expect(links[0].getAttribute('href')).toBe('/');
    expect(links[0].closest('[data-active="true"]')).not.toBeNull();
    expect(document.querySelectorAll('[data-active="true"]')).toHaveLength(1);
  });
});

describe('UI-ABOUT: copy that states the limit with the claim (brand section 4)', () => {
  it('the intro does not claim Asclexis answers nothing, and sends the meaning to the healthcare provider', async () => {
    await renderAbout();
    const intro = screen.getByRole('heading', { level: 1 }).nextElementSibling?.textContent ?? '';
    expect(intro).not.toMatch(/does not answer/i);
    expect(intro).toMatch(/ask better questions/);
    expect(intro).toMatch(/healthcare provider can tell you what your results mean for you/);
  });

  it('the results step names the reference range used for that chart, not the range printed on the report', async () => {
    await renderAbout();
    const steps = document.querySelector('ol')?.textContent ?? '';
    expect(steps).toMatch(/next to the reference range used for that chart/);
    expect(steps).not.toMatch(/printed on your report/);
  });

  it('the local-first statement names the optional external AI setting as its one exception', async () => {
    await renderAbout();
    const statement = document.querySelector('[data-about-local-first]')?.textContent ?? '';
    expect(statement).toMatch(/Your records stay on this device/);
    expect(statement).toMatch(/optional external AI setting/);
    expect(statement).toMatch(/off unless you turn it on/);
    // It says what the setting does, and the storage claim matches the layout (a vault per profile).
    expect(statement).toMatch(/while it is on, its requests leave this device/);
    expect(statement).toMatch(/encrypted in a separate vault for each profile/);
    expect(statement).not.toMatch(/encrypted file/);
  });
});

describe('UI-ABOUT: the profile menu links to /about', () => {
  it('the menu has an About link to /about between Settings and Lock now', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/inbox']}>
          <ProfileMenu />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await user.click(screen.getByRole('button', { name: 'Profile and settings' }));

    const settings = await screen.findByRole('link', { name: 'Settings' });
    const about = screen.getByRole('link', { name: 'About' });
    const lock = screen.getByRole('button', { name: 'Lock now' });
    expect(about.getAttribute('href')).toBe('/about');
    expect(settings.compareDocumentPosition(about) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(about.compareDocumentPosition(lock) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('choosing About closes the menu', async () => {
    const user = userEvent.setup();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/inbox']}>
          <ProfileMenu />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await user.click(screen.getByRole('button', { name: 'Profile and settings' }));
    await user.click(await screen.findByRole('link', { name: 'About' }));
    await waitFor(() => expect(screen.queryByRole('link', { name: 'About' })).toBeNull());
  });
});
