import { useState } from 'react';
import { Link } from 'react-router-dom';
import { User } from 'lucide-react';
import { IconButton } from '@/components/ui/IconButton';
import { Popover } from '@/components/ui/Popover';

/**
 * The profile trigger (plan §3.2, §3.4). It holds Settings only: About waits for
 * UI-ABOUT, and "Lock now" is SESSION-REENTRY Task 3, a separate row (plan §8.2).
 */
export function ProfileMenu() {
  const [open, setOpen] = useState(false);

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
      <Link
        to="/settings"
        onClick={() => setOpen(false)}
        className="flex min-h-target items-center rounded-lg px-3 text-sm font-medium text-ink hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden"
      >
        Settings
      </Link>
    </Popover>
  );
}
