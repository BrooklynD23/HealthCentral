import { useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { User } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { Popover } from '@/components/ui/Popover';
import { useLockProfile } from '@/services/profiles';
import { useAuthStore } from '@/stores/authStore';

/**
 * The profile trigger (plan §3.2, §3.4). It holds Settings, then "Lock now"
 * (SESSION-REENTRY Task 3, plan §8.2): Lock now locks the profile, clears the
 * session the way logout does, and lands on the unlock card at /setup. About
 * waits for UI-ABOUT.
 */
export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const profileId = useAuthStore((state) => state.profileId);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const lock = useLockProfile();
  // A ref as well as lock.isPending: two clicks in one tick can both read isPending as false.
  const lockInFlight = useRef(false);

  const lockNow = async () => {
    if (!profileId || lockInFlight.current) return;
    lockInFlight.current = true;
    try {
      await lock.mutateAsync(profileId);
    } catch {
      // Clear the session even when the server cannot be reached, as useLogout does.
    } finally {
      lockInFlight.current = false;
      clearAuth();
      queryClient.clear();
      setOpen(false);
      // Replace, not push, as ProtectedRoute does: Back must not return to the locked page.
      navigate('/setup', { replace: true });
    }
  };

  return (
    <Popover
      open={open}
      onOpenChange={setOpen}
      label="Profile menu"
      align="end"
      trigger={
        <IconButton
          variant="secondary"
          aria-label="Profile and settings"
          title="Profile and settings"
          className="h-10 w-10 rounded-xl border-border"
        >
          <User className="h-5 w-5" aria-hidden="true" />
        </IconButton>
      }
    >
      <div className="flex flex-col gap-1">
        <Link
          to="/settings"
          onClick={() => setOpen(false)}
          className="flex min-h-target items-center rounded-lg px-3 text-sm font-medium text-ink hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden"
        >
          Settings
        </Link>
        <button
          type="button"
          onClick={() => void lockNow()}
          disabled={!profileId || lock.isPending}
          className="flex min-h-target w-full items-center rounded-lg px-3 text-left text-sm font-medium text-ink hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden disabled:cursor-not-allowed disabled:opacity-60"
        >
          Lock now
        </button>
      </div>
    </Popover>
  );
}
