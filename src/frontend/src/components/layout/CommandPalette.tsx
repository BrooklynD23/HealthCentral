import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, FlaskConical, Pill, Search, Tags, Upload, type LucideIcon } from 'lucide-react';
import { Modal } from '@/components/ui/Dialog';
import { useObservations } from '@/services/observations';
import { useSearch, type SearchRecordType } from '@/services/search';
import type { Observation } from '@/services/types';
import { useAuthStore } from '@/stores/authStore';
import { navGroups } from './navConfig';
import { closePalette, PALETTE_TRIGGER_SELECTOR, usePaletteOpen, usePaletteSession } from './paletteEvents';

/**
 * The command palette (plan §3.3, UI-PALETTE). Lazy: AppLayout fetches this chunk on the first open.
 *
 * It has no open or close animation and no animated highlight, so the dialog is the `still` (M0) Modal and no item
 * has a transition. Four groups: Results (an analyte with its latest value as static T0 text), Go to, Actions and
 * Records (the existing /search service, debounced 150 ms). Enter on free text with nothing else to select goes to
 * /search?q= (the "Search records for" item is the default selection then).
 *
 * DF-5: cmdk 1.1.1 left `aria-activedescendant` naming an option the filter had removed, even with a controlled `value`
 * (L0 ruling 6573186885). So this is a WAI-ARIA combobox and listbox on the Radix Dialog. The active option is derived
 * on every render from the visible options (the stored choice if it is still visible, else the first), and the input's
 * `aria-activedescendant` is that option's id, so it can only name a rendered option and is absent when there are none.
 *
 * The body (state, the observations and the record search) is a child of the dialog, so it mounts on each open and
 * unmounts after the close. A closed palette then holds no live query for a focus refetch to re-run (each /search and
 * /observations call writes an audit row), and a reopened one starts with an empty query.
 */

const DEBOUNCE_MS = 150;
const MAX_RESULTS = 8;
const MAX_RECORDS = 5;
/** The /search route refuses a longer q with a 422 (api/search.py). */
const MAX_QUERY_LENGTH = 200;

interface Entry {
  /** Unique across the palette; the key of the selection. */
  value: string;
  label: string;
  keywords: string[];
  icon: LucideIcon;
  /** Static text on the right (the Results group's latest value). Marked data-t0. */
  detail?: string;
  /** A record hit the patient has not verified (owner D4: an unverified value is visibly marked). */
  unverified?: boolean;
  run: (navigate: ReturnType<typeof useNavigate>) => void;
}

interface Group {
  id: string;
  heading: string;
  entries: Entry[];
}

const RECORD_LINK: Record<SearchRecordType, { icon: LucideIcon; to: string; kind: string }> = {
  document: { icon: FileText, to: '/inbox', kind: 'Document' },
  entity: { icon: Tags, to: '/verify', kind: 'Extracted detail' },
  observation: { icon: FlaskConical, to: '/trends', kind: 'Observation' },
};

/** The most recent observation of each analyte, newest date first (an undated one counts as oldest). */
function latestByAnalyte(observations: Observation[] | undefined): Observation[] {
  const latest = new Map<string, Observation>();
  for (const obs of observations ?? []) {
    const seen = latest.get(obs.analyte_canonical);
    if (!seen || (obs.collected_at ?? '') > (seen.collected_at ?? '')) latest.set(obs.analyte_canonical, obs);
  }
  return [...latest.values()].sort((a, b) => (b.collected_at ?? '').localeCompare(a.collected_at ?? ''));
}

