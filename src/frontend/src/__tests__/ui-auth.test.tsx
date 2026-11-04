/**
 * UI-PG-AUTH (plan section 7.8): the setup, unlock and recovery screens.
 *
 * - HC-UIAUTH-001: a fixed field's error disappears on the next valid input.
 * - HC-UIAUTH-002: no progress step that is not tied to the real request.
 * - HC-UIAUTH-003: the Lift on unlock (unit part: the detached ghost holds no secret).
 * - HC-UIAUTH-004: the recovery code renders in 4-character groups.
 * - HC-UIAUTH-005: field errors sit outside the S1 wrapper and carry data-t0.
 *
 * Presentation only (L0 AUTH GUARD): these tests never change what is sent, kept or validated.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileSetup } from '@/pages/ProfileSetup';
import { RecoverProfile } from '@/pages/RecoverProfile';
import { RecoveryCodeCard } from '@/components/profile/RecoveryCodeCard';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { duration, ease } from '@/motion/tokens';

vi.mock('@/services/api', () => ({
  apiPost: vi.fn(),
  apiGet: vi.fn(),
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

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const PASSWORD = 'SecurePass123';
const CODE = 'H4K2-9QMR-7TXB-3VWZ-5CDF-8GHJ-2NPS-6KTV';
const created = {
  access_token: 'test-jwt-token-123',
  token_type: 'bearer',
  expires_in: 3600,
  profile_id: 'profile-uuid-123',
  profile_name: 'My Health Profile',
  recovery_code: CODE,
};
const PROFILE = {
  id: 'profile-uuid-123',
  display_name: 'Maria Lopez',
  is_locked: false,
  created_at: '2026-01-01T00:00:00Z',
  last_accessed_at: null,
  has_recovery_code: true,
};

function renderPage(ui: React.ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

function setReducedMotion(reduced: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: reduced && query.includes('prefers-reduced-motion'),
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

/** An element is "moving" if it, or an ancestor, carries an inline opacity or transform (framer-motion's way). */
function animatedAncestor(el: Element): Element | null {
  for (let node: Element | null = el; node && node !== document.body; node = node.parentElement) {
    const style = (node as HTMLElement).style;
    if (style && (style.opacity !== '' || style.transform !== '')) return node;
  }
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  sessionStorage.clear();
  useAuthStore.getState().clearAuth();
  setReducedMotion(false);
  vi.mocked(api.apiGet).mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
  delete (Element.prototype as { animate?: unknown }).animate;
  document.querySelectorAll('[data-lift-ghost]').forEach((n) => n.remove());
});

describe('HC-UIAUTH-001: a fixed field error disappears on the next valid input', () => {
  it('clears "Name is required" once the name has text, and the password error once the password is valid', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);

    await user.click(await screen.findByRole('button', { name: /create your profile/i }));
    expect(screen.getByText('Name is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();

    await user.type(screen.getByLabelText('Profile Name'), 'M');
    expect(screen.queryByText('Name is required')).not.toBeInTheDocument();
    // The other field's error is untouched by the first field's fix.
    expect(screen.getByText('Password is required')).toBeInTheDocument();

    // 'Password is required' is no longer true once anything is typed; the live rule list takes over.
    await user.type(screen.getByPlaceholderText('Create a secure password'), 'Secure1');
    expect(screen.queryByText('Password is required')).not.toBeInTheDocument();
    expect(screen.getByText('At least 8 characters')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(api.apiPost).not.toHaveBeenCalled();
  });

  it('replaces nothing on change: an invalid edit never adds an error before submit', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);

    const name = await screen.findByLabelText('Profile Name');
    await user.type(name, 'Ab');
    await user.clear(name);
    await user.type(screen.getByPlaceholderText('Create a secure password'), 'weak');
    expect(screen.queryByText('Name is required')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('drops the submit-time rule list as soon as the password is edited, so no met rule stays listed', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);

    await user.type(await screen.findByLabelText('Profile Name'), 'Maria');
    await user.type(screen.getByPlaceholderText('Create a secure password'), 'weakpass');
    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/at least one uppercase letter/i);

    await user.type(screen.getByPlaceholderText('Create a secure password'), 'A');
    // The stale list (which still names the uppercase rule) is gone. The live hints list only what is unmet.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText('At least one uppercase letter')).not.toBeInTheDocument();
    expect(screen.getByText('At least one digit')).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText('Create a secure password'), '1');
    expect(screen.queryByText('At least one digit')).not.toBeInTheDocument();
    // Submit stays authoritative: nothing was added on change.
    expect(api.apiPost).not.toHaveBeenCalled();
  });

  it('clears the unlock "Enter your password" error once something is typed, and keeps a server error while typing', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    renderPage(<ProfileSetup />);
    const field = await screen.findByLabelText('Unlock password');
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter your password');
    expect(field).toHaveAttribute('aria-invalid', 'true');

    await user.type(field, 'x');
    expect(screen.queryByText('Enter your password')).not.toBeInTheDocument();
    expect(field).not.toHaveAttribute('aria-invalid');

    // A message from the server is not about the empty field: typing does not clear it.
    vi.mocked(api.apiPost).mockRejectedValueOnce(new api.ApiError(429, 'Too Many Requests', 'Slow down'));
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts');
    await user.type(field, 'y');
    expect(screen.getByRole('alert')).toHaveTextContent('Too many attempts');
  });
});

