import { Lightbulb } from 'lucide-react';
import { cn } from '@/utils/cn';

interface AdviceSectionProps {
  adviceText: string;
  className?: string;
}

export function AdviceSection({ adviceText, className }: AdviceSectionProps) {
  const paragraphs = adviceText.split('\n').filter(Boolean);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-accent" />
        <h4 className="text-sm font-semibold text-ink">Recommendations</h4>
      </div>
      <div className="space-y-2 pl-6">
        {paragraphs.map((paragraph, i) => (
          <p key={i} className="text-sm text-ink-secondary leading-relaxed">
            {paragraph}
          </p>
        ))}
      </div>
    </div>
  );
}
