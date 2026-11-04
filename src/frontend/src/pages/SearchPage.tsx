/** Cross-record local search page (HC-M21). */

import { FormEvent, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  FileSearch,
  FileText,
  FlaskConical,
  Loader2,
  Search,
  Tags,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Badge, Button, Card, CardContent, EmptyState, Input } from '@/components/ui';
import { HIGHLIGHT_LABELS } from '@/services/highlights';
import type { HighlightType } from '@/services/highlights';
import { useSearch } from '@/services/search';
import type { SearchRecordType, SearchResult } from '@/services/search';

const CATEGORY_OPTIONS = [
  { value: '', label: 'All categories' },
  { value: 'lab', label: 'Lab reports' },
  { value: 'imaging', label: 'Imaging' },
  { value: 'pathology', label: 'Pathology' },
  { value: 'visit_notes', label: 'Visit notes' },
];

const RECORD_META: Record<
  SearchRecordType,
  { label: string; icon: LucideIcon; link: string; linkLabel: string }
> = {
  document: { label: 'Document', icon: FileText, link: '/inbox', linkLabel: 'Open inbox' },
  entity: { label: 'Extracted detail', icon: Tags, link: '/verify', linkLabel: 'Review extraction' },
  observation: { label: 'Observation', icon: FlaskConical, link: '/trends', linkLabel: 'View trends' },
};

/**
 * One result is one link. The record link is stretched over the whole card (after:inset-0), so the card is the target;
 * the link text and the target are unchanged. Card variant="interactive" is not used: its hover lifts the card, and a
 * T0 value never sits inside an ancestor that moves (plan section 2.1).
 */
