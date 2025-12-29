import { useState } from 'react';
import { Search, Shield, ShieldCheck, User } from 'lucide-react';
import { cn } from '@/utils/cn';

export function TopBar() {
  const [safeMode, setSafeMode] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-40 h-16 px-8 flex items-center justify-between gap-6 bg-surface/80 backdrop-blur-md border-b border-black/[0.04]">
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-tertiary" />
          <input
            type="search"
            placeholder="Search tests, terms..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2.5 rounded-xl',
              'bg-white border border-black/[0.06]',
              'text-sm text-ink placeholder:text-ink-tertiary',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
              'transition-shadow duration-200'
            )}
            aria-label="Search tests and terms"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setSafeMode(!safeMode)}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium',
            'min-h-[44px] transition-all duration-200',
            'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
            safeMode
              ? 'bg-verified-subtle text-status-verified'
              : 'bg-surface-muted text-ink-secondary hover:bg-black/[0.06]'
          )}
          aria-pressed={safeMode ? "true" : "false"}
          aria-label={`Safety mode ${safeMode ? 'enabled' : 'disabled'}`}
        >
          {safeMode ? (
            <ShieldCheck className="w-4 h-4" />
          ) : (
            <Shield className="w-4 h-4" />
          )}
          <span>Safety Mode</span>
          <span
            className={cn(
              'px-1.5 py-0.5 rounded text-xs font-semibold',
              safeMode ? 'bg-status-verified/20' : 'bg-black/10'
            )}
          >
            {safeMode ? 'ON' : 'OFF'}
          </span>
        </button>

        <button
          className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            'bg-surface-elevated border border-black/[0.06] shadow-soft',
            'text-ink-secondary hover:text-ink hover:shadow-card',
            'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
            'transition-all duration-200'
          )}
          aria-label="User profile"
        >
          <User className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}
