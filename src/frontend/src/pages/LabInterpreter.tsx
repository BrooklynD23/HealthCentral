import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  Loader2,
  AlertTriangle,
  FileText,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Badge,
} from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useObservations, useTrend } from '@/services/observations';
import {
  useInterpretation,
  useGenerateInterpretation,
  useGeneratePanelInterpretation,
} from '@/services/interpretations';
import { useAuthStore } from '@/stores/authStore';
import {
  InterpretedResultCard,
  PanelInterpretationDashboard,
  InterpretedTrendChart,
} from '@/components/lab-interpreter';
import type { Observation, PanelInterpretationResponse } from '@/services/types';

const panels = [
  { id: 'cbc', label: 'CBC' },
  { id: 'cmp', label: 'CMP' },
  { id: 'lipid', label: 'Lipids' },
  { id: 'thyroid', label: 'Thyroid' },
];

export function LabInterpreter() {
  const prefersReducedMotion = useReducedMotion();
  const { profileId } = useAuthStore();
  const [activePanel, setActivePanel] = useState('cbc');
  const [selectedObservation, setSelectedObservation] = useState<Observation | null>(null);
  const [panelInterpretation, setPanelInterpretation] = useState<PanelInterpretationResponse | null>(null);

  const {
    data: observations,
    isLoading: observationsLoading,
    isError: observationsError,
  } = useObservations({ profile_id: profileId || '' });

  // Group observations by analyte
  const analyteList = useMemo(() => {
    if (!observations) return [];
    const uniqueAnalytes = new Map<string, Observation>();
    observations.forEach((obs) => {
      if (!uniqueAnalytes.has(obs.analyte_canonical)) {
        uniqueAnalytes.set(obs.analyte_canonical, obs);
      }
    });
    return Array.from(uniqueAnalytes.values());
  }, [observations]);

  const effectiveObservation = selectedObservation || (analyteList[0] ?? null);

  // Fetch interpretation for selected observation
  const {
    data: interpretation,
    isLoading: interpLoading,
  } = useInterpretation(effectiveObservation?.id);

  // Fetch trend for selected observation
  const { data: trendData, isLoading: trendLoading } = useTrend(
    effectiveObservation?.analyte_canonical,
    profileId || ''
  );

  const generateInterpretation = useGenerateInterpretation();
  const generatePanelInterp = useGeneratePanelInterpretation();

  const handleGenerateInterpretation = () => {
    if (!effectiveObservation) return;
    generateInterpretation.mutate({ observationId: effectiveObservation.id });
  };

  const handleGeneratePanelInterpretation = () => {
    const latestDate = observations?.[0]?.collected_at;
    if (!latestDate) return;
    generatePanelInterp.mutate(
      { panelName: activePanel, collectedAt: latestDate },
      { onSuccess: (data) => setPanelInterpretation(data) }
    );
  };

  // Loading state
  if (observationsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  // Error state
  if (observationsError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Failed to load observations</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!observations || observations.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Lab Interpreter
          </h1>
          <p className="text-ink-secondary mt-1">
            AI-powered insights for your lab results
          </p>
        </div>
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
              <p className="text-lg font-medium text-ink mb-1">No lab results</p>
              <p className="text-ink-secondary">
                Import lab documents to get AI interpretations.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Lab Interpreter
          </h1>
          <p className="text-ink-secondary mt-1">
            AI-powered insights for your lab results
          </p>
        </div>
        <Button
          onClick={handleGeneratePanelInterpretation}
          disabled={generatePanelInterp.isPending}
          className="gap-2"
        >
          {generatePanelInterp.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4" />
          )}
          Interpret {activePanel.toUpperCase()} Panel
        </Button>
      </div>

      {/* Panel Tabs */}
      <div className="flex gap-2">
        {panels.map((panel) => (
          <button
            key={panel.id}
            onClick={() => {
              setActivePanel(panel.id);
              setPanelInterpretation(null);
            }}
            className={cn(
              'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2',
              activePanel === panel.id
                ? 'bg-accent text-white shadow-soft'
                : 'bg-surface-elevated border border-black/[0.06] text-ink-secondary hover:bg-surface-muted'
            )}
          >
            {panel.label}
          </button>
        ))}
      </div>

      {/* Panel Interpretation */}
      {(panelInterpretation || generatePanelInterp.isPending) && (
        <PanelInterpretationDashboard
          interpretation={panelInterpretation ?? undefined}
          isLoading={generatePanelInterp.isPending}
          isError={generatePanelInterp.isError}
        />
      )}

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-6">
        {/* Chart + Interpretation */}
        <div className="col-span-2 space-y-4">
          <InterpretedTrendChart
            trendData={trendData}
            interpretation={interpretation ?? undefined}
            isLoading={trendLoading}
            isError={false}
          />

          {/* Interpretation card or generate prompt */}
          {interpretation ? (
            <InterpretedResultCard
              interpretation={interpretation}
              analyteName={effectiveObservation?.analyte_raw}
              value={effectiveObservation?.value}
              unit={effectiveObservation?.unit ?? undefined}
              refLow={effectiveObservation?.ref_low}
              refHigh={effectiveObservation?.ref_high}
              onRegenerate={handleGenerateInterpretation}
              isRegenerating={generateInterpretation.isPending}
            />
          ) : !interpLoading && effectiveObservation ? (
            <Card>
              <CardContent className="py-8">
                <div className="text-center space-y-3">
                  <Brain className="w-10 h-10 text-ink-tertiary mx-auto" />
                  <div>
                    <p className="text-sm font-medium text-ink">
                      No interpretation yet
                    </p>
                    <p className="text-xs text-ink-secondary mt-1">
                      Generate an AI interpretation for{' '}
                      {effectiveObservation.analyte_raw}
                    </p>
                  </div>
                  <Button
                    onClick={handleGenerateInterpretation}
                    disabled={generateInterpretation.isPending}
                    className="gap-2"
                  >
                    {generateInterpretation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Sparkles className="w-4 h-4" />
                    )}
                    Generate Interpretation
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : interpLoading ? (
            <Card>
              <CardContent className="py-8">
                <div className="flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-accent" />
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>

        {/* Analyte Sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Lab Results</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-black/[0.04]">
                {analyteList.map((obs, index) => (
                  <motion.button
                    key={obs.analyte_canonical}
                    initial={prefersReducedMotion ? {} : { opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.03 }}
                    onClick={() => setSelectedObservation(obs)}
                    className={cn(
                      'w-full flex items-center justify-between p-4 text-left transition-colors',
                      'hover:bg-surface-muted/50 focus:outline-none focus:bg-accent-subtle',
                      effectiveObservation?.analyte_canonical === obs.analyte_canonical &&
                        'bg-accent-subtle'
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink text-sm truncate">
                        {obs.analyte_raw}
                      </p>
                      <p className="text-xs text-ink-secondary mt-0.5">
                        {obs.value ?? obs.value_text} {obs.unit}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      {obs.is_abnormal && (
                        <Badge variant="attention" className="text-[10px] px-1.5 py-0.5">
                          !
                        </Badge>
                      )}
                      <ChevronRight className="w-4 h-4 text-ink-tertiary" />
                    </div>
                  </motion.button>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