describe('HC-UIAUTH-002: no progress that is not tied to the real request', () => {
  it('shows no fake step labels, shows the loading label only while the POST is pending, and starts no timer', async () => {
    const user = userEvent.setup({ delay: null });
    let resolvePost: (value: unknown) => void = () => undefined;
    vi.mocked(api.apiPost).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      })
    );
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);

    // Every setTimeout the flow makes, with the frame that called it (React Query's own timers are not ours).
    const realSetTimeout = globalThis.setTimeout;
    const calls: { delay: unknown; stack: string }[] = [];
    const spy = vi.spyOn(globalThis, 'setTimeout').mockImplementation(((
      fn: TimerHandler,
      delay?: number,
      ...rest: unknown[]
    ) => {
      // The first frame that is not the spy machinery is whoever called setTimeout.
      const caller =
        (new Error().stack ?? '')
          .split('\n')
          .slice(1)
          .find((line) => !/tinyspy|@vitest|ui-auth\.test/.test(line)) ?? '';
      calls.push({ delay, stack: caller });
      return realSetTimeout(fn as () => void, delay, ...rest);
    }) as typeof setTimeout);

    expect(screen.queryByText('Creating your profile…')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /create your profile/i }));

    // Pending: the real request is in flight, so the loading label is on the button.
    const pending = await screen.findByRole('button', { name: /creating your profile…/i });
    expect(pending).toBeDisabled();
    expect(api.apiPost).toHaveBeenCalledTimes(1);
    for (const fake of ['Creating secure vault...', 'Setting up encryption...', 'Profile ready!']) {
      expect(screen.queryByText(fake)).not.toBeInTheDocument();
    }

    resolvePost(created);
    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(CODE);
    expect(screen.queryByText('Creating your profile…')).not.toBeInTheDocument();
    for (const fake of ['Creating secure vault...', 'Setting up encryption...', 'Profile ready!']) {
      expect(screen.queryByText(fake)).not.toBeInTheDocument();
    }

    spy.mockRestore();
    const fromFlow = calls.filter(
      (c) => c.delay === 500 || /pages\/ProfileSetup/.test(c.stack)
    );
    expect(fromFlow).toEqual([]);
  });

  it('while the POST is pending the recovery link cannot be used (the one-time code would be lost) and the fields are locked', async () => {
    const user = userEvent.setup({ delay: null });
    let resolvePost: (value: unknown) => void = () => undefined;
    vi.mocked(api.apiPost).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      })
    );
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    const link = screen.getByRole('link', { name: 'Use your recovery code' });
    expect(link.closest('p')).not.toHaveClass('invisible');

    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    await screen.findByRole('button', { name: /creating your profile…/i });

    // visibility:hidden takes the link out of the tab order and out of reach of the pointer; the line keeps its
    // height, so nothing shifts.
    expect(link.closest('p')).toHaveClass('invisible');
    expect(screen.getByLabelText('Profile Name')).toBeDisabled();
    expect(screen.getByPlaceholderText('Create a secure password')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Show password' })).toBeDisabled();

    resolvePost(created);
    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(CODE);
  });

  it('while the POST is pending the button is disabled and busy with its label and no spinner (G5: a spinner rotates under reduced motion)', async () => {
    const user = userEvent.setup({ delay: null });
    let resolvePost: (value: unknown) => void = () => undefined;
    vi.mocked(api.apiPost).mockReturnValueOnce(
      new Promise((resolve) => {
        resolvePost = resolve;
      })
    );
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /create your profile/i }));

    const pending = await screen.findByRole('button', { name: /creating your profile…/i });
    expect(pending).toBeDisabled();
    expect(pending).toHaveAttribute('aria-busy', 'true');
    // No element in the page spins: Tailwind's animate-spin is a transform that reduced motion does not stop.
    expect(document.querySelector('[class*="animate-spin"]')).toBeNull();

    resolvePost(created);
    expect(await screen.findByTestId('recovery-code')).toHaveTextContent(CODE);
  });

  it('a revealed password is hidden again while the POST is pending, and shown again if the request fails', async () => {
    const user = userEvent.setup({ delay: null });
    let rejectPost: (reason: unknown) => void = () => undefined;
    vi.mocked(api.apiPost).mockReturnValueOnce(
      new Promise((_resolve, reject) => {
        rejectPost = reject;
      })
    );
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    const field = screen.getByPlaceholderText('Create a secure password');
    await user.type(field, PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Show password' }));
    expect(field).toHaveAttribute('type', 'text');

    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    await screen.findByRole('button', { name: /creating your profile…/i });
    // The toggle that would hide it is disabled for the whole request, so the field must not stay readable.
    expect(field).toHaveAttribute('type', 'password');

    rejectPost(new Error('Server unavailable'));
    await screen.findByText(/server unavailable/i);
    // The user's choice survives: the field is as they left it.
    expect(field).toHaveAttribute('type', 'text');
  });

  it('a failed request puts the link and the fields back, and the failure is a data-t0 alert', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Server unavailable'));
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /create your profile/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/failed to create profile/i);
    expect(alert).toHaveTextContent(/server unavailable/i);
    expect(alert).toHaveAttribute('data-t0');
    expect(animatedAncestor(alert)).toBeNull();
    expect(screen.getByRole('link', { name: 'Use your recovery code' }).closest('p')).not.toHaveClass('invisible');
    expect(screen.getByLabelText('Profile Name')).toBeEnabled();
    expect(screen.getByPlaceholderText('Create a secure password')).toBeEnabled();
  });

  it('the loading label goes away when the request fails, and the error shows', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Server unavailable'));
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    expect(await screen.findByText(/server unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText('Creating your profile…')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create your profile/i })).toBeEnabled();
  });

  it('the unlinked Terms of Service sentence is gone and the local-storage sentence stays', async () => {
    renderPage(<ProfileSetup />);
    expect(await screen.findByLabelText('Profile Name')).toBeInTheDocument();
    expect(screen.queryByText(/terms of service/i)).not.toBeInTheDocument();
    expect(screen.getByText(/your data is stored locally and never uploaded/i)).toBeInTheDocument();
  });
});