/** The value, its unit and (owner D4) an unverified mark. A numeric 0 is a value, so test for null, not truthiness. */
function formatLatest(obs: Observation): string | undefined {
  const value = obs.value ?? obs.value_text;
  if (value === null || value === undefined || value === '') return undefined;
  const text = obs.unit ? `${value} ${obs.unit}` : String(value);
  return obs.user_verified === true ? text : `${text} (unverified)`;
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

const OPTION_CLASS =
  'flex min-h-target cursor-default items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink aria-selected:bg-accent-subtle';

/** Every word of the query appears in the label or a keyword. An empty query matches everything. */
function matchesQuery(entry: Entry, words: string[]): boolean {
  const text = [entry.label, ...entry.keywords].join(' ').toLowerCase();
  return words.every((word) => text.includes(word));
}

export default function CommandPalette() {
  const open = usePaletteOpen();
  const session = usePaletteSession();

  // Focus returns to where the palette was opened from. Below lg the header button is hidden, so the phone search
  // link stands in: take the trigger that is rendered.
  const opener = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);
  useLayoutEffect(() => {
    if (open && !wasOpen.current) {
      const focused = document.activeElement;
      opener.current = focused instanceof HTMLElement && focused !== document.body ? focused : null;
    }
    if (!open && wasOpen.current) {
      const triggers = Array.from(document.querySelectorAll<HTMLElement>(PALETTE_TRIGGER_SELECTOR));
      const target = opener.current?.isConnected
        ? opener.current
        : (triggers.find((el) => el.getClientRects().length > 0) ?? triggers[0]);
      // After Radix's own unmount work, which would otherwise win (DoseLoggingModal does the same).
      window.setTimeout(() => target?.focus(), 0);
    }
    wasOpen.current = open;
  }, [open]);

  return (
    <Modal
      name="CommandPalette"
      variant="dialog"
      still
      showClose={false}
      open={open}
      onOpenChange={(next) => {
        if (!next) closePalette();
      }}
      title={<span className="sr-only">Command palette</span>}
      description={<span className="sr-only">Type to find a result, a page or an action. Enter on text searches your records.</span>}
      className="top-[12vh] max-w-xl translate-y-0 overflow-hidden p-0"
    >
      {/* Modal puts mt-4 between its (screen-reader only) header and the content; cancel it so the input sits at the top. */}
      <div className="-mt-4">
        <PaletteBody key={session} />
      </div>
    </Modal>
  );
}

