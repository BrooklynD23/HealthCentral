import { useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Sheet } from '@/components/ui/Sheet';
import { navGroups } from './navConfig';

/**
 * The More sheet (plan §3.2): a bottom sheet (M5) that lists every group as 52 px
 * tiles, so every destination is reachable from it. Escape closes it and the
 * Dialog returns focus to the More tab.
 */
export function MoreSheet({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen} title="More" trigger={trigger}>
      <div className="space-y-6">
        {navGroups.map((group) => (
          <section key={group.label}>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-tertiary">{group.label}</p>
            <ul className="grid grid-cols-2 gap-2">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      onClick={() => setOpen(false)}
                      className="flex min-h-[52px] items-center gap-3 rounded-xl border border-border bg-surface-elevated px-3 text-sm font-medium text-ink focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden"
                    >
                      <Icon className="h-5 w-5 shrink-0 text-ink-secondary" aria-hidden="true" />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
    </Sheet>
  );
}
