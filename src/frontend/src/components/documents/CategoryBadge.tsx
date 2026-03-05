/**
 * CategoryBadge — colored badge showing document category.
 */

import { cn } from '@/utils/cn';

const CATEGORY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  imaging: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Imaging' },
  pathology: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Pathology' },
  visit_notes: { bg: 'bg-green-50', text: 'text-green-700', label: 'Visit Notes' },
  lab: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Lab' },
  unknown: { bg: 'bg-gray-50', text: 'text-gray-500', label: 'Uncategorized' },
};

interface CategoryBadgeProps {
  category: string;
  confidence?: number;
  className?: string;
}

export function CategoryBadge({ category, confidence, className }: CategoryBadgeProps) {
  const style = CATEGORY_STYLES[category] ?? CATEGORY_STYLES.unknown;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        style.bg,
        style.text,
        className
      )}
    >
      {style.label}
      {confidence !== undefined && confidence < 0.8 && (
        <span className="text-[10px] opacity-60" title={`${Math.round(confidence * 100)}% confidence`}>
          ?
        </span>
      )}
    </span>
  );
}
