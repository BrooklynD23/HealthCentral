import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Shield, ShieldCheck, User } from 'lucide-react';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui';

export function TopBar() {
  const navigate = useNavigate();
  const [safeMode, setSafeMode] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const q = searchQuery.trim();
    if (q) navigate(`/search?${new URLSearchParams({ q }).toString()}`);
  };

  return (
    <header className="sticky top-0 z-40 h-16 px-8 flex items-center justify-between gap-6 bg-surface/80 backdrop-blur-md border-b border-black/[0.04]">
      <form className="flex-1 max-w-md" role="search" onSubmit={submitSearch}>
        <div className="relative group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-tertiary group-focus-within:text-accent transition-colors" />
          <input
            type="search"
            placeholder="Search health records..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={cn(
              'w-full pl-10 pr-4 py-2 rounded-xl h-10',
              'bg-white border border-black/[0.06]',
              'text-sm text-ink placeholder:text-ink-tertiary',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:border-accent focus:ring-offset-0',
              'transition-all duration-200'
            )}
            aria-label="Search health records"
          />
        </div>
      </form>

      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setSafeMode(!safeMode)}
          className={cn(
            'gap-2 h-10 px-4 rounded-xl font-medium border-black/[0.06]',
            safeMode && 'bg-status-verified-subtle text-status-verified border-status-verified/20 hover:bg-status-verified-subtle'
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
              'px-1.5 py-0.5 rounded text-[10px] font-bold tracking-wider',
              safeMode ? 'bg-status-verified/20' : 'bg-black/10'
            )}
          >
            {safeMode ? 'ON' : 'OFF'}
          </span>
        </Button>

        <Button
          type="button"
          variant="secondary"
          size="icon"
          className="h-10 w-10 rounded-xl border-black/[0.06]"
          aria-label="Profile and settings"
          title="Profile and settings"
          onClick={() => navigate('/settings')}
        >
          <User className="w-5 h-5" />
        </Button>
      </div>
    </header>
  );
}
