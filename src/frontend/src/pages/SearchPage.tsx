/**
 * SearchPage - Hybrid search with faceted filters
 *
 * Sprint 04: DATA-005
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import { Search, SlidersHorizontal, X } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { SearchResults } from '@/components/SearchResults';
import { useSearch } from '@/services/search';
import type { SearchFilters } from '@/services/search';

interface SavedSearch {
  id: string;
  name: string;
  query: string;
  filters: SearchFilters;
}

const SEARCH_HISTORY_KEY = 'hc.search.history.v1';
const SAVED_SEARCHES_KEY = 'hc.search.saved.v1';
const SEARCH_PERSIST_KEY = 'hc.search.persist_device.v1';
type StorageScope = 'session' | 'local';

function getStorage(scope: StorageScope): Storage | null {
  if (typeof window === 'undefined') return null;
  return scope === 'local' ? window.localStorage : window.sessionStorage;
}

function readStorageList<T>(key: string, scope: StorageScope): T[] {
  const storage = getStorage(scope);
  if (!storage) return [];
  try {
    const raw = storage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed as T[] : [];
  } catch {
    return [];
  }
}

function writeStorageList<T>(key: string, value: T[], scope: StorageScope) {
  const storage = getStorage(scope);
  if (!storage) return;
  storage.setItem(key, JSON.stringify(value));
}

function removeStorageKey(key: string, scope: StorageScope) {
  const storage = getStorage(scope);
  if (!storage) return;
  storage.removeItem(key);
}

function readPersistSetting(): boolean {
  const storage = getStorage('local');
  if (!storage) return false;
  return storage.getItem(SEARCH_PERSIST_KEY) === 'true';
}

function writePersistSetting(enabled: boolean) {
  const storage = getStorage('local');
  if (!storage) return;
  storage.setItem(SEARCH_PERSIST_KEY, enabled ? 'true' : 'false');
}

function persistStorageList<T>(key: string, value: T[], persistOnDevice: boolean) {
  const scope: StorageScope = persistOnDevice ? 'local' : 'session';
  writeStorageList(key, value, scope);
  if (!persistOnDevice) {
    removeStorageKey(key, 'local');
  }
}

export function SearchPage() {
  const [inputValue, setInputValue] = useState('');
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilters>({
    mode: 'hybrid',
    limit: 20,
    offset: 0,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [persistOnDevice, setPersistOnDevice] = useState(false);

  const { data, isLoading, isFetching } = useSearch(query, filters);

  // Debounced search
  const debounceRef = useMemo(() => ({ timer: null as ReturnType<typeof setTimeout> | null }), []);

  useEffect(() => {
    const persisted = readPersistSetting();
    const preferredScope: StorageScope = persisted ? 'local' : 'session';

    let initialHistory = readStorageList<string>(SEARCH_HISTORY_KEY, preferredScope);
    let initialSaved = readStorageList<SavedSearch>(SAVED_SEARCHES_KEY, preferredScope);

    // Migrate legacy localStorage values into session storage when persistence is disabled.
    if (!persisted && initialHistory.length === 0 && initialSaved.length === 0) {
      const legacyHistory = readStorageList<string>(SEARCH_HISTORY_KEY, 'local');
      const legacySaved = readStorageList<SavedSearch>(SAVED_SEARCHES_KEY, 'local');
      if (legacyHistory.length > 0 || legacySaved.length > 0) {
        initialHistory = legacyHistory;
        initialSaved = legacySaved;
        writeStorageList(SEARCH_HISTORY_KEY, legacyHistory, 'session');
        writeStorageList(SAVED_SEARCHES_KEY, legacySaved, 'session');
        removeStorageKey(SEARCH_HISTORY_KEY, 'local');
        removeStorageKey(SAVED_SEARCHES_KEY, 'local');
      }
    }

    setPersistOnDevice(persisted);
    setHistory(initialHistory);
    setSavedSearches(initialSaved);
  }, []);

  const addToHistory = useCallback((searchQuery: string) => {
    const trimmed = searchQuery.trim();
    if (!trimmed) return;
    setHistory((prev) => {
      const next = [trimmed, ...prev.filter((item) => item !== trimmed)].slice(0, 8);
      persistStorageList(SEARCH_HISTORY_KEY, next, persistOnDevice);
      return next;
    });
  }, [persistOnDevice]);

  const applySearch = useCallback((nextQuery: string, nextFilters?: SearchFilters) => {
    const trimmed = nextQuery.trim();
    setInputValue(trimmed);
    setQuery(trimmed);
    if (nextFilters) {
      setFilters({ ...nextFilters, offset: 0 });
    } else {
      setFilters((prev) => ({ ...prev, offset: 0 }));
    }
  }, []);

  const saveCurrentSearch = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setSavedSearches((prev) => {
      const id = `${Date.now()}`;
      const candidate: SavedSearch = {
        id,
        name: trimmed,
        query: trimmed,
        filters: {
          mode: filters.mode,
          from_date: filters.from_date,
          to_date: filters.to_date,
          analyte: filters.analyte,
          abnormal_only: filters.abnormal_only,
          limit: filters.limit,
        },
      };
      const deduped = [candidate, ...prev.filter((item) => item.query !== trimmed)].slice(0, 10);
      persistStorageList(SAVED_SEARCHES_KEY, deduped, persistOnDevice);
      return deduped;
    });
  }, [filters, persistOnDevice, query]);

  const removeSavedSearch = useCallback((id: string) => {
    setSavedSearches((prev) => {
      const next = prev.filter((item) => item.id !== id);
      persistStorageList(SAVED_SEARCHES_KEY, next, persistOnDevice);
      return next;
    });
  }, [persistOnDevice]);

  const handlePersistenceToggle = useCallback((enabled: boolean) => {
    setPersistOnDevice(enabled);
    writePersistSetting(enabled);
    persistStorageList(SEARCH_HISTORY_KEY, history, enabled);
    persistStorageList(SAVED_SEARCHES_KEY, savedSearches, enabled);
  }, [history, savedSearches]);

  const handleInputChange = useCallback(
    (value: string) => {
      setInputValue(value);
      if (debounceRef.timer) clearTimeout(debounceRef.timer);
      debounceRef.timer = setTimeout(() => {
        const trimmed = value.trim();
        setQuery(trimmed);
        setFilters((prev) => ({ ...prev, offset: 0 }));
        addToHistory(trimmed);
      }, 300);
    },
    [addToHistory, debounceRef],
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

  useEffect(() => {
    return () => {
      if (debounceRef.timer) {
        clearTimeout(debounceRef.timer);
      }
    };
  }, [debounceRef]);

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
          aria-label="Search"
          className="w-full pl-12 pr-20 py-3 rounded-xl border border-black/[0.08] bg-white text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent"
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {inputValue && (
            <button onClick={handleClear} className="p-1.5 rounded-lg hover:bg-surface-muted" aria-label="Clear search">
              <X className="w-4 h-4 text-ink-tertiary" />
            </button>
          )}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="p-1.5 rounded-lg hover:bg-surface-muted"
            aria-label="Toggle filters"
          >
            <SlidersHorizontal className="w-4 h-4 text-ink-secondary" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Results */}
        <div className="md:col-span-2">
          {query ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-ink-secondary">
                  {data ? `${data.total_count} results for "${data.query}"` : 'Searching...'}
                </p>
                <div className="flex items-center gap-2">
                  {query && (
                    <Button variant="secondary" size="sm" onClick={saveCurrentSearch}>
                      Save Search
                    </Button>
                  )}
                  {(isFetching) && (
                    <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                  )}
                </div>
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
                    aria-label="Previous page"
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
                    aria-label="Next page"
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
        <div className="hidden space-y-4 md:block">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Search Mode</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2" role="radiogroup" aria-label="Search mode">
              {(['hybrid', 'text', 'semantic'] as const).map((mode) => (
                <button
                  key={mode}
                  role="radio"
                  aria-checked={filters.mode === mode}
                  onClick={() => handleModeChange(mode)}
                  className={`w-full text-left px-3 py-2.5 rounded-xl text-sm font-medium transition-colors min-h-[44px] ${
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

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Recent Searches</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {history.length === 0 ? (
                <p className="text-sm text-ink-tertiary">No recent searches yet.</p>
              ) : (
                history.map((item) => (
                  <button
                    key={item}
                    onClick={() => applySearch(item)}
                    className="w-full text-left px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink-secondary hover:bg-surface-sunken"
                  >
                    {item}
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Saved Searches</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {savedSearches.length === 0 ? (
                <p className="text-sm text-ink-tertiary">Save a query to pin it here.</p>
              ) : (
                savedSearches.map((saved) => (
                  <div key={saved.id} className="flex items-center gap-2">
                    <button
                      onClick={() => applySearch(saved.query, saved.filters)}
                      className="flex-1 text-left px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink-secondary hover:bg-surface-sunken"
                    >
                      {saved.name}
                    </button>
                    <button
                      onClick={() => removeSavedSearch(saved.id)}
                      className="p-1.5 rounded-lg hover:bg-surface-muted"
                      aria-label={`Remove saved search ${saved.name}`}
                    >
                      <X className="w-4 h-4 text-ink-tertiary" />
                    </button>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Search Privacy</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <label className="flex items-center gap-2 text-sm text-ink-secondary">
                <input
                  type="checkbox"
                  checked={persistOnDevice}
                  onChange={(e) => handlePersistenceToggle(e.target.checked)}
                  className="rounded border-black/[0.12]"
                />
                Remember searches on this device
              </label>
              <p className="text-xs text-ink-tertiary">
                {persistOnDevice
                  ? 'Search history is saved across browser restarts on this device.'
                  : 'Search history is only kept for this browser session.'}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
