import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Heart, Lock, Shield, Database, ArrowRight, Check, AlertCircle } from 'lucide-react';
import { Button, Card, CardContent } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useCreateProfile } from '@/services';

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

export function ProfileSetup() {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();
  const [isCreating, setIsCreating] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  
  const createProfile = useCreateProfile();

  const handleCreateProfile = async () => {
    setIsCreating(true);
    setError(null);
    setStep(0);
    
    try {
      // Step 1: Creating vault
      await new Promise((r) => setTimeout(r, 500));
      setStep(1);
      
      // Step 2: Setting up encryption - actual API call
      const profile = await createProfile.mutateAsync({
        display_name: 'My Health Profile',
      });
      
      setStep(2);
      await new Promise((r) => setTimeout(r, 500));
      
      // Store profile ID in localStorage for session persistence
      localStorage.setItem('activeProfileId', profile.id);
      
      navigate('/inbox');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create profile');
      setIsCreating(false);
      setStep(0);
    }
  };

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
        <motion.div variants={itemVariants} className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-accent/80 shadow-card mb-6">
            <Heart className="w-8 h-8 text-white" strokeWidth={2} />
          </div>
          <h1 className="font-display text-3xl font-semibold text-ink tracking-tight mb-3">
            Welcome to HealthCentral
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
            <Button
              onClick={handleCreateProfile}
              size="lg"
              className="w-full group"
            >
              Create Your Profile
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Button>
          ) : (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-3">
                  {['Creating secure vault...', 'Setting up encryption...', 'Profile ready!'].map(
                    (label, index) => (
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
                    )
                  )}
                </div>
              </CardContent>
            </Card>
          )}
          
          {error && (
            <div className="mt-4 p-4 bg-status-critical/10 border border-status-critical/20 rounded-xl flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-status-critical flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-status-critical">Failed to create profile</p>
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
