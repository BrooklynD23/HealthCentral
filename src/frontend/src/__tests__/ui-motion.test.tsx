/**
 * UI-MOTION (HC-UIMO-001..003): one motion API, LazyMotion strict, and a
 * synchronous reduced-motion read on the first render.
 *
 * framer-motion is deliberately NOT mocked in this file: the point is to see
 * the real library reject a leftover `motion.*` under LazyMotion strict.
 */

import { describe, it, expect, vi, beforeEach, afterEach, onTestFinished } from 'vitest';
import { Component, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { renderToStaticMarkup } from 'react-dom/server';
import { act, render, waitFor } from '@testing-library/react';
import App from '@/App';
import { PageTransition } from '@/components/ui/Motion';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/api', () => ({
  // Empty GETs resolve to []. Endpoints whose page reads a field off the
  // response get that field, so the route renders its empty state.
  apiGet: vi.fn(async (path: string) => {
    if (path === '/gamification/badges') return { badges: [] };
    if (path === '/settings/model/diagnostics') return { components: [] };
    if (path === '/settings/model/tiers') return { tiers: [], recommended_tier: null };
    if (path === '/medications/med-1') return { id: 'med-1', name: 'Test medication', schedules: [] };
    return [];
  }),
  apiPost: vi.fn().mockResolvedValue({}),
  apiPut: vi.fn().mockResolvedValue({}),
  apiPatch: vi.fn().mockResolvedValue({}),
  apiDelete: vi.fn().mockResolvedValue(undefined),
  apiGetRaw: vi.fn().mockResolvedValue(new Response('')),
  apiUpload: vi.fn().mockResolvedValue({}),
  getApiBaseUrl: () => 'http://localhost:8000/api/v1',
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

const SELF = __filename;
const SRC_DIR = resolve(__dirname, '..');
const PACKAGE_JSON = resolve(__dirname, '../..', 'package.json');

// `import { motion, ... } from 'framer-motion'` (single or multi-line).
const MOTION_IMPORT = /import\s*(?:type\s*)?\{[^}]*\bmotion\b[^}]*\}\s*from\s*['"]framer-motion['"]/;
// A namespace import, e.g. `import * as FM from 'framer-motion'`. It is flagged
// because this audit cannot follow `FM.motion`; use named imports instead.
const NAMESPACE_IMPORT = /import\s+\*\s+as\s+\w+\s+from\s*['"]framer-motion['"]/;
// A `motion` element in JSX, e.g. <motion.div ...>.
const MOTION_JSX = /<motion\./;

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

describe('UI-MOTION source audit', () => {
  it('HC-UIMO-001: no motion component is imported from framer-motion or rendered as <motion.*> outside src/motion/', () => {
    const motionDir = join(SRC_DIR, 'motion') + sep;
    const offenders = walk(SRC_DIR)
      .filter((file) => /\.(ts|tsx)$/.test(file))
      .filter((file) => file !== SELF && !file.startsWith(motionDir))
      .filter((file) => {
        const text = readFileSync(file, 'utf8');
        return MOTION_IMPORT.test(text) || NAMESPACE_IMPORT.test(text) || MOTION_JSX.test(text);
      })
      .map((file) => relative(SRC_DIR, file));

    expect(offenders).toEqual([]);
  });

  it('HC-UIMO-001: package.json pins framer-motion 10.x and has no motion package', () => {
    const pkg = JSON.parse(readFileSync(PACKAGE_JSON, 'utf8')) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const deps = { ...pkg.dependencies, ...pkg.devDependencies };

    expect(deps['framer-motion']).toMatch(/^\^10\.\d+\.\d+$/);
    expect(deps).not.toHaveProperty('motion');
  });
});

describe('UI-MOTION reduced motion on the first render', () => {
  let originalMatchMedia: typeof window.matchMedia;

  beforeEach(() => {
    originalMatchMedia = window.matchMedia;
    window.matchMedia = ((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it('HC-UIMO-002: the first render of PageTransition has no transform when reduced motion is on', () => {
    // renderToStaticMarkup runs exactly one render and no effects, so it shows
    // the first render. A hook that starts false would emit the y offset here.
    const html = renderToStaticMarkup(
      <PageTransition>
        <p>Page body</p>
      </PageTransition>
    );

    expect(html).toContain('Page body');
    expect(html).not.toMatch(/translate/);
  });
});

class RenderCatcher extends Component<
  { children: ReactNode; onError: (error: unknown) => void },
  Record<string, never>
> {
  componentDidCatch(error: unknown) {
    this.props.onError(error);
  }

  render() {
    return this.props.children;
  }
}

const ROUTE_PATHS = [
  '/setup',
  '/recover',
  '/inbox',
  '/verify',
  '/trends',
  '/timeline',
  '/search',
  '/interpret',
  '/medications',
  '/medications/med-1',
  '/notifications',
  '/care-tasks',
  '/pinboards',
  '/explain',
  '/export',
  '/settings',
];

// What the route block proves: the strict provider is live, and every route
// renders under it with empty fixtures. Empty lists never reach `m.*` elements
// that sit behind data branches, so those are not exercised here. HC-UIMO-001
// (the source audit above) is the complete guard against a leftover `motion.*`.
describe('UI-MOTION every route under LazyMotion strict', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({
      token: 'test-token',
      profileId: 'profile-123',
      profileName: 'Test Profile',
      expiresIn: 3600,
    });
  });

  it('HC-UIMO-003 control: a motion.* element under MotionProvider throws, so a leftover would be caught', async () => {
    const { MotionProvider } = (await import(/* @vite-ignore */ '@/motion/MotionProvider')) as {
      MotionProvider: (props: { children: ReactNode }) => ReactNode;
    };
    const errors: unknown[] = [];

    render(
      <MotionProvider>
        <RenderCatcher onError={(error) => errors.push(error)}>
          <motion.div />
        </RenderCatcher>
      </MotionProvider>
    );

    expect(errors.map((error) => String(error)).join('\n')).toMatch(/motion` component within a `LazyMotion`/);
  });

  it.each(ROUTE_PATHS)(
    'HC-UIMO-003: %s renders under MotionProvider without throwing',
    async (path) => {
      // Loaded at run time so a missing module fails this id alone, not the file.
      const providerModule = '@/motion/MotionProvider';
      const { MotionProvider } = (await import(/* @vite-ignore */ providerModule)) as {
        MotionProvider: (props: { children: ReactNode }) => ReactNode;
      };
      window.history.pushState({}, '', path);
      const errors: unknown[] = [];
      // The route boundary catches a render error, so RenderCatcher never sees
      // it. The boundary's fallback and its log line show that it did.
      const consoleError = vi.spyOn(console, 'error');
      onTestFinished(() => consoleError.mockRestore());

      const { container, unmount } = render(
        <MotionProvider>
          <RenderCatcher onError={(error) => errors.push(error)}>
            <App />
          </RenderCatcher>
        </MotionProvider>
      );

      // Let LazyMotion load its features and any lazy route chunk resolve.
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 50));
      });
      await waitFor(
        () => {
          if (errors.length === 0) {
            expect(container.textContent ?? '').not.toContain('Loading page...');
          }
        },
        { timeout: 20000 }
      );

      expect(errors.map((error) => String(error))).toEqual([]);
      expect(container.textContent ?? '').not.toContain('This page hit a problem');
      const routeFailures = consoleError.mock.calls.filter((args) => /Route render failed/.test(String(args[0])));
      expect(routeFailures).toEqual([]);
      expect(container.innerHTML).not.toBe('');
      unmount();
    },
    30000
  );
});
