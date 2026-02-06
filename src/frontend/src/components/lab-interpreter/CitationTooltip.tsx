import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import { cn } from '@/utils/cn';
import type { Citation } from '@/services/types';

interface CitationTooltipProps {
  citation: Citation;
  index: number;
}

export function CitationTooltip({ citation, index }: CitationTooltipProps) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        type="button"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className={cn(
          'inline-flex items-center justify-center',
          'w-5 h-5 rounded-full text-[10px] font-semibold',
          'bg-accent-subtle text-accent cursor-help',
          'hover:bg-accent/20 transition-colors',
          'focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1'
        )}
        aria-label={`Citation ${index + 1}: ${citation.text}`}
      >
        {index + 1}
      </button>
      {open && (
        <div
          role="tooltip"
          className={cn(
            'absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2',
            'w-64 p-3 rounded-xl',
            'bg-white border border-black/[0.08] shadow-elevated',
            'text-sm text-ink animate-in fade-in-0 zoom-in-95'
          )}
        >
          <div className="flex items-start gap-2">
            <BookOpen className="w-4 h-4 text-ink-tertiary flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase tracking-wider mb-1">
                {citation.type.replace('_', ' ')}
              </p>
              <p className="text-sm text-ink leading-relaxed">{citation.text}</p>
            </div>
          </div>
          <div className="absolute left-1/2 -translate-x-1/2 -bottom-1.5 w-3 h-3 bg-white border-r border-b border-black/[0.08] rotate-45" />
        </div>
      )}
    </span>
  );
}
