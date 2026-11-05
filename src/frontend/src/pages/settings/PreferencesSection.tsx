/**
 * Preferences section (UI-PG-SETTINGS): time zone, voice logging, streaks visibility.
 *
 * Also exports SwitchRow, the labelled row the other sections use for their switches.
 */

import { useEffect, useId, useState, type ReactNode, type Ref } from 'react';
import { Clock, Flame, Mic } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { Switch } from '@/components/ui/Switch';
import { cn } from '@/utils/cn';
import { useTimezone, useSaveTimezone, useVoiceSettings, useSaveVoiceSettings } from '@/services';
import { useGamificationSettings, useSaveGamificationSettings } from '@/services/modelSettings';

const COMMON_TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
];

interface SwitchRowProps {
  label: string;
  checked: boolean;
  onCheckedChange: () => void;
  disabled?: boolean;
  /** The Switch's button, for a caller that returns focus to it. */
  switchRef?: Ref<HTMLButtonElement>;
}

/**
 * Mounts its children `frames` paints after it mounts. Opening a section is a burst of work (the cards mount, then their
 * replies arrive), and a burst of back-to-back tasks delays the page's timers (G10, stillness; the readings found tasks under
 * 50 ms at dev x1, not one long task): the parts that are not above T0 are mounted a frame or two later, so that the first
 * paint is small. Used for what the patient reads second. That includes T0 copy (DataDonationCard's consent copy in Assistant
 * & privacy): G10 takes a node's baseline from the first sample in which it exists, so a node that mounts late is held still
 * from its mount, not counted as having moved.
 */
export function AfterPaint({ frames, children }: { frames: number; children: ReactNode }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let remaining = frames;
    let raf = 0;
    const tick = () => {
      remaining -= 1;
      if (remaining <= 0) setReady(true);
      else raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [frames]);
  return ready ? <>{children}</> : null;
}

/** A label and a Switch in one tinted row. The label names the switch and a click on it toggles. */
export function SwitchRow({ label, checked, onCheckedChange, disabled, switchRef }: SwitchRowProps) {
  const id = useId();
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4 rounded-xl border px-4 py-3',
        checked ? 'border-accent/20 bg-accent-subtle' : 'border-transparent bg-surface-muted'
      )}
    >
      <label htmlFor={id} className={cn('text-sm font-medium', checked ? 'text-accent' : 'text-ink-secondary')}>
        {label}
      </label>
      <Switch ref={switchRef} id={id} checked={checked} onCheckedChange={onCheckedChange} disabled={disabled} />
    </div>
  );
}

export function PreferencesSection() {
  const { data: timezoneData } = useTimezone();
  const saveTimezone = useSaveTimezone();
  const { data: voiceData } = useVoiceSettings();
  const saveVoice = useSaveVoiceSettings();
  const { data: gamificationData } = useGamificationSettings();
  const saveGamification = useSaveGamificationSettings();
  const showStreaks = gamificationData?.streaks_hidden !== true;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:items-start">
      {/* Timezone */}
      <Card>
        <CardHeader className="border-b border-black/4">
          <CardTitle className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-ink-secondary" />
            Timezone
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-sm text-ink-secondary mb-3">
            Used for streak and badge calculations.
          </p>
          <select
            aria-label="Time zone"
            value={timezoneData?.timezone ?? 'UTC'}
            onChange={(e) => saveTimezone.mutate(e.target.value)}
            className="w-full px-3 py-2 rounded-xl bg-surface-muted text-sm text-ink border border-black/6 focus:outline-hidden focus:ring-2 focus:ring-accent transition-all"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>{tz.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </CardContent>
      </Card>

      {/* Voice Logging */}
      <Card>
        <CardHeader className="border-b border-black/4">
          <CardTitle className="flex items-center gap-3">
            <Mic className="w-5 h-5 text-ink-secondary" />
            Voice Logging
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-sm text-ink-secondary mb-3">
            Use your microphone to log doses by voice. Speech is processed locally by your browser.
          </p>
          <SwitchRow
            label="Enable Voice Logging"
            checked={voiceData?.voice_logging_enabled === true}
            onCheckedChange={() => {
              saveVoice.mutate({
                voice_logging_enabled: !voiceData?.voice_logging_enabled,
              });
            }}
          />
        </CardContent>
      </Card>

      {/* Streaks */}
      <Card>
        <CardHeader className="border-b border-black/4">
          <CardTitle className="flex items-center gap-3">
            <Flame className="w-5 h-5 text-ink-secondary" />
            Streaks
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <p className="text-sm text-ink-secondary mb-3">
            Show medication streak counts. Badges stay visible either way.
          </p>
          <SwitchRow
            label="Show streaks"
            checked={showStreaks}
            onCheckedChange={() => saveGamification.mutate({ streaks_hidden: showStreaks })}
          />
        </CardContent>
      </Card>
    </div>
  );
}
