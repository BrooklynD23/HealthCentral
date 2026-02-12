import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  AlertTriangle,
  Edit3,
  Eye,
  ChevronDown,
  FileText,
  Info,
  Loader2,
  X,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useObservations, useVerifyObservation } from '@/services/observations';
import { useAuthStore } from '@/stores/authStore';
import { apiGet } from '@/services/api';
import type { Observation, DocumentPage } from '@/services/types';

export function VerificationWorkbench() {
  const prefersReducedMotion = useReducedMotion();
  const { profileId } = useAuthStore();
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [editingObservation, setEditingObservation] = useState<Observation | null>(null);
  const [editValue, setEditValue] = useState('');
  const [sourcePages, setSourcePages] = useState<DocumentPage[]>([]);
  const [loadingSource, setLoadingSource] = useState(false);

  // Fetch observations that need verification
  const {
    data: observations,
    isLoading,
    isError,
    error,
  } = useObservations({
    profile_id: profileId || '',
    needs_verification: true,
  });

  const verifyMutation = useVerifyObservation();

  const handleVerify = async (observation: Observation) => {
    await verifyMutation.mutateAsync({
      observationId: observation.id,
      data: {},
    });
  };

  const handleEdit = (observation: Observation) => {
    setEditingObservation(observation);
    setEditValue(observation.value?.toString() || observation.value_text || '');
  };

  const handleSaveEdit = async () => {
    if (!editingObservation) return;

    const newValue = parseFloat(editValue);
    await verifyMutation.mutateAsync({
      observationId: editingObservation.id,
      data: {
        value: isNaN(newValue) ? undefined : newValue,
        value_text: isNaN(newValue) ? editValue : undefined,
      },
    });
    setEditingObservation(null);
  };

  const handleRowSelect = async (observation: Observation) => {
    setSelectedRow(observation.id);

    // Load source document pages
    if (observation.doc_id) {
      setLoadingSource(true);
      try {
        const pages = await apiGet<DocumentPage[]>(
          `/documents/${observation.doc_id}/pages`,
          {}
        );
        setSourcePages(pages);
      } catch {
        setSourcePages([]);
      } finally {
        setLoadingSource(false);
      }
    }
  };

  const getStatusColor = (observation: Observation) => {
    if (observation.flag === 'H' || observation.flag === 'HH' || observation.flag === 'HIGH') {
      return 'text-status-attention';
    }
    if (observation.flag === 'L' || observation.flag === 'LL' || observation.flag === 'LOW') {
      return 'text-status-caution';
    }
    return 'text-ink';
  };

  const getConfidenceBadge = (confidence: number | null) => {
    if (confidence === null) return null;
    if (confidence >= 0.8) {
      return <Badge variant="verified">High Confidence</Badge>;
    }
    if (confidence >= 0.5) {
      return <Badge variant="caution">Medium</Badge>;
    }
    return <Badge variant="attention">Low Confidence</Badge>;
  };

  const formatRefRange = (observation: Observation) => {
    if (observation.ref_range_text) return observation.ref_range_text;
    if (observation.ref_low !== null && observation.ref_high !== null) {
      return `${observation.ref_low}-${observation.ref_high}`;
    }
    return '-';
  };

  // Count unverified items
  const unverifiedCount = observations?.filter((o) => !o.user_verified).length ?? 0;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" role="status" aria-live="polite">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="sr-only">Loading observations for verification...</span>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">
            Failed to load observations: {(error as Error)?.message || 'Unknown error'}
          </p>
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
            Verification Workbench
          </h1>
          <p className="text-ink-secondary mt-1">
            Review and correct extracted values from your documents
          </p>
        </div>
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <CheckCircle className="w-12 h-12 text-status-verified mx-auto mb-3" />
              <p className="text-lg font-medium text-ink mb-1">
                All observations verified
              </p>
              <p className="text-ink-secondary">
                No items need review at this time.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Verification Workbench
          </h1>
          <p className="text-ink-secondary mt-1">
            Review and correct extracted values from your documents
          </p>
        </div>
        <div className="flex items-center gap-3">
          {unverifiedCount > 0 && (
            <Badge variant="caution" className="gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              {unverifiedCount} items need review
            </Badge>
          )}
          <Button variant="secondary" className="gap-2">
            <Eye className="w-4 h-4" />
            View Source
          </Button>
          <Button className="gap-2">
            <CheckCircle className="w-4 h-4" />
            Mark All Verified
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-ink-secondary" />
                Lab Results
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-black/[0.04] bg-surface-muted/50">
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Test Name
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Value
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Reference Range
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Status
                      </th>
                      <th className="text-right text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {observations.map((observation, index) => (
                      <motion.tr
                        key={observation.id}
                        initial={prefersReducedMotion ? {} : { opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={cn(
                          'border-b border-black/[0.04] transition-colors cursor-pointer',
                          selectedRow === observation.id
                            ? 'bg-accent-subtle'
                            : 'hover:bg-surface-muted/50'
                        )}
                        onClick={() => handleRowSelect(observation)}
                      >
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-ink">
                              {observation.analyte_raw}
                            </span>
                            {observation.user_verified && (
                              <Badge variant="verified" className="text-xs gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Verified
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span
                            className={cn(
                              'font-mono font-semibold',
                              getStatusColor(observation)
                            )}
                          >
                            {observation.value ?? observation.value_text ?? '-'}
                          </span>
                          <span className="text-ink-secondary ml-1 text-sm">
                            {observation.unit}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-sm text-ink-secondary font-mono">
                          {formatRefRange(observation)} {observation.unit}
                        </td>
                        <td className="px-4 py-4">
                          {getConfidenceBadge(observation.extraction_confidence)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Edit value"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleEdit(observation);
                              }}
                            >
                              <Edit3 className="w-4 h-4" />
                            </Button>
                            {!observation.user_verified && (
                              <Button
                                variant="ghost"
                                size="sm"
                                aria-label="Verify observation"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleVerify(observation);
                                }}
                                disabled={verifyMutation.isPending}
                              >
                                {verifyMutation.isPending ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  'Verify'
                                )}
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedRow(
                                  expandedRow === observation.id ? null : observation.id
                                );
                              }}
                              aria-label="Expand details"
                            >
                              <ChevronDown
                                className={cn(
                                  'w-4 h-4 transition-transform',
                                  expandedRow === observation.id && 'rotate-180'
                                )}
                              />
                            </Button>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source Preview</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingSource ? (
                <div className="aspect-[3/4] rounded-xl bg-surface-muted flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-accent" />
                </div>
              ) : sourcePages.length > 0 ? (
                <div className="aspect-[3/4] rounded-xl bg-surface-muted p-4 overflow-auto">
                  {sourcePages.map((page) => (
                    <div key={page.page_number} className="mb-4">
                      <p className="text-xs font-medium text-ink-secondary mb-2">
                        Page {page.page_number}
                      </p>
                      <p className="text-sm text-ink whitespace-pre-wrap font-mono">
                        {page.text}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="aspect-[3/4] rounded-xl bg-surface-muted flex items-center justify-center">
                  <div className="text-center p-6">
                    <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
                    <p className="text-sm text-ink-secondary">
                      Select a row to preview the source document location
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="bg-status-info-subtle border-status-info/20">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-status-info flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-ink text-sm mb-1">
                    Verification Tips
                  </h4>
                  <p className="text-xs text-ink-secondary leading-relaxed">
                    Click any value to edit. Low confidence items are flagged
                    for your review. All changes are tracked with "Edited"
                    badges.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Edit Modal */}
      {editingObservation && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
        >
          <Card className="w-full max-w-md">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Edit Value</CardTitle>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setEditingObservation(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-ink mb-1 block">
                  {editingObservation.analyte_raw}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="flex-1 px-3 py-2 border border-black/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                    autoFocus
                  />
                  <span className="px-3 py-2 bg-surface-muted rounded-lg text-ink-secondary">
                    {editingObservation.unit}
                  </span>
                </div>
              </div>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="secondary"
                  onClick={() => setEditingObservation(null)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSaveEdit}
                  disabled={verifyMutation.isPending}
                >
                  {verifyMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  Save & Verify
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
