import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { BrandMark } from './BrandMark';
import { ProfileMenu } from './ProfileMenu';
import { SafetyModeToggle } from './SafetyModeToggle';

/**
 * The top bar (plan §3.2): a 64 px row with the search form, the safety toggle
 * and the profile menu. On phones the brand mark sits at the start, since the
 * sidebar that carries the wordmark on desktop is absent.
 */
export function TopBar() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    const q = searchQuery.trim();
    if (q) navigate(`/search?${new URLSearchParams({ q }).toString()}`);
  };

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-2 border-b border-border bg-surface px-3 lg:gap-6 lg:px-8">
      <span className="lg:hidden">
        <BrandMark wordmark={false} />
      </span>

      <form className="min-w-0 flex-1 lg:max-w-md" role="search" onSubmit={submitSearch}>
        <div className="relative">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-tertiary"
          />
          <input
            type="search"
            placeholder="Search"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-10 w-full min-w-0 rounded-xl border border-border bg-surface-elevated pl-10 pr-3 text-sm text-ink placeholder:text-ink-tertiary focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
            aria-label="Search health records"
          />
        </div>
      </form>

      <div className="flex shrink-0 items-center gap-2 lg:gap-4">
        <SafetyModeToggle />
        <ProfileMenu />
      </div>
    </header>
  );
}
