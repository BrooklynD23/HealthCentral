/**
 * SearchPage - Hybrid search with faceted filters
 *
 * Sprint 04: DATA-005
 */

import { useState, useMemo, useCallback } from 'react';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { SearchResults } from '@/components/SearchResults';
import { useSearch } from '@/services/search';
import type { SearchFilters } from '@/services/search';

export function SearchPage() {
  const [inputValue, setInputValue] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    mode: 'hybrid',
    limit: 20,
    offset: 0,
  });
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, isFetching } = useSearch(query, filters);

  // Debounced search
  const debounceRef = useMemo(() => ({ timer: null as ReturnType<typeof setTimeout> | null }), []);

  const handleInputChange = useCallback(
    (value: string) => {
      setInputValue(value);
      if (debounceRef.timer) clearTimeout(debounceRef.timer);
      debounceRef.timer = setTimeout(() => {
        setQuery(value.trim());
        setFilters((prev) => ({ ...prev, offset: 0 }));
      }, 300);
    },
    [debounceRef],
  );

  const handleModeChange = (mode: SearchFilters['mode']) => {
    setFilters((prev) => ({ ...prev, mode, offset: 0 }));
  };

  const handleClear = () => {
    setInputValue('');
    setQuery('');
  };

  const handlePageNext = () => {
    setFilters((prev) => ({
      ...prev,
      offset: (prev.offset || 0) + (prev.limit || 20),
    }));
  };

  const handlePagePrev = () => {
    setFilters((prev) => ({
      ...prev,
      offset: Math.max(0, (prev.offset || 0) - (prev.limit || 20)),
    }));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Search
        </h1>
        <p className="text-ink-secondary mt-1">
          Search across your lab results and documents
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-ink-tertiary" />
        <input
          type="text"
          value={inputValue}
          onChange={(e) => handleInputChange(e.target.value)}
          placeholder="Search analytes, values, documents..."
          className="w-full pl-12 pr-20 py-3 rounded-xl border border-black/[0.08] bg-white text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {inputValue && (
            <button onClick={handleClear} className="p-1.5 rounded-lg hover:bg-surface-muted">
              <X className="w-4 h-4 text-ink-tertiary" />
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-1.5 rounded-lg hover:bg-surface-muted"
          >
            <SlidersHorizontal className="w-4 h-4 text-ink-secondary" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Results */}
        <div className="col-span-2">
          {query ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-ink-secondary">
                  {data ? `${data.total_count} results for "${data.query}"` : 'Searching...'}
                </p>
                {(isFetching) && (
                  <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                )}
              </div>
              <SearchResults results={data?.results || []} isLoading={isLoading} />
              {/* Pagination */}
              {data && data.total_count > (filters.limit || 20) && (
                <div className="flex items-center justify-center gap-4 mt-6">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePagePrev}
                    disabled={(filters.offset || 0) === 0}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-ink-secondary">
                    {(filters.offset || 0) + 1}–{Math.min((filters.offset || 0) + (filters.limit || 20), data.total_count)} of {data.total_count}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePageNext}
                    disabled={(filters.offset || 0) + (filters.limit || 20) >= data.total_count}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-16">
              <Search className="w-12 h-12 text-ink-tertiary mx-auto mb-4" />
              <p className="text-ink-secondary">Enter a search term to find lab results and documents.</p>
            </div>
          )}
        </div>

        {/* Filters sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Search Mode</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(['hybrid', 'text', 'semantic'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => handleModeChange(mode)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    filters.mode === mode
                      ? 'bg-accent-subtle text-accent'
                      : 'bg-surface-muted text-ink-secondary hover:bg-surface-sunken'
                  }`}
                >
                  {mode === 'hybrid' ? 'Hybrid (Recommended)' : mode === 'text' ? 'Full Text' : 'Semantic'}
                </button>
              ))}
            </CardContent>
          </Card>

          {showFilters && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Filters</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="flex items-center gap-2 text-sm text-ink-secondary">
                  <input
                    type="checkbox"
                    checked={filters.abnormal_only || false}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, abnormal_only: e.target.checked, offset: 0 }))
                    }
                    className="rounded border-black/[0.12]"
                  />
                  Abnormal values only
                </label>
                <div>
                  <label className="text-xs text-ink-tertiary mb-1 block">From date</label>
                  <input
                    type="date"
                    value={filters.from_date || ''}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, from_date: e.target.value || undefined, offset: 0 }))
                    }
                    className="w-full px-3 py-1.5 rounded-lg border border-black/[0.08] text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-ink-tertiary mb-1 block">To date</label>
                  <input
                    type="date"
                    value={filters.to_date || ''}
                    onChange={(e) =>
                      setFilters((prev) => ({ ...prev, to_date: e.target.value || undefined, offset: 0 }))
                    }
                    className="w-full px-3 py-1.5 rounded-lg border border-black/[0.08] text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
