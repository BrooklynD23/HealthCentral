/**
 * ProfileSetup Page
 *
 * Sprint 1 - S1-FE-001: Profile creation with password field.
 *
 * Creates a new profile with password authentication.
 * Stores the returned JWT token in authStore.
 */

import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Heart,
  Lock,
  Shield,
  Database,
  ArrowRight,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Button, Card, CardContent, Input } from '@/components/ui';
import { ShowcaseReveal } from '@/components/ui/ShowcaseReveal';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { duration, ease } from '@/motion/tokens';
import { cn } from '@/utils/cn';
import { useCreateProfile, useLogin, useProfiles } from '@/services';
import { ApiError } from '@/services/api';
import { takeRestoreNotice } from '@/services/backup';
import { RecoveryCodeCard } from '@/components/profile/RecoveryCodeCard';

const features = [
  {
    icon: Lock,
    title: 'Encrypted by Default',
    description: 'Your health data is encrypted locally on your device.',
  },
  {
    icon: Database,
    title: 'Offline-First',
    description: 'Access your records anytime, even without internet.',
  },
  {
    icon: Shield,
    title: 'Private & Secure',
    description: 'Data never leaves your device unless you choose to share.',
  },
];

/**
 * Password validation rules matching backend requirements.
 */
function validatePassword(password: string): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (password.length < 8) {
    errors.push('At least 8 characters');
  }
  if (!/[A-Z]/.test(password)) {
    errors.push('At least one uppercase letter');
  }
  if (!/[a-z]/.test(password)) {
    errors.push('At least one lowercase letter');
  }
  if (!/[0-9]/.test(password)) {
    errors.push('At least one digit');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * The Lift (plan section 4.1, owner UI-AUTH-SCREENS): on a successful unlock the unlock panel fades and lifts
 * 8 px in 240 ms (opacity only, 150 ms, under reduced motion) onto the shell.
 *
 * /setup sits outside the shell and navigate must stay immediate, so the panel cannot animate itself: it is
 * unmounted with the route. The panel stays on screen (inert) from the unlock until then, and a detached ghost
 * takes its place for the length of the animation: a fixed, inert, aria-hidden empty card surface with the
 * panel's rect, appended to <body> and removed when the animation ends. It holds no form control and no text, so
 * the password can never reach it. The ghost is added in the same commit that removes the page, so the shell is
 * already there beneath it. It sits at z-20, under the Safety Rail (z-30) and the bars (z-40), so it never covers
 * what must stay visible. Presentation only: it never throws and never delays navigate.
 */
function startLift(panel: HTMLElement | null, reduced: boolean): void {
  try {
    if (!panel) return;
    const rect = panel.getBoundingClientRect();

    const lift = () => {
      let ghost: HTMLDivElement | null = null;
      try {
        if (typeof Element.prototype.animate !== 'function') return;
        ghost = document.createElement('div');
        ghost.setAttribute('data-lift-ghost', '');
        ghost.setAttribute('aria-hidden', 'true');
        // The plain Card surface (border, no shadow: plan E1).
        ghost.className = 'rounded-2xl border border-black/4 bg-surface-elevated';
        Object.assign(ghost.style, {
          position: 'fixed',
          top: `${rect.top}px`,
          left: `${rect.left}px`,
          width: `${rect.width}px`,
          height: `${rect.height}px`,
          pointerEvents: 'none',
          zIndex: '20',
        });
        document.body.appendChild(ghost);
        const animation = ghost.animate(
          reduced
            ? [{ opacity: '1' }, { opacity: '0' }]
            : [
                { opacity: '1', transform: 'translateY(0)' },
                { opacity: '0', transform: 'translateY(-8px)' },
              ],
          {
            duration: (reduced ? duration.hover : duration.md) * 1000,
            easing: `cubic-bezier(${ease.out.join(', ')})`,
            fill: 'forwards',
          }
        );
        const remove = () => ghost?.remove();
        animation.onfinish = remove;
        animation.oncancel = remove;
      } catch {
        // The Lift is decoration: never leave an opaque surface behind.
        ghost?.remove();
      }
    };

    // Start when the page leaves the document. If it never does (navigation did not happen), nothing is drawn.
    const page = panel.closest('[data-setup-page]') ?? panel;
    const watcher = new MutationObserver(() => {
      if (page.isConnected) return;
      watcher.disconnect();
      lift();
    });
    watcher.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => watcher.disconnect(), 3000);
  } catch {
    // The Lift is decoration: a failure here must never reach the unlock flow.
  }
}

const UNLOCK_EMPTY_MESSAGE = 'Enter your password';

