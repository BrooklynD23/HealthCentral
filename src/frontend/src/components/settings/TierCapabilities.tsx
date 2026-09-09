/**
 * Per-tier capability disclosure.
 *
 * The tier list already tells a user whether their hardware can RUN a tier.
 * It said nothing about what the tier could then DO — so someone picking the
 * lightest option had no way to learn it will never support the assistant's
 * tool-driven features.
 *
 * This is disclosure, not gating: no feature is refused on these flags. The
 * absence of a capability is stated explicitly rather than omitted, because an
 * omitted row reads as an oversight while a stated one reads as a property of
 * the choice.
 */
import { Cpu, Image as ImageIcon, Wrench } from 'lucide-react';

import { Badge } from '@/components/ui';

import type { TierCapabilityFlags } from '@/services/modelSettings';

interface TierCapabilitiesProps {
  capabilities?: TierCapabilityFlags;
}

function formatContext(tokens: number): string {
  if (tokens >= 1024) return `${Math.round(tokens / 1024)}K context`;
  return `${tokens} token context`;
}

export function TierCapabilities({ capabilities }: TierCapabilitiesProps) {
  // Older backends, and any tier the server could not describe, send nothing.
  // Render nothing rather than inventing defaults that would read as fact.
  if (!capabilities) return null;

  const { context_size, multimodal, agentic_capable } = capabilities;
  const hasModel = context_size > 0;

  return (
    <div className="flex flex-wrap items-center gap-1.5 mt-2">
      {hasModel ? (
        <Badge variant="default" className="gap-1 text-[10px] font-medium">
          <Cpu className="w-3 h-3" aria-hidden="true" />
          {formatContext(context_size)}
        </Badge>
      ) : (
        <Badge variant="default" className="gap-1 text-[10px] font-medium">
          No local model — templated answers only
        </Badge>
      )}

      {multimodal && (
        <Badge variant="info" className="gap-1 text-[10px] font-medium">
          <ImageIcon className="w-3 h-3" aria-hidden="true" />
          Reads images
        </Badge>
      )}

      {hasModel &&
        (agentic_capable ? (
          <Badge variant="verified" className="gap-1 text-[10px] font-medium">
            <Wrench className="w-3 h-3" aria-hidden="true" />
            Assistant tools
          </Badge>
        ) : (
          // NOT "no assistant tools". `function_calling` is a declaration in
          // TIER_MODEL_CONFIG, and most tiers simply don't declare it — Phi-4-mini
          // and BioMistral can call tools whether or not the config says so.
          // Asserting absence here would present a config gap as a model property.
          <Badge variant="default" className="gap-1 text-[10px] font-medium">
            <Wrench className="w-3 h-3" aria-hidden="true" />
            Tool support unconfirmed
          </Badge>
        ))}
    </div>
  );
}
