/**
 * ProfileSetup Page
 *
 * Sprint 1 - S1-FE-001: Profile creation with password field.
 *
 * Creates a new profile with password authentication.
 * Stores the returned JWT token in authStore.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Heart,
  Lock,
  Shield,
  Database,
  ArrowRight,
  Check,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Button, Card, CardContent, Input } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useCreateProfile } from '@/services';
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

export function ProfileSetup() {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [isCreating, setIsCreating] = useState(false);
  const [step, setStep] = useState(0);
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
    setStep(0);

    try {
      // Step 1: Creating vault
      await new Promise((r) => setTimeout(r, 500));
      setStep(1);

      // Step 2: Setting up encryption - actual API call
      const created = await createProfile.mutateAsync({
        display_name: displayName.trim() || 'My Health Profile',
        password,
      });
      // RCC-2: the password has done its job. Detach the mutation (gcTime 0
      // then removes it, with the password and code) and clear the field.
      createProfile.reset();
      setPassword('');

      setStep(2);
      await new Promise((r) => setTimeout(r, 500));

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
      setStep(0);
    }
  };

  // Password strength indicator
  const passwordValidation = validatePassword(password);
  const showPasswordHints = password.length > 0 && !passwordValidation.isValid;

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: prefersReducedMotion ? 0 : 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  };

  if (recoveryCode) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <RecoveryCodeCard
            code={recoveryCode}
            acknowledgeLabel="Continue to my records"
            onAcknowledge={() => navigate('/inbox')}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-1/4 -right-1/4 w-1/2 h-1/2 bg-accent/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-1/4 -left-1/4 w-1/2 h-1/2 bg-accent/3 rounded-full blur-3xl" />
      </div>

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="w-full max-w-lg relative z-10"
      >
        {restoreNotice && (
          <motion.div variants={itemVariants} className="mb-6">
            <div
              role="status"
              className="rounded-lg border border-status-info/30 bg-status-info-subtle px-4 py-3 text-sm text-ink"
            >
              {restoreNotice}
            </div>
          </motion.div>
        )}

        <motion.div variants={itemVariants} className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-accent/80 shadow-card mb-6">
            <Heart className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
          <h1 className="font-display text-3xl font-semibold text-ink tracking-tight mb-3">
            Welcome to Asclexis
          </h1>
          <p className="text-ink-secondary text-lg">
            Your personal medical results companion.
            <br />
            Private, offline-first, and always grounded.
          </p>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="mb-6">
            <CardContent className="p-6">
              <div className="space-y-4">
                {features.map((feature, index) => (
                  <motion.div
                    key={feature.title}
                    initial={prefersReducedMotion ? {} : { opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + index * 0.1 }}
                    className="flex items-start gap-4"
                  >
                    <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-accent-subtle flex items-center justify-center">
                      <feature.icon className="w-5 h-5 text-accent" />
                    </div>
                    <div>
                      <h3 className="font-medium text-ink">{feature.title}</h3>
                      <p className="text-sm text-ink-secondary">
                        {feature.description}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          {!isCreating ? (
            <Card>
              <CardContent className="p-6 space-y-4">
                <Input
                  label="Profile Name"
                  placeholder="My Health Profile"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  error={formErrors.displayName}
                  autoComplete="name"
                />

                <div className="relative">
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    label="Password"
                    placeholder="Create a secure password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    error={formErrors.password}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-[38px] text-ink-tertiary hover:text-ink transition-colors"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>

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
                  disabled={createProfile.isPending}
                >
                  Create Your Profile
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </Button>

                {/* SEC-RECOV-001: the way back in for an existing profile
                    whose password has been forgotten. */}
                <p className="mt-4 text-center text-sm text-ink-secondary">
                  Already have a profile and forgot the password?{' '}
                  <Link to="/recover" className="underline">
                    Use your recovery code
                  </Link>
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-3">
                  {[
                    'Creating secure vault...',
                    'Setting up encryption...',
                    'Profile ready!',
                  ].map((label, index) => (
                    <div
                      key={label}
                      className={cn(
                        'flex items-center gap-3 text-sm transition-opacity duration-300',
                        step >= index ? 'opacity-100' : 'opacity-40'
                      )}
                    >
                      <div
                        className={cn(
                          'w-5 h-5 rounded-full flex items-center justify-center transition-colors',
                          step > index
                            ? 'bg-status-verified text-white'
                            : step === index
                            ? 'bg-accent text-white animate-pulse'
                            : 'bg-surface-muted'
                        )}
                      >
                        {step > index && <Check className="w-3 h-3" />}
                      </div>
                      <span
                        className={cn(
                          step >= index ? 'text-ink' : 'text-ink-tertiary'
                        )}
                      >
                        {label}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {error && (
            <div className="mt-4 p-4 bg-status-critical/10 border border-status-critical/20 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-critical flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-status-critical">
                  Failed to create profile
                </p>
                <p className="text-sm text-ink-secondary mt-1">{error}</p>
              </div>
            </div>
          )}
        </motion.div>

        <motion.p
          variants={itemVariants}
          className="text-center text-xs text-ink-tertiary mt-6"
        >
          By creating a profile, you agree to our Terms of Service.
          <br />
          Your data is stored locally and never uploaded.
        </motion.p>
      </motion.div>
    </div>
  );
}