function PaletteBody() {
  const open = usePaletteOpen();
  const navigate = useNavigate();
  const { profileId } = useAuthStore();
  const { data: observations } = useObservations({ profile_id: profileId || '' });

  const [query, setQuery] = useState('');
  const [chosen, setChosen] = useState('');
  const listId = useId();
  const trimmed = query.trim();
  const debounced = useDebounced(trimmed, DEBOUNCE_MS);
  // Closing stops the query at once, even while the dialog is held for its exit: a refetch would write a search.view audit row.
  const { data: found } = useSearch({ q: open ? debounced : '', limit: MAX_RECORDS });

  const groups = useMemo<Group[]>(() => {
    const words = trimmed.toLowerCase().split(/\s+/).filter(Boolean);
    const matches = (entry: Entry) => matchesQuery(entry, words);

    const results: Entry[] = latestByAnalyte(observations)
      .map((obs) => ({
        value: `result:${obs.analyte_canonical}`,
        label: obs.analyte_raw || obs.analyte_canonical,
        keywords: [obs.analyte_canonical, 'result', 'lab'],
        icon: FlaskConical,
        detail: formatLatest(obs),
        run: (go: typeof navigate) => go(`/trends?${new URLSearchParams({ analyte: obs.analyte_canonical }).toString()}`),
      }))
      .filter(matches)
      .slice(0, MAX_RESULTS);

    const goTo: Entry[] = navGroups
      .flatMap((group) => group.items.map((item) => ({ item, group: group.label })))
      .map(({ item, group }) => ({
        value: `goto:${item.to}`,
        label: item.label,
        keywords: [group, item.to.slice(1)],
        icon: item.icon,
        run: (go: typeof navigate) => go(item.to),
      }))
      .filter(matches);

    const actions: Entry[] = [
      {
        value: 'action:import',
        label: 'Import a document',
        keywords: ['upload', 'add', 'file', 'pdf', 'scan'],
        icon: Upload,
        run: (go: typeof navigate) => go('/inbox'),
      },
      {
        value: 'action:dose',
        label: 'Log a dose',
        keywords: ['medication', 'medicine', 'pill', 'take'],
        icon: Pill,
        run: (go: typeof navigate) => go('/medications'),
      },
    ].filter(matches);

    const records: Entry[] = [];
    if (trimmed) {
      records.push({
        value: 'search:all',
        label: `Search records for “${trimmed}”`,
        keywords: [],
        icon: Search,
        run: (go: typeof navigate) => go(`/search?${new URLSearchParams({ q: trimmed }).toString()}`),
      });
      if (debounced === trimmed) {
        for (const hit of found?.results ?? []) {
          const meta = RECORD_LINK[hit.type];
          records.push({
            value: `record:${hit.type}:${hit.id}`,
            label: hit.title,
            keywords: [],
            icon: meta.icon,
            unverified: hit.verified_status === 'unverified',
            run: (go: typeof navigate) => go(meta.to),
          });
        }
      }
    }

    return [
      { id: 'results', heading: 'Results', entries: results },
      { id: 'goto', heading: 'Go to', entries: goTo },
      { id: 'actions', heading: 'Actions', entries: actions },
      { id: 'records', heading: 'Records', entries: records },
    ].filter((group) => group.entries.length > 0);
  }, [observations, trimmed, debounced, found]);

  const visible = useMemo(() => groups.flatMap((group) => group.entries), [groups]);
  // DF-5: the active option is always one of the visible ones. A choice the filter removed falls back to the first.
  const activeIndex = Math.max(
    0,
    visible.findIndex((entry) => entry.value === chosen)
  );
  const active = visible[activeIndex];
  const optionId = (index: number) => `${listId}-option-${index}`;
  const activeId = active ? optionId(activeIndex) : undefined;

  useEffect(() => {
    if (activeId) document.getElementById(activeId)?.scrollIntoView?.({ block: 'nearest' });
  }, [activeId]);

  const run = (entry: Entry) => {
    entry.run(navigate);
    closePalette();
  };

  const changeQuery = (next: string) => {
    setQuery(next);
    setChosen(''); // a new filter starts on its first option
  };

  const move = (to: number) => setChosen(visible[(to + visible.length) % visible.length]?.value ?? '');

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.nativeEvent.isComposing || visible.length === 0) return;
    const keys: Record<string, () => void> = {
      ArrowDown: () => move(activeIndex + 1),
      ArrowUp: () => move(activeIndex - 1),
      Home: () => move(0),
      End: () => move(visible.length - 1),
      Enter: () => run(active),
    };
    if (!(event.key in keys)) return;
    event.preventDefault();
    keys[event.key]();
  };

  return (
    <>
      <input
        role="combobox"
        aria-label="Search results, pages and records"
        aria-autocomplete="list"
        aria-controls={listId}
        aria-expanded={visible.length > 0}
        aria-activedescendant={activeId}
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        maxLength={MAX_QUERY_LENGTH}
        value={query}
        onChange={(event) => changeQuery(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Search results, pages and records"
        className="h-12 w-full border-b border-border bg-transparent px-4 text-sm text-ink placeholder:text-ink-secondary focus:outline-hidden focus-visible:ring-inset focus-visible:ring-offset-0"
      />
      <div
        role="listbox"
        id={listId}
        aria-label="Suggestions"
        tabIndex={-1}
        onMouseDown={(event) => event.preventDefault()}
        className="max-h-[min(24rem,60dvh)] overflow-y-auto p-2"
      >
        {groups.map((group) => (
          <div key={group.id} role="group" aria-labelledby={`${listId}-${group.id}`}>
            <div
              id={`${listId}-${group.id}`}
              className="px-3 py-2 text-xs font-medium uppercase text-ink-secondary"
            >
              {group.heading}
            </div>
            {group.entries.map((entry) => {
              const index = visible.indexOf(entry);
              const Icon = entry.icon;
              return (
                <div
                  key={entry.value}
                  id={optionId(index)}
                  role="option"
                  aria-selected={index === activeIndex}
                  onClick={() => run(entry)}
                  onMouseMove={() => index !== activeIndex && setChosen(entry.value)}
                  className={OPTION_CLASS}
                >
                  <Icon className="h-4 w-4 shrink-0 text-ink-secondary" aria-hidden="true" />
                  <span className="min-w-0 flex-1 truncate">{entry.label}</span>
                  {entry.detail ? (
                    <span
                      data-t0=""
                      className="max-w-[50%] text-right tabular-nums text-ink-secondary [overflow-wrap:anywhere]"
                    >
                      {entry.detail}
                    </span>
                  ) : null}
                  {entry.unverified ? (
                    <>
                      {' '}
                      <span className="shrink-0 text-xs text-ink-secondary">(unverified)</span>
                    </>
                  ) : null}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </>
  );
}
