import { Lightbulb } from 'lucide-react';
import { cn } from '@/utils/cn';
import { formatInterpretationText } from './formatInterpretationText';

interface AdviceSectionProps {
  adviceText: string;
  className?: string;
}

export function AdviceSection({ adviceText, className }: AdviceSectionProps) {
  const paragraphs = adviceText
    .split('\n')
    .flatMap((line) => formatInterpretationText(line).paragraphs);

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-accent" />
        <h4 className="text-sm font-semibold text-ink">Recommendations</h4>
      </div>
      <div className="space-y-2 pl-6">
        {paragraphs.map((runs, i) => (
          <p key={i} className="text-sm text-ink-secondary leading-relaxed">
            {runs.map((run, j) =>
              run.bold ? <strong key={j}>{run.text}</strong> : <span key={j}>{run.text}</span>
            )}
          </p>
        ))}
      </div>
    </div>
  );
}
