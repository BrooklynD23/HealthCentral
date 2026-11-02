import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { BrandMark } from './BrandMark';
import { openPalette, usePaletteShortcuts } from './paletteEvents';
import { ProfileMenu } from './ProfileMenu';
import { SafetyModeToggle } from './SafetyModeToggle';

/**
 * The top bar (plan §3.2). On desktop it is one 64 px row: the search button that opens the command palette (plan
 * §3.3), the safety toggle and the profile menu. On phones the brand mark sits at the start and a search icon link
 * stands in for the button. Row 1 holds the brand, the search link and the profile menu; row 2 holds the safety
 * toggle with its full label (L0 ruling 10:24:24Z). Row 2 is part of the header, so the route container starts
 * below it.
 */
export function TopBar() {
  usePaletteShortcuts();

  return (
    <header className="sticky top-0 z-40 flex flex-wrap items-center gap-x-2 border-b border-border bg-surface px-3 py-1 lg:h-16 lg:flex-nowrap lg:gap-6 lg:px-8 lg:py-0">
      <span className="lg:hidden">
        <BrandMark wordmark={false} />
      </span>

      <button
        type="button"
        data-palette-trigger=""
        onClick={openPalette}
        aria-haspopup="dialog"
        aria-keyshortcuts="Control+K Meta+K /"
        className="relative hidden h-10 min-w-0 flex-1 items-center rounded-xl border border-border bg-surface-elevated pl-10 pr-3 text-left text-sm text-ink-secondary hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden lg:flex lg:max-w-md"
      >
        <Search
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-secondary"
        />
        Search health records
      </button>

      <Link
        to="/search"
        aria-label="Search"
        className="ml-auto inline-flex min-h-target min-w-target items-center justify-center rounded-xl border border-border bg-surface-elevated text-ink hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-hidden lg:hidden"
      >
        <Search className="h-5 w-5" aria-hidden="true" />
      </Link>

      {/* Below lg the group is `contents`, so the toggle and the profile menu become header items: the toggle
          drops to row 2 (order-last, full width) and the profile menu stays on row 1. At lg they sit side by side. */}
      <div className="contents lg:flex lg:shrink-0 lg:items-center lg:gap-4">
        <SafetyModeToggle className="order-last basis-full lg:order-none lg:basis-auto" />
        <ProfileMenu />
      </div>
    </header>
  );
}
