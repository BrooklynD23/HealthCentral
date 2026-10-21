/**
 * AGENT-ENABLED-TOGGLE (RRSI-OQ-9): per-profile switch for the agent graph.
 * On by default; when off, chat answers come from the legacy retrieval path.
 */
import { cn } from '@/utils/cn';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { useModelSettings, useSaveAgentSettings } from '@/services';

export function AgentSettingsCard() {
  const { data, isLoading, isError } = useModelSettings();
  const save = useSaveAgentSettings();
  const on = data?.agent_enabled === true;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Assistant mode</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-ink-secondary">Loading your assistant setting...</p>
        ) : isError || !data ? (
          <p role="alert" className="text-sm text-status-critical">
            Could not load this setting. Reload to try again.
          </p>
        ) : (
          <button
            type="button"
            role="switch"
            aria-checked={on}
            aria-label="Step-by-step assistant"
            aria-describedby="agent-enabled-desc"
            disabled={save.isPending}
            onClick={() => save.mutate(!on)}
            className={cn(
              'w-full flex items-center justify-between gap-4 px-4 py-3 rounded-xl text-left',
              'transition-all duration-300 ease-in-out',
              on
                ? 'bg-accent-subtle border border-accent/20'
                : 'bg-surface-muted border border-transparent hover:bg-surface-sunken',
            )}
          >
            <span id="agent-enabled-desc" className="text-sm text-ink-secondary">
              Use the step-by-step assistant. When off, answers come from the simpler search path.
            </span>
            <span
              aria-hidden
              className={cn(
                'w-10 h-6 shrink-0 rounded-full relative transition-colors duration-300',
                on ? 'bg-accent' : 'bg-black/12',
              )}
            >
              <span
                className={cn(
                  'absolute w-4 h-4 rounded-full bg-white top-1 transition-transform duration-300',
                  on ? 'translate-x-5' : 'translate-x-1',
                )}
              />
            </span>
          </button>
        )}
        {save.isError && (
          <p role="alert" className="mt-2 text-sm text-status-critical">
            Could not save this setting. Try again.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
