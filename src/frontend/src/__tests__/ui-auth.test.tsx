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

    await user.type(screen.getByPlaceholderText('Create a secure password'), 'Secure1');
    // Still not valid (7 characters): the error stays until the rule is met.
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText('Create a secure password'), 'x');
    expect(screen.queryByText('Password is required')).not.toBeInTheDocument();
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

  it('keeps the password error while the rules are unmet after a submit', async () => {
    const user = userEvent.setup({ delay: null });
    renderPage(<ProfileSetup />);

    await user.type(await screen.findByLabelText('Profile Name'), 'Maria');
    await user.type(screen.getByPlaceholderText('Create a secure password'), 'weakpass');
    await user.click(screen.getByRole('button', { name: /create your profile/i }));
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/at least one uppercase letter/i);

    await user.type(screen.getByPlaceholderText('Create a secure password'), 'A');
    // Uppercase met, digit still missing: Submit stays authoritative, the error is not re-derived.
    expect(screen.getByRole('alert')).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText('Create a secure password'), '1');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
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

  async function unlock(user: ReturnType<typeof userEvent.setup>) {
    vi.mocked(api.apiGet).mockResolvedValue([PROFILE]);
    vi.mocked(api.apiPost).mockResolvedValueOnce({
      access_token: 'unlocked-token-456',
      token_type: 'bearer',
      expires_in: 3600,
      profile_id: PROFILE.id,
      profile_name: PROFILE.display_name,
    });
    renderPage(<ProfileSetup />);
    await user.type(await screen.findByLabelText('Unlock password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: /^unlock$/i }));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/inbox'));
  }

  it('starts the Lift right before navigate: 240 ms, 8 px up and a fade', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    await unlock(user);

    expect(lifts).toHaveLength(1);
    const { keyframes, options } = lifts[0];
    expect(options.duration).toBe(240);
    const last = keyframes[keyframes.length - 1];
    expect(last.opacity).toBe('0');
    expect(last.transform).toBe('translateY(-8px)');
    // Navigate is not delayed and runs once; the Lift was started by then.
    expect(mockNavigate).toHaveBeenCalledTimes(1);
  });

  it('under reduced motion the Lift is opacity only, 150 ms', async () => {
    setReducedMotion(true);
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    await unlock(user);

    expect(lifts).toHaveLength(1);
    const { keyframes, options } = lifts[0];
    expect(options.duration).toBe(150);
    for (const frame of keyframes) expect(frame).not.toHaveProperty('transform');
    expect(keyframes[keyframes.length - 1].opacity).toBe('0');
  });

  it('the ghost is inert, has no form control, and no attribute or value in the document holds the password', async () => {
    const user = userEvent.setup({ delay: null });
    const lifts = fakeAnimate();
    await unlock(user);

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

  it('the S1 wrapper holds the label-and-input groups and the field errors are not inside it', async () => {
    renderPage(<ProfileSetup />);
    const name = await screen.findByLabelText('Profile Name');
    // The S1 groups move (inline opacity/transform); the inputs sit inside them.
    expect(animatedAncestor(name)).not.toBeNull();
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