function ResultCard({ result }: { result: SearchResult }) {
  const meta = RECORD_META[result.type];
  const Icon = meta.icon;
  return (
    <Card
      data-search-result
      className="relative transition-colors duration-[var(--dur-hover)] ease-[var(--ease-out)] hover:bg-surface-muted has-[a:focus-visible]:ring-2 has-[a:focus-visible]:ring-accent"
    >
      <CardContent className="py-4">
        <div className="flex items-start gap-4">
          <div className="mt-0.5 rounded-xl bg-surface-muted p-2.5">
            <Icon className="h-5 w-5 text-ink-secondary" aria-hidden="true" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="accent">{meta.label}</Badge>
              {result.verified_status === 'unverified' && (
                <Badge variant="caution" data-t0 data-search-verification>
                  Needs verification
                </Badge>
              )}
              {result.category && <Badge>{result.category.replace('_', ' ')}</Badge>}
            </div>
            <h2 data-t0 data-search-title className="mt-1.5 text-sm font-medium text-ink [overflow-wrap:anywhere]">
              {result.title}
            </h2>
            <p data-t0 data-search-snippet className="mt-1 text-sm text-ink-secondary [overflow-wrap:anywhere]">
              {result.snippet}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs">
              {result.date && (
                <span data-t0 data-search-date className="text-ink-tertiary">
                  {result.date}
                </span>
              )}
              <Link
                to={meta.link}
                className="font-medium text-accent hover:underline after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-hidden"
              >
                {meta.linkLabel}
              </Link>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeQuery = searchParams.get('q') ?? '';
  const [queryInput, setQueryInput] = useState(activeQuery);
  // The URL can change while this page stays mounted (the palette sends /search?q=... from /search, and the layout
  // keys on the pathname only). The box follows it; set during render, so there is no frame with the old text.
  const [syncedQuery, setSyncedQuery] = useState(activeQuery);
  if (syncedQuery !== activeQuery) {
    setSyncedQuery(activeQuery);
    setQueryInput(activeQuery);
  }
  const [provider, setProvider] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [category, setCategory] = useState('');
  const [highlightType, setHighlightType] = useState<HighlightType | ''>('');

  const { data, isLoading, isError, refetch } = useSearch({
    q: activeQuery,
    provider,
    date_from: dateFrom,
    date_to: dateTo,
    category,
    highlight_type: highlightType,
    limit: 50,
  });
  const results = data?.results ?? [];
  const searchInput = useRef<HTMLInputElement>(null);

  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    const q = queryInput.trim();
    setSearchParams(q ? { q } : {});
  };

  // The Try again button leaves with the error while the query refetches, so focus goes to the box rather than to
  // <body>.
  const tryAgain = () => {
    searchInput.current?.focus();
    void refetch();
  };

  // Clears the query and every filter, so the next search is not empty again because of a forgotten filter. The
  // button leaves with the empty state, so focus goes to the box rather than to <body>.
  const clearSearch = () => {
    setSearchParams({});
    setProvider('');
    setDateFrom('');
    setDateTo('');
    setCategory('');
    setHighlightType('');
    requestAnimationFrame(() => searchInput.current?.focus());
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">Search records</h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Find text recorded in imported documents, extracted details, and observations.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 py-4">
          <form onSubmit={submitSearch} className="flex gap-2" role="search">
            <Input
              ref={searchInput}
              type="search"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder="Search your records"
              aria-label="Search health records"
            />
            <Button type="submit" disabled={!queryInput.trim()}>
              <Search className="mr-2 h-4 w-4" aria-hidden="true" />
              Search
            </Button>
          </form>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">Provider</span>
              <Input value={provider} onChange={(event) => setProvider(event.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">From</span>
              <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">To</span>
              <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">Category</span>
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                className="h-10 w-full rounded-xl border border-border bg-surface-elevated px-3 text-sm text-ink focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
              >
                {CATEGORY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink-secondary">Highlight</span>
              <select
                value={highlightType}
                onChange={(event) => setHighlightType(event.target.value as HighlightType | '')}
                className="h-10 w-full rounded-xl border border-border bg-surface-elevated px-3 text-sm text-ink focus:outline-hidden focus-visible:ring-2 focus-visible:ring-accent"
              >
                <option value="">All highlights</option>
                {Object.entries(HIGHLIGHT_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>
        </CardContent>
      </Card>

      {activeQuery && (
        <p data-search-query className="text-sm text-ink-secondary [overflow-wrap:anywhere]">
          Searched for “{activeQuery}”
        </p>
      )}

      {isLoading && (
        <div className="flex justify-center py-16" role="status" aria-live="polite">
          <Loader2 className="h-6 w-6 motion-safe:animate-spin text-ink-tertiary" />
          <span className="sr-only">Searching records...</span>
        </div>
      )}

      {isError && (
        // Error text is T0 (plan section 2.1): a static alert, not an EmptyState, whose entrance would move it.
        <Card data-search-error className="border-status-critical/30 bg-status-critical/5">
          <CardContent className="py-10 text-center">
            <div role="alert" data-t0>
              <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-status-critical" aria-hidden="true" />
              <h2 className="font-display text-lg font-medium text-ink">Could not search records</h2>
              <p className="mx-auto mt-1 max-w-xs text-sm text-ink-secondary">
                Something went wrong loading matching records. Please try again.
              </p>
            </div>
            <Button variant="secondary" className="mt-6" onClick={tryAgain}>
              Try again
            </Button>
          </CardContent>
        </Card>
      )}

      {!activeQuery && !isLoading && (
        <EmptyState
          icon={FileSearch}
          title="Search your records"
          description="Enter words found in a document, extracted detail, or observation."
          action={
            <Button variant="secondary" onClick={() => searchInput.current?.focus()}>
              Start a search
            </Button>
          }
        />
      )}

      {activeQuery && !isLoading && !isError && results.length === 0 && (
        <EmptyState
          icon={FileSearch}
          title="No matching records"
          description="Try a different search or adjust the filters."
          action={
            <Button variant="secondary" onClick={clearSearch}>
              Clear search and filters
            </Button>
          }
        />
      )}

      {results.length > 0 && (
        <section aria-label="Search results" className="space-y-3">
          <p className="text-sm font-medium text-ink-secondary">
            {data?.count ?? results.length} result{(data?.count ?? results.length) === 1 ? '' : 's'}
          </p>
          <ol className="space-y-3">
            {results.map((result) => (
              <li key={`${result.type}:${result.id}`}><ResultCard result={result} /></li>
            ))}
          </ol>
        </section>
      )}
    </div>
  );
}