describe('HC-UIAUTH-003: the Lift on unlock holds no secret', () => {
  /** Stubs Element.animate (jsdom has none) and records only the calls made on the Lift ghost. */
  function fakeAnimate() {
    const ghostCalls: {
      keyframes: Record<string, string>[];
      options: KeyframeAnimationOptions;
      animation: { onfinish: (() => void) | null; oncancel: (() => void) | null };
      order: number;
    }[] = [];
    let counter = 0;
    (Element.prototype as unknown as { animate: unknown }).animate = vi.fn(function (
      this: Element,
      keyframes: Record<string, string>[],
      options: KeyframeAnimationOptions
    ) {
      const animation = { onfinish: null, oncancel: null, cancel: vi.fn(), finished: new Promise(() => undefined) };
      counter += 1;
      if (this.hasAttribute('data-lift-ghost')) {
        ghostCalls.push({ keyframes, options, animation, order: counter });
      }
      return animation;
    });
    return ghostCalls;
  }

  /**
   * Unlocks with navigate mocked (the page stays mounted), then unmounts the page the way the route swap does (the cache clear empties the profile list earlier, which must not start it):
   * the Lift starts when the page leaves the document.
   */
  async function unlock(user: ReturnType<typeof userEvent.setup>, options: { refetchPends?: boolean } = {}) {
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    if (options.refetchPends) {
      // After the cache clear the list is fetched again, with the new token: until that answers there is no data
      // (the real route commit waits on a lazy chunk for about as long).
      vi.mocked(api.apiGet).mockReset();
      vi.mocked(api.apiGet).mockResolvedValueOnce([PROFILE]).mockReturnValue(new Promise(() => undefined));
    }
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'unlocked-token-456',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: PROFILE.id,
      profile_name: PROFILE.display_name,
    });
    const view = renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Unlock password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/inbox'));
    return view;
  }

  it('starts the Lift when the page leaves, with navigate unchanged: 240 ms, 8 px up and a fade', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    const view = await unlock(user);
    // Navigate ran at once and the page is still there: the Lift waits for the page to leave.
    expect(lifts).toHaveLength(0);
    view.unmount();
    await waitFor(() => expect(lifts).toHaveLength(1));
    const { keyframes, options } = lifts[0];
    expect(options.duration).toBe(240);
    const last = keyframes[keyframes.length - 1];
    expect(last.opacity).toBe('0');
    expect(last.transform).toBe('translateY(-8px)');
    // Navigate is not delayed and runs once.
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });

  it('keeps the unlock panel on screen, inert, after the cache clear, until the page leaves', async () => {
    const user = userEvent.setup({ delay: null });
    fakeAnimate();
    await unlock(user, { refetchPends: true });
    // Navigate has run and queryClient.clear() has emptied the profile list. The route has not committed yet
    // (here it never does): the card the user was looking at must not blank out in between.
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.length).toBeGreaterThanOrEqual(2));
    await new Promise((resolve) => setTimeout(resolve, 50));
    const heading = screen.getByRole('heading', { name: 'Unlock your profile' });
    expect(heading).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Maria Lopez' })).toBeInTheDocument();
    // It is still a form with a password field, so it must not take input or focus any more.
    expect(heading.closest('[inert]')).not.toBeNull();
    expect(screen.getByLabelText('Unlock password')).toHaveValue('');
  });

  it('keeps the create card and the footer as they were, and locks the whole page, after the cache clear', async () => {
    const user = userEvent.setup({ delay: null });
    fakeAnimate();
    await unlock(user, { refetchPends: true });
    await waitFor(() => expect(vi.mocked(api.apiGet).mock.calls.length).toBeGreaterThanOrEqual(2));
    await new Promise((resolve) => setTimeout(resolve, 50));
    // The page must not collapse under the ghost (a scroll clamp would move the panel away from the rect it
    // copied), and the create card must not turn into the form (it would play S1 under the Lift).
    const createButton = screen.getByRole('button', { name: 'Create a new profile' });
    expect(screen.queryByRole('heading', { name: 'Set up your profile' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Profile Name')).not.toBeInTheDocument();
    expect(screen.getByText(/your data is stored locally and never uploaded/i)).toBeInTheDocument();
    // The whole page is inert, so the create card and its button take no input either.
    expect(createButton.closest('[inert]')).not.toBeNull();
    expect(createButton.closest('[inert]')).toBe(document.querySelector('[data-setup-page]'));
  });

  it('the ghost sits below the Safety Rail (z-30), the tab bar and the top bar (z-40), uses the plain card border and no shadow, and the motion tokens', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    const view = await unlock(user);
    view.unmount();
    await waitFor(() => expect(lifts).toHaveLength(1));
    const ghost = document.querySelector('[data-lift-ghost]') as HTMLElement;
    expect(Number(ghost.style.zIndex)).toBeLessThan(30);
    expect(Number(ghost.style.zIndex)).toBeGreaterThan(0);
    expect(ghost.style.boxShadow).toBe('');
    expect(ghost.className).toMatch(/\bborder\b/);
    expect(ghost.className).toMatch(/border-black\/4/);
    expect(ghost.className).toMatch(/bg-surface-elevated/);
    expect(lifts[0].options.duration).toBe(duration.md * 1000);
    expect(lifts[0].options.easing).toBe(`cubic-bezier(${ease.out.join(', ')})`);
  });

  it('a failure while drawing the ghost leaves nothing behind and throws nothing', async () => {
    const user = userEvent.setup({ delay: null });
    (Element.prototype as unknown as { animate: unknown }).animate = () => {
      throw new Error('animate failed');
    };
    const view = await unlock(user);
    view.unmount();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(document.querySelector('[data-lift-ghost]')).toBeNull();
  });

  it('under reduced motion the Lift is opacity only, 150 ms', async () => {
    setReducedMotion(true);
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    const view = await unlock(user);
    view.unmount();
    await waitFor(() => expect(lifts).toHaveLength(1));
    const { keyframes, options } = lifts[0];
    expect(options.duration).toBe(duration.hover * 1000);
    for (const frame of keyframes) expect(frame).not.toHaveProperty('transform');
    expect(keyframes[keyframes.length - 1].opacity).toBe('0');
  });

  it('the ghost is inert, has no form control, and no attribute or value in the document holds the password', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    const view = await unlock(user);
    view.unmount();
    await waitFor(() => expect(lifts).toHaveLength(1));

    const ghost = document.querySelector('[data-lift-ghost]') as HTMLElement | null;
    expect(ghost, 'the ghost is in the document while the Lift runs').not.toBeNull();
    expect(ghost!.getAttribute('aria-hidden')).toBe('true');
    expect(ghost!.style.pointerEvents).toBe('none');
    expect(ghost!.querySelector('input, select, textarea, button')).toBeNull();
    expect(ghost!.textContent).toBe('');

    const holders: string[] = [];
    for (const el of Array.from(document.querySelectorAll('*'))) {
      for (const attr of Array.from(el.attributes)) {
        if (attr.value.includes(PASSWORD)) holders.push(`${el.tagName}[${attr.name}]`);
      }
      const value = (el as HTMLInputElement).value;
      if (typeof value === 'string' && value.includes(PASSWORD)) holders.push(`${el.tagName}.value`);
    }
    expect(holders).toEqual([]);
    expect(document.documentElement.outerHTML).not.toContain(PASSWORD);

    // It removes itself when the animation ends or is cancelled.
    lifts[0].animation.onfinish?.();
    expect(document.querySelector('[data-lift-ghost]')).toBeNull();
  });

  it('a wrong password starts no Lift', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockRejectedValueOnce(new api.ApiError(401, 'Unauthorized', 'Invalid'));
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Unlock password'), 'WrongPass999');
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect password');
    expect(lifts).toHaveLength(0);
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

describe('HC-UIAUTH-004: the recovery code renders in 4-character groups', () => {
  it('keeps textContent equal to the code and wraps only between groups', () => {
    render(<RecoveryCodeCard code={CODE} onAcknowledge={() => undefined} />);
    const block = screen.getByTestId('recovery-code');
    expect(block.textContent).toBe(CODE);

    const groups = Array.from(block.querySelectorAll('[data-code-group]'));
    expect(groups.map((g) => g.textContent)).toEqual(CODE.split('-'));
    for (const group of groups) {
      expect(group.textContent).toHaveLength(4);
      // A group is one unbreakable box.
      expect(group.className).toMatch(/\binline-block\b/);
      expect(group.className).toMatch(/\bwhitespace-nowrap\b/);
    }
    // break-all is what split a group across lines.
    expect(block.className).not.toMatch(/break-all/);
  });

  it('marks the code and its warning data-t0, with the warning in the caution token', () => {
    render(<RecoveryCodeCard code={CODE} onAcknowledge={() => undefined} />);
    expect(screen.getByTestId('recovery-code')).toHaveAttribute('data-t0');
    const warning = screen.getByText(/cannot be recovered by anyone/i);
    expect(warning).toHaveAttribute('data-t0');
    expect(warning.className).toMatch(/text-status-caution/);
    expect(warning.className).not.toMatch(/text-status-attention/);
  });

  it('copies the code exactly as given', async () => {
    const user = userEvent.setup({ delay: null });
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    render(<RecoveryCodeCard code={CODE} onAcknowledge={() => undefined} />);
    await user.click(screen.getByRole('button', { name: 'Copy' }));
    expect(writeText).toHaveBeenCalledWith(CODE);
  });

  it('has no entrance: no ancestor of the code carries an inline opacity or transform', () => {
    render(<RecoveryCodeCard code={CODE} onAcknowledge={() => undefined} />);
    expect(animatedAncestor(screen.getByTestId('recovery-code'))).toBeNull();
  });
});

describe('HC-UIAUTH-005: errors sit outside the S1 wrapper and carry data-t0', () => {
  it('field errors are data-t0 alerts with no moving ancestor, linked to their inputs', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);
    await user.click(await screen.findByRole('button', { name: /create your profile/i }));

    const alerts = screen.getAllByRole('alert');
    expect(alerts).toHaveLength(2);
    for (const alert of alerts) {
      expect(alert).toHaveAttribute('data-t0');
      expect(animatedAncestor(alert), 'no inline opacity/transform on or above the error').toBeNull();
    }

    const name = screen.getByLabelText('Profile Name');
    const password = screen.getByPlaceholderText('Create a secure password');
    expect(name).toHaveAttribute('aria-invalid', 'true');
    expect(password).toHaveAttribute('aria-invalid', 'true');
    expect(document.getElementById(name.getAttribute('aria-describedby')!)).toHaveTextContent('Name is required');
    expect(document.getElementById(password.getAttribute('aria-describedby')!)).toHaveTextContent(
      'Password is required'
    );
  });

  it('the S1 wrapper holds the label-and-input groups, and the errors that appear after a submit are not inside it', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);
    const name = await screen.findByLabelText('Profile Name');
    // The S1 groups move (inline opacity/transform); the inputs sit inside them.
    expect(animatedAncestor(name)).not.toBeNull();

    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    const alerts = screen.getAllByRole('alert');
    expect(alerts).toHaveLength(2);
    for (const alert of alerts) {
      expect(animatedAncestor(alert)).toBeNull();
      expect(animatedAncestor(name)!.contains(alert), 'an error inside the moving wrapper').toBe(false);
    }
  });

  it('the unlock error is a data-t0 alert with no moving ancestor', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockRejectedValueOnce(new api.ApiError(401, 'Unauthorized', 'Invalid'));
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Unlock password'), 'WrongPass999');
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveAttribute('data-t0');
    expect(animatedAncestor(alert)).toBeNull();
  });

  it('the recovery-code step has no S1 and marks the code and warning data-t0', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiPost).mockResolvedValueOnce(created);
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Profile Name'), 'My Health Profile');
    await user.type(screen.getByPlaceholderText('Create a secure password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    const code = await screen.findByTestId('recovery-code');
    expect(code).toHaveAttribute('data-t0');
    expect(animatedAncestor(code)).toBeNull();
    expect(document.querySelectorAll('[data-t0]').length).toBeGreaterThanOrEqual(2);
    const t0 = Array.from(document.querySelectorAll('[data-t0]'));
    expect(t0.some((el) => /cannot be recovered/i.test(el.textContent ?? ''))).toBe(true);
  });

  it('RecoverProfile: the error text is a data-t0 alert; #recover-code is the Input primitive', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('That recovery code is not valid.'));
    renderPage(<RecoverProfile />);

    const code = await screen.findByLabelText('Recovery code');
    expect(code).toHaveAttribute('id', 'recover-code');
    expect(code).toHaveAttribute('placeholder', 'XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX');
    // The Input primitive's field border token.
    expect(code.className).toContain('--line-strong');

    await user.selectOptions(screen.getByLabelText('Profile'), PROFILE.id);
    await user.type(code, 'AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GGGG-HHHH');
    await user.type(screen.getByLabelText('New password'), 'NewPass123');
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/not valid/i);
    expect(alert).toHaveAttribute('data-t0');
    expect(within(document.body).getAllByRole('alert')).toHaveLength(1);
  });
});

