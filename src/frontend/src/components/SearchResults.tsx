/**
 * SearchResults - Renders search result cards
 *
 * Sprint 04: DATA-005
 */

import { FileText, FlaskConical, Calendar } from 'lucide-react';
import { Badge } from '@/components/ui';
import type { SearchResultItem } from '@/services/search';

interface SearchResultsProps {
  results: SearchResultItem[];
  isLoading?: boolean;
}

function ResultSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-surface-muted rounded-xl p-4 space-y-2">
          <div className="h-4 bg-black/[0.06] rounded w-1/3" />
          <div className="h-3 bg-black/[0.04] rounded w-2/3" />
        </div>
      ))}
    </div>
  );
}

export function SearchResults({ results, isLoading }: SearchResultsProps) {
  if (isLoading) return <ResultSkeleton />;

  if (results.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-4" />
        <p className="text-ink-secondary">No results found.</p>
        <p className="text-sm text-ink-tertiary mt-1">Try a different search term or adjust filters.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {results.map((result) => (
        <div
          key={result.id}
          className="bg-white rounded-xl border border-black/[0.06] p-4 hover:border-accent/30 transition-colors"
        >
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-surface-muted flex items-center justify-center flex-shrink-0 mt-0.5">
              {result.type === 'observation' ? (
                <FlaskConical className="w-4 h-4 text-accent" />
              ) : (
                <FileText className="w-4 h-4 text-ink-secondary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-semibold text-ink truncate">{result.title}</h3>
                {result.value !== null && result.unit && (
                  <Badge variant="default">{result.value} {result.unit}</Badge>
                )}
                <Badge variant={result.type === 'observation' ? 'verified' : 'default'}>
                  {result.type === 'observation' ? 'Lab' : 'Document'}
                </Badge>
              </div>
              <p
                className="text-sm text-ink-secondary line-clamp-2"
                dangerouslySetInnerHTML={{ __html: result.snippet }}
              />
              <div className="flex items-center gap-4 mt-2 text-xs text-ink-tertiary">
                {result.collected_at && (
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(result.collected_at).toLocaleDateString()}
                  </span>
                )}
                <span>Relevance: {(result.score * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
