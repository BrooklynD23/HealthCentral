/**
 * MedicationOverlay — Displays medication periods active during a given time window.
 *
 * UX-001: Frontend-only temporal overlay using existing observation + medication data.
 */

import { Pill } from 'lucide-react';
import { Badge } from '@/components/ui';
import type { MedicationOverlayPeriod } from '@/services/types';

interface MedicationOverlayProps {
  medications: MedicationOverlayPeriod[];
  className?: string;
}

export function MedicationOverlay({ medications, className }: MedicationOverlayProps) {
  if (medications.length === 0) {
    return (
      <div className={className} data-testid="medication-overlay-empty">
        <p className="text-sm text-ink-tertiary">
          No medications were active when this result was collected.
        </p>
      </div>
    );
  }

  return (
    <div className={className} data-testid="medication-overlay">
      <div className="flex flex-wrap gap-2">
        {medications.map((med) => (
          <a
            key={med.medicationId}
            href={`/medications/${med.medicationId}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent-subtle text-accent text-sm font-medium hover:bg-accent/10 transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2"
            aria-label={`View ${med.medicationName} details`}
          >
            <Pill className="w-3.5 h-3.5" />
            <span>{med.medicationName}</span>
            {med.dosageLabel && (
              <Badge variant="default" className="text-xs ml-1">
                {med.dosageLabel}
              </Badge>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