describe('RecoverProfile copy and field state', () => {
  it('shows the intro with the form and not above the "no recovery code" notice', async () => {
    vi.mocked(api.apiGet).mockResolvedValue([{ ...PROFILE, has_recovery_code: false }]);
    const { unmount } = renderPage(<RecoverProfile />);
    expect(await screen.findByText(/none of the profiles on this device has a recovery code/i)).toBeInTheDocument();
    expect(screen.queryByText(/choose a new password/i)).not.toBeInTheDocument();
    unmount();

    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    renderPage(<RecoverProfile />);
    await screen.findByLabelText('Recovery code');
    // True for a code that was rotated or replaced in Settings too, so it does not say when it was saved.
    expect(screen.getByText('Use your saved recovery code to choose a new password.')).toBeInTheDocument();
    expect(screen.queryByText(/when you made this profile/i)).not.toBeInTheDocument();
  });

  it('a failed request does not mark the recovery code field invalid (the failure may be the password, a limit or the network)', async () => {
    const user = userEvent.setup({ delay: null });
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockRejectedValueOnce(new Error('Password must contain an uppercase letter'));
    renderPage(<RecoverProfile />);
    const code = await screen.findByLabelText('Recovery code');
    await user.selectOptions(screen.getByLabelText('Profile'), PROFILE.id);
    await user.type(code, 'AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GGGG-HHHH');
    await user.type(screen.getByLabelText('New password'), 'newpass123');
    await user.click(screen.getByRole('button', { name: /unlock my records/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/uppercase/i);
    expect(code).not.toHaveAttribute('aria-invalid');
  });
});
