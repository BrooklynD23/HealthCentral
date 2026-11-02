import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Command, defaultFilter } from 'cmdk';
import { FileText, FlaskConical, Pill, Search, Tags, Upload, type LucideIcon } from 'lucide-react';
import { Modal } from '@/components/ui/Dialog';
import { useObservations } from '@/services/observations';
import { useSearch, type SearchRecordType } from '@/services/search';
import type { Observation } from '@/services/types';
import { useAuthStore } from '@/stores/authStore';
import { navGroups } from './navConfig';
import { closePalette, PALETTE_TRIGGER_SELECTOR, usePaletteOpen } from './paletteEvents';

/**
 * The command palette (plan §3.3, UI-PALETTE). Lazy: AppLayout fetches this chunk on the first open.
 *
 * It has no open or close animation and no animated highlight, so the dialog is the `still` (M0) Modal and no item
 * has a transition. Four groups: Results (an analyte with its latest value as static T0 text), Go to, Actions and
 * Records (the existing /search service, debounced 150 ms). Enter on free text with nothing else to select goes to
 * /search?q= (the "Search records for" item is the default selection then).
 *
 * DF-5: cmdk's `aria-activedescendant` can name an option that the filter has removed. The palette filters the
 * items itself, controls cmdk's `value`, and re-selects the first visible item whenever the query or the visible
 * set changes, so the id always names a rendered option.
 */

const DEBOUNCE_MS = 150;
const MAX_RESULTS = 8;
const MAX_RECORDS = 5;

interface Entry {
  /** Unique across the palette; cmdk's `value` and the key of the controlled selection. */
  value: string;
  label: string;
  keywords: string[];
  icon: LucideIcon;
  /** Static text on the right (the Results group's latest value). Marked data-t0. */
  detail?: string;
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

function formatLatest(obs: Observation): string | undefined {
  const value = obs.value ?? obs.value_text;
  if (value === null || value === undefined || value === '') return undefined;
  return [value, obs.unit].filter(Boolean).join(' ');
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

const ITEM_CLASS =
  'flex min-h-target cursor-default items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink data-[selected=true]:bg-accent-subtle';

function PaletteItem({ entry, onRun }: { entry: Entry; onRun: (entry: Entry) => void }) {
  const Icon = entry.icon;
  return (
    <Command.Item value={entry.value} keywords={entry.keywords} onSelect={() => onRun(entry)} className={ITEM_CLASS}>
      <Icon className="h-4 w-4 shrink-0 text-ink-secondary" aria-hidden="true" />
      <span className="min-w-0 flex-1 truncate">{entry.label}</span>
      {entry.detail ? (
        <span data-t0="" className="shrink-0 tabular-nums text-ink-secondary">
          {entry.detail}
        </span>
      ) : null}
    </Command.Item>
  );
}

export default function CommandPalette() {
  const open = usePaletteOpen();
  const navigate = useNavigate();
  const { profileId } = useAuthStore();
  const { data: observations } = useObservations({ profile_id: profileId || '' });

  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState('');
  const trimmed = query.trim();
  const debounced = useDebounced(trimmed, DEBOUNCE_MS);
  const { data: found } = useSearch({ q: debounced, limit: MAX_RECORDS });

  const groups = useMemo<Group[]>(() => {
    const matches = (entry: Entry) => defaultFilter(entry.label, trimmed, entry.keywords) > 0;

    const results: Entry[] = latestByAnalyte(observations)
      .map((obs) => ({
        value: `result:${obs.analyte_canonical}`,
        label: obs.analyte_raw || obs.analyte_canonical,
        keywords: [obs.analyte_canonical, 'result', 'lab'],
        icon: FlaskConical,
        detail: formatLatest(obs),
        run: (go: typeof navigate) => go('/trends'),
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
            detail: undefined,
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
  const firstVisible = visible[0]?.value ?? '';

  // DF-5: whenever the selection names something that is not on screen, select the first visible item.
  useEffect(() => {
    if (!visible.some((entry) => entry.value === selected)) setSelected(firstVisible);
  }, [visible, selected, firstVisible]);

  // Focus returns to where the palette was opened from (the header trigger when it was opened from the page body).
  const opener = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);
  useLayoutEffect(() => {
    if (open && !wasOpen.current) {
      const active = document.activeElement;
      opener.current = active instanceof HTMLElement && active !== document.body ? active : null;
      setQuery('');
    }
    if (!open && wasOpen.current) {
      const target = opener.current?.isConnected
        ? opener.current
        : document.querySelector<HTMLElement>(PALETTE_TRIGGER_SELECTOR);
      // After Radix's own unmount work, which would otherwise win (DoseLoggingModal does the same).
      window.setTimeout(() => target?.focus(), 0);
    }
    wasOpen.current = open;
  }, [open]);

  const run = (entry: Entry) => {
    entry.run(navigate);
    closePalette();
  };

  const changeQuery = (next: string) => {
    setQuery(next);
    // Select the first item of the new filter now, not after the next render, so the two never disagree.
    setSelected('');
  };

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
      <Command
        label="Command palette"
        shouldFilter={false}
        loop
        value={selected}
        onValueChange={setSelected}
      >
        <Command.Input
          value={query}
          onValueChange={changeQuery}
          placeholder="Search results, pages and records"
          className="h-12 w-full border-b border-border bg-transparent px-4 text-sm text-ink placeholder:text-ink-secondary focus:outline-hidden"
        />
        <Command.List label="Suggestions" className="max-h-[min(24rem,60dvh)] overflow-y-auto p-2">
          {groups.map((group) => (
            <Command.Group
              key={group.id}
              heading={group.heading}
              className="[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:py-2 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-ink-secondary"
            >
              {group.entries.map((entry) => (
                <PaletteItem key={entry.value} entry={entry} onRun={run} />
              ))}
            </Command.Group>
          ))}
        </Command.List>
      </Command>
    </Modal>
  );
}
