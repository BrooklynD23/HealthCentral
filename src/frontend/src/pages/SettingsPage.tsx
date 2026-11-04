/**
 * SettingsPage - section host (UI-PG-SETTINGS)
 *
 * `/settings?section=` picks one of four sections: Profile & security (the landing section, also for a missing or
 * unknown value), Preferences, Assistant & privacy, and Advanced. Each section owns its hooks, so landing on
 * Profile & security fetches no model settings, tiers or diagnostics. Below the shell's phone breakpoint the
 * sections are chosen from a sheet instead of a tab list.
 */

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui';
import { Sheet } from '@/components/ui/Sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { SecuritySection } from './settings/SecuritySection';
import { PreferencesSection } from './settings/PreferencesSection';
import { AssistantPrivacySection } from './settings/AssistantPrivacySection';
import { AdvancedSection, type TrainingExportResult } from './settings/AdvancedSection';

const SECTIONS = [
  { id: 'security', label: 'Profile & security' },
  { id: 'preferences', label: 'Preferences' },
  { id: 'assistant-privacy', label: 'Assistant & privacy' },
  { id: 'advanced', label: 'Advanced' },
] as const;

type SectionId = (typeof SECTIONS)[number]['id'];

const LANDING: SectionId = 'security';

function readSection(value: string | null): SectionId {
  return SECTIONS.find((section) => section.id === value)?.id ?? LANDING;
}

// The shell's phone breakpoint: the sidebar appears at 1024 px, and below it the tab bar and the More sheet stand in.
const PHONE_QUERY = '(max-width: 1023px)';

function readIsPhone(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(PHONE_QUERY).matches;
}

/** Synchronous first read, so the first render already has the right layout. */
function useIsPhone(): boolean {
  const [isPhone, setIsPhone] = useState(readIsPhone);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const query = window.matchMedia(PHONE_QUERY);
    setIsPhone(query.matches);
    const handleChange = (event: MediaQueryListEvent) => setIsPhone(event.matches);
    query.addEventListener('change', handleChange);
    return () => query.removeEventListener('change', handleChange);
  }, []);

  return isPhone;
}

function SectionSheet({ section, onSelect }: { section: SectionId; onSelect: (id: SectionId) => void }) {
  const [open, setOpen] = useState(false);
  const current = SECTIONS.find((candidate) => candidate.id === section) ?? SECTIONS[0];

  return (
    <Sheet
      open={open}
      onOpenChange={setOpen}
      title="Settings sections"
      trigger={
        <Button variant="secondary" className="w-full justify-between">
          <span className="flex flex-col items-start text-left">
            <span className="text-xs font-normal text-ink-tertiary">Settings sections</span>
            <span>{current.label}</span>
          </span>
          <ChevronDown className="h-4 w-4 shrink-0" aria-hidden="true" />
        </Button>
      }
    >
      <ul className="space-y-2">
        {SECTIONS.map((candidate) => (
          <li key={candidate.id}>
            <Button
              variant={candidate.id === section ? 'primary' : 'secondary'}
              aria-current={candidate.id === section ? 'true' : undefined}
              className="w-full justify-start"
              onClick={() => {
                onSelect(candidate.id);
                setOpen(false);
              }}
            >
              {candidate.label}
            </Button>
          </li>
        ))}
      </ul>
    </Sheet>
  );
}

export function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const section = readSection(searchParams.get('section'));
  const isPhone = useIsPhone();

  const select = (id: SectionId) => setSearchParams({ section: id }, { replace: true });

  // Profile & security holds state that cannot be asked for again: a recovery code is shown once (the old one is already
  // invalid by then), a code issued while the user is on another section would have nowhere to go, and a restore reports
  // its result there. So once visited it stays mounted, hidden while another section is on screen. The other sections
  // mount again from the server's data. What they hold that the server cannot give back is lifted to this page, which
  // outlives the section: the last training-data export's counts and file path (Advanced), the only statement of them.
  // Advanced is not kept mounted: its hidden T0 nodes would change rect on a section change.
  const securityVisited = useRef(false);
  if (section === 'security') securityVisited.current = true;
  const [exportResult, setExportResult] = useState<TrainingExportResult | null>(null);

  const bodies: Record<SectionId, ReactNode> = {
    security: <SecuritySection />,
    preferences: <PreferencesSection />,
    'assistant-privacy': <AssistantPrivacySection />,
    advanced: <AdvancedSection exportResult={exportResult} onExportResult={setExportResult} />,
  };

  // One tree for both layouts: only the control that chooses the section differs. A breakpoint change must not remount
  // the panels, so nothing below branches on isPhone except that control and the panel's role.
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Settings
        </h1>
        <p className="text-ink-secondary mt-1">
          Configure AI models, document import (OCR), and hardware.
        </p>
      </div>

      <Tabs value={section} onValueChange={(value) => select(readSection(value))}>
        {isPhone ? (
          <SectionSheet section={section} onSelect={select} />
        ) : (
          <TabsList aria-label="Settings sections">
            {SECTIONS.map((candidate) => (
              <TabsTrigger key={candidate.id} value={candidate.id}>
                {candidate.label}
              </TabsTrigger>
            ))}
          </TabsList>
        )}
        {SECTIONS.map((candidate) => {
          const keepMounted = candidate.id === 'security' && securityVisited.current;
          const active = candidate.id === section;
          return (
            // Radix makes a tabpanel a Tab stop. These panels hold focusable controls and are taller than the screen, so the
            // panel's own focus ring would sit under the Safety Rail (WCAG 2.4.11, ui-shell "focus is not obscured").
            // On a phone there is no tab list for the panel to be labelled by, so it is a labelled region instead.
            <TabsContent
              key={candidate.id}
              value={candidate.id}
              tabIndex={-1}
              forceMount={keepMounted ? true : undefined}
              hidden={!active}
              {...(isPhone ? { role: 'region', 'aria-labelledby': undefined, 'aria-label': candidate.label } : {})}
              className={isPhone ? 'mt-6' : undefined}
            >
              {bodies[candidate.id]}
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