export function ProfileSetup() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const prefersReducedMotion = useReducedMotion();
  const unlockPanelRef = useRef<HTMLDivElement>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // SEC-RECOV-001: shown once, between creation and entering the app.
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);
  // FE-02: a restore ends the session deliberately. Without this the user
  // lands on "Welcome to Asclexis" and reads it as having lost the data
  // they just restored. Read once, on first render.
  const [restoreNotice] = useState<string | null>(() => takeRestoreNotice());

  // Form state
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [formErrors, setFormErrors] = useState<{
    displayName?: string;
    password?: string;
  }>({});

  const createProfile = useCreateProfile();

  // SESSION-REENTRY: an existing profile unlocks with its password through the
  // normal login endpoint. The recovery code is only for a forgotten password.
  const { data: profiles, isPending: profilesPending } = useProfiles();
  const login = useLogin();
  const hasProfiles = !!profiles && profiles.length > 0;
  const [showCreate, setShowCreate] = useState(false);
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [unlockError, setUnlockError] = useState<string | null>(null);
  // Presentation only: the profile list as it was when the unlock succeeded. queryClient.clear() empties the
  // list until it is fetched again, and the card must not blank out before the route commits (the Lift).
  const leavingProfilesRef = useRef<typeof profiles>(undefined);
  const leavingProfiles = leavingProfilesRef.current;
  const unlockProfiles = leavingProfiles ?? profiles;
  const unlockProfileId =
    unlockProfiles?.find((p) => p.id === selectedProfileId)?.id ?? unlockProfiles?.[0]?.id;

  const beginLift = () => {
    leavingProfilesRef.current = profiles;
    startLift(unlockPanelRef.current, prefersReducedMotion);
  };

  const handleUnlock = async () => {
    if (!unlockProfileId) return;
    setUnlockError(null);
    if (!unlockPassword) {
      setUnlockError(UNLOCK_EMPTY_MESSAGE);
      return;
    }
    try {
      // useLogin's onSuccess stores the token.
      await login.mutateAsync({
        profile_id: unlockProfileId,
        password: unlockPassword,
      });
      setUnlockPassword('');
      login.reset();
      // Nothing cached under a previous profile's session may be shown to
      // this one.
      queryClient.clear();
      beginLift();
      navigate('/overview');
    } catch (err) {
      login.reset();
      setUnlockPassword('');
      if (err instanceof ApiError && err.status === 401) {
        setUnlockError('Incorrect password');
      } else if (err instanceof ApiError && err.status === 429) {
        setUnlockError(
          'Too many attempts. Wait a moment, then try again.'
        );
      } else {
        setUnlockError(
          err instanceof Error && err.message
            ? err.message
            : 'Could not unlock your profile'
        );
      }
    }
  };

  const handleCreateProfile = async () => {
    // Reset errors
    setFormErrors({});
    setError(null);

    // Validate
    const errors: { displayName?: string; password?: string } = {};

    if (!displayName.trim()) {
      errors.displayName = 'Name is required';
    }

    if (!password) {
      errors.password = 'Password is required';
    } else {
      const passwordValidation = validatePassword(password);
      if (!passwordValidation.isValid) {
        errors.password = passwordValidation.errors.join(', ');
      }
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setIsCreating(true);

    try {
      const created = await createProfile.mutateAsync({
        display_name: displayName.trim() || 'My Health Profile',
        password,
      });
      // RCC-2: the password has done its job. Detach the mutation (gcTime 0
      // then removes it, with the password and code) and clear the field.
      createProfile.reset();
      setPassword('');
      // Same rule as unlock: nothing cached under a previous session may be
      // shown to the new profile.
      queryClient.clear();

      // Show the one-time recovery code before entering the app. This is the
      // only time it exists in plaintext anywhere.
      setRecoveryCode(created.recovery_code);
      setIsCreating(false);
    } catch (err) {
      createProfile.reset();
      const raw = err instanceof Error ? err.message : String(err);
      const timedOut =
        raw.toLowerCase().includes('aborted') ||
        raw.toLowerCase().includes('timeout');
      setError(
        timedOut
          ? 'Request timed out while creating your profile. Confirm the API is running and .env.local VITE_API_URL matches its port (see backend terminal or logs/asclexis.log).'
          : raw || 'Failed to create profile'
      );
      setIsCreating(false);
    }
  };

  // Password strength indicator
  const passwordValidation = validatePassword(password);
  const showPasswordHints = password.length > 0 && !passwordValidation.isValid;

  if (recoveryCode) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <RecoveryCodeCard
            code={recoveryCode}
            acknowledgeLabel="Continue to my records"
            onAcknowledge={() => navigate('/overview')}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      data-setup-page=""
      className="min-h-screen bg-surface px-4 py-10 sm:px-6 sm:py-16"
      // Once unlocked the page only waits to be lifted away: no focus, no input, in the unlock card or the create one.
      {...(leavingProfiles ? { inert: '' } : {})}
    >
      <div className="mx-auto w-full max-w-lg">
        {restoreNotice && (
          <div className="mb-6">
            <div
              role="status"
              className="rounded-xl border border-status-info/30 bg-status-info-subtle px-4 py-3 text-sm text-ink"
            >
              {restoreNotice}
            </div>
          </div>
        )}

        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-accent text-[var(--on-accent)] mb-5">
            <Heart className="w-7 h-7" strokeWidth={2} aria-hidden="true" />
          </div>
          <h1 className="font-display text-3xl font-semibold text-ink tracking-tight mb-3">
            Welcome to Asclexis
          </h1>
          <p className="text-ink-secondary text-lg">
            Your personal medical results companion.
            <br />
            Private, offline-first, and always grounded.
          </p>
        </div>

        <Card className="mb-6">
          <CardContent className="p-6">
            <div className="space-y-4">
              {features.map((feature) => (
                <div key={feature.title} className="flex items-start gap-4">
                  <div className="shrink-0 w-10 h-10 rounded-xl bg-accent-subtle flex items-center justify-center">
                    <feature.icon className="w-5 h-5 text-accent" aria-hidden="true" />
                  </div>
                  <div>
                    <h3 className="font-medium text-ink">{feature.title}</h3>
                    <p className="text-sm text-ink-secondary">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {(hasProfiles || leavingProfiles) && !isCreating && (
          <Card ref={unlockPanelRef} className="mb-6">
            <CardContent className="p-6 space-y-4">
              <h2 className="font-display text-xl font-semibold text-ink">
                Unlock your profile
              </h2>
              <form
                className="space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  void handleUnlock();
                }}
              >
                <div>
                  <label
                    htmlFor="unlock-profile"
                    className="block text-sm font-medium text-ink mb-1.5"
                  >
                    Profile
                  </label>
                  <select
                    id="unlock-profile"
                    value={unlockProfileId ?? ''}
                    onChange={(e) => setSelectedProfileId(e.target.value)}
                    className="h-11 w-full rounded-xl border border-[var(--line-strong)] bg-surface-elevated px-4 py-2 text-ink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:border-accent"
                  >
                    {unlockProfiles!.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <Input
                  id="unlock-password"
                  type="password"
                  label="Unlock password"
                  placeholder="Your password"
                  value={unlockPassword}
                  onChange={(e) => {
                    setUnlockPassword(e.target.value);
                    // The empty-field message stops being true once there is text. A server message stays.
                    if (e.target.value) {
                      setUnlockError((m) => (m === UNLOCK_EMPTY_MESSAGE ? null : m));
                    }
                  }}
                  autoComplete="current-password"
                  aria-invalid={unlockError ? true : undefined}
                  aria-describedby={unlockError ? 'unlock-password-error' : undefined}
                  className="aria-[invalid=true]:border-status-critical"
                />
                {unlockError && (
                  <p
                    id="unlock-password-error"
                    role="alert"
                    data-t0=""
                    className="text-sm text-status-critical"
                  >
                    {unlockError}
                  </p>
                )}
                <Button
                  type="submit"
                  size="lg"
                  className="w-full"
                  disabled={login.isPending}
                >
                  Unlock
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* While leaving, the create card and the footer stay as they were: a shorter page could clamp the scroll and
            move the panel away from the rect the ghost copied. */}
        {profilesPending && !leavingProfiles ? null : (
          <>
            <Card>
              <CardContent className="p-6 space-y-4">
                {(hasProfiles || leavingProfiles) && !showCreate ? (
                  <Button
                    variant="secondary"
                    size="lg"
                    className="w-full"
                    onClick={() => setShowCreate(true)}
                  >
                    Create a new profile
                  </Button>
                ) : (
                  <>
                    <h2 className="font-display text-xl font-semibold text-ink">
                      Set up your profile
                    </h2>

                    {/* S1 (UI-AUTH-SCREENS): the label-and-input groups rise in. Errors and hints are NOT in
                        here: a moving ancestor would move an error that has just appeared (HC-UIAUTH-005). */}
                    <ShowcaseReveal id="setup-create">
                      <div className="pb-4">
                        <Input
                          id="profile-name"
                          label="Profile Name"
                          placeholder="My Health Profile"
                          value={displayName}
                          onChange={(e) => {
                            const value = e.target.value;
                            setDisplayName(value);
                            // A fixed field stops showing its old error. Submit stays authoritative: nothing
                            // is added here.
                            if (value.trim()) {
                              setFormErrors((prev) =>
                                prev.displayName ? { ...prev, displayName: undefined } : prev
                              );
                            }
                          }}
                          autoComplete="name"
                          disabled={isCreating}
                          aria-invalid={formErrors.displayName ? true : undefined}
                          aria-describedby={
                            formErrors.displayName ? 'profile-name-error' : undefined
                          }
                          className="aria-[invalid=true]:border-status-critical"
                        />
                      </div>

                      <div className="relative pb-4">
                        <Input
                          id="profile-password"
                          // The toggle is disabled for the whole request, so a revealed password must not stay readable meanwhile.
                          type={showPassword && !isCreating ? 'text' : 'password'}
                          label="Password"
                          placeholder="Create a secure password"
                          value={password}
                          onChange={(e) => {
                            const value = e.target.value;
                            setPassword(value);
                            // A submit-time message ("Password is required", a rule list) goes stale on the first
                            // keystroke; the live hints below take over. Nothing is added here.
                            if (value) {
                              setFormErrors((prev) =>
                                prev.password ? { ...prev, password: undefined } : prev
                              );
                            }
                          }}
                          autoComplete="new-password"
                          disabled={isCreating}
                          aria-invalid={formErrors.password ? true : undefined}
                          aria-describedby={
                            formErrors.password ? 'profile-password-error' : undefined
                          }
                          className="aria-[invalid=true]:border-status-critical"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          disabled={isCreating}
                          className="absolute right-2 top-[32px] flex h-8 w-8 items-center justify-center rounded-lg text-ink-secondary hover:text-ink transition-colors"
                          aria-label={showPassword ? 'Hide password' : 'Show password'}
                        >
                          {showPassword ? (
                            <EyeOff className="w-5 h-5" />
                          ) : (
                            <Eye className="w-5 h-5" />
                          )}
                        </button>
                      </div>
                    </ShowcaseReveal>

                    {(formErrors.displayName || formErrors.password) && (
                      <div className="space-y-1.5">
                        {formErrors.displayName && (
                          <p
                            id="profile-name-error"
                            role="alert"
                            data-t0=""
                            className="text-sm text-status-critical"
                          >
                            {formErrors.displayName}
                          </p>
                        )}
                        {formErrors.password && (
                          <p
                            id="profile-password-error"
                            role="alert"
                            data-t0=""
                            className="text-sm text-status-critical"
                          >
                            {formErrors.password}
                          </p>
                        )}
                      </div>
                    )}

                    {showPasswordHints && (
                      <div className="text-sm text-ink-secondary space-y-1">
                        <p className="font-medium">Password requirements:</p>
                        <ul className="list-disc list-inside space-y-0.5">
                          {passwordValidation.errors.map((err) => (
                            <li key={err} className="text-status-critical">
                              {err}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <Button
                      onClick={handleCreateProfile}
                      size="lg"
                      className="w-full group"
                      disabled={createProfile.isPending || isCreating}
                      aria-busy={isCreating || undefined}
                    >
                      {isCreating ? (
                        'Creating your profile…'
                      ) : (
                        <>
                          Create Your Profile
                          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                        </>
                      )}
                    </Button>
                  </>
                )}

                {/* SEC-RECOV-001: the way back in for an existing profile
                    whose password has been forgotten. */}
                {/* Hidden (not removed) while the request runs: leaving now would lose the one-time code, and
                    removing the line would move the card. */}
                <p className={cn('text-center text-sm text-ink-secondary', isCreating && 'invisible')}>
                  Already have a profile and forgot the password?{' '}
                  <Link to="/recover" className="text-ink underline underline-offset-4">
                    Use your recovery code
                  </Link>
                </p>
              </CardContent>
            </Card>

            {error && (
              <div
                role="alert"
                data-t0=""
                className="mt-4 p-4 bg-status-critical/10 border border-status-critical/20 rounded-xl flex items-start gap-3"
              >
                <AlertCircle className="w-5 h-5 text-status-critical shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-status-critical">
                    Failed to create profile
                  </p>
                  <p className="text-sm text-ink-secondary mt-1">{error}</p>
                </div>
              </div>
            )}

            <p className="text-center text-xs text-ink-tertiary mt-6">
              Your data is stored locally and never uploaded.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
