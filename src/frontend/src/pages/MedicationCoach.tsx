import { useState, useCallback } from 'react';
import {
  Pill,
  Plus,
  AlertTriangle,
  FileSearch,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StaggerGroup,
  StaggerItem,
  ListSkeleton,
  EmptyState,
} from '@/components/ui';
import {
  MedicationCard,
  MedicationForm,
  DoseLoggingModal,
  BadgeToast,
  AchievementsWidget,
} from '@/components/medication-coach';
import {
  useMedications,
  useCreateMedication,
  useUpdateMedication,
  useLogDose,
} from '@/services/medications';
import { useDocuments, useMedReconciliation } from '@/services';
import type { MedReconcileSuggestion } from '@/services';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import type { MedicationCreate, Medication, BadgeInfo } from '@/services/types';

/**
 * Record-keeping labels for reconciliation suggestions. These describe the
 * difference between the note and the list — never an instruction or a
 * recommendation. The app never changes the list from a suggestion; the
 * user reviews and submits the normal medication form.
 */
const SUGGESTION_LABELS: Record<MedReconcileSuggestion['suggestion_type'], string> = {
  new_medication: 'Not on your list',
  stopped_medication: 'Active on your list',
  dose_or_frequency_change: 'Differs from your list',
  possible_duplicate: 'Already on your list',
  unclear: 'Could not be matched',
};

function SuggestionCard({
  suggestion,
  matchedMedication,
  onReviewAdd,
  onReviewEntry,
}: {
  suggestion: MedReconcileSuggestion;
  matchedMedication: Medication | null;
  onReviewAdd: (name: string) => void;
  onReviewEntry: (medication: Medication) => void;
}) {
  const quote = suggestion.source_quote || suggestion.entity_value;
  const showAdd =
    suggestion.suggestion_type === 'new_medication' && !!suggestion.drug_name;
  const showReview = matchedMedication !== null;

  return (
    <div className="flex items-start justify-between gap-4 p-4 rounded-xl border border-black/[0.06] bg-surface-muted">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide text-ink-tertiary">
          {SUGGESTION_LABELS[suggestion.suggestion_type]}
        </p>
        <p className="text-sm text-ink mt-1.5">
          <span className="font-medium">The note says:</span>{' '}
          <span className="italic">&ldquo;{quote}&rdquo;</span>
        </p>
        <p className="text-sm text-ink-secondary mt-1">
          <span className="font-medium">Your list has:</span>{' '}
          {suggestion.current_list_summary}
        </p>
        {suggestion.reason && (
          <p className="text-sm text-ink-tertiary mt-1">{suggestion.reason}</p>
        )}
      </div>
      {showAdd && (
        <Button
          size="sm"
          variant="secondary"
          className="shrink-0"
          onClick={() => onReviewAdd(suggestion.drug_name!)}
        >
          Review and add to your list
        </Button>
      )}
      {!showAdd && showReview && (
        <Button
          size="sm"
          variant="secondary"
          className="shrink-0"
          onClick={() => onReviewEntry(matchedMedication)}
        >
          Review this entry
        </Button>
      )}
    </div>
  );
}

function MedReconcilePanel({
  medications,
  onReviewAdd,
  onReviewEntry,
}: {
  medications: Medication[];
  onReviewAdd: (name: string) => void;
  onReviewEntry: (medication: Medication) => void;
}) {
  const profileId = useAuthStore((state) => state.profileId) || '';
  const [selectedDocId, setSelectedDocId] = useState('');

  const { data: documents = [] } = useDocuments({ profile_id: profileId });
  const { data: suggestions = [], isLoading } = useMedReconciliation(
    selectedDocId || undefined
  );

  const medById = new Map(medications.map((med) => [med.id, med]));

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileSearch className="w-5 h-5" />
          Compare with a document
        </CardTitle>
        <p className="text-sm text-ink-secondary mt-1">
          Pick a visit note or discharge summary to see where its medication
          lines differ from your list. Nothing changes unless you review and
          save an entry yourself.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <label
          className="block text-sm font-medium text-ink"
          htmlFor="med-reconcile-doc-select"
        >
          Document
        </label>
        <select
          id="med-reconcile-doc-select"
          className="w-full max-w-md px-3 py-2 rounded-xl border border-black/[0.1] bg-white text-sm text-ink focus-visible:ring-2 focus-visible:ring-accent"
          value={selectedDocId}
          onChange={(event) => setSelectedDocId(event.target.value)}
        >
          <option value="">Select a document...</option>
          {documents.map((doc) => (
            <option key={doc.id} value={doc.id}>
              {doc.source || doc.id}
            </option>
          ))}
        </select>

        {selectedDocId && isLoading && <ListSkeleton count={2} />}
        {selectedDocId && !isLoading && suggestions.length === 0 && (
          <p className="text-sm text-ink-secondary">
            No medication lines in this document differ from your list.
          </p>
        )}
        {suggestions.map((suggestion) => (
          <SuggestionCard
            key={suggestion.source_entity_id ?? suggestion.entity_value}
            suggestion={suggestion}
            matchedMedication={
              suggestion.matched_medication_id
                ? medById.get(suggestion.matched_medication_id) ?? null
                : null
            }
            onReviewAdd={onReviewAdd}
            onReviewEntry={onReviewEntry}
          />
        ))}
      </CardContent>
    </Card>
  );
}

export function MedicationCoach() {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [prefillName, setPrefillName] = useState<string | null>(null);
  const [editingMed, setEditingMed] = useState<Medication | null>(null);
  const [loggingMed, setLoggingMed] = useState<Medication | null>(null);
  const [badgeQueue, setBadgeQueue] = useState<BadgeInfo[]>([]);
  const dismissBadge = useCallback(() => setBadgeQueue((q) => q.slice(1)), []);

  const {
    data: medications,
    isLoading,
    isError,
  } = useMedications(true);

  const createMedication = useCreateMedication();
  const updateMedication = useUpdateMedication();
  const logDose = useLogDose();

  const handleCreate = (data: MedicationCreate) => {
    createMedication.mutate(data, {
      onSuccess: () => {
        setShowForm(false);
        setPrefillName(null);
      },
    });
  };

  const handleUpdate = (data: MedicationCreate) => {
    if (!editingMed) return;
    updateMedication.mutate(
      { medicationId: editingMed.id, data },
      {
        onSuccess: () => setEditingMed(null),
      }
    );
  };

  // A reconciliation suggestion only PRE-FILLS the normal forms below; the
  // user completes and submits them — nothing is applied directly.
  const handleReviewAdd = (name: string) => {
    setEditingMed(null);
    setShowForm(true);
    setPrefillName(name);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleReviewEntry = (medication: Medication) => {
    setShowForm(false);
    setPrefillName(null);
    setEditingMed(medication);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleQuickLog = (medicationId: string) => {
    const med = medications?.find((m) => m.id === medicationId);
    if (med) setLoggingMed(med);
  };

  const handleViewDetail = (medicationId: string) => {
    navigate(`/medications/${medicationId}`);
  };

  // Loading
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-8 w-48 bg-black/[0.05] animate-pulse rounded-lg" />
            <div className="h-4 w-64 bg-black/[0.05] animate-pulse rounded-lg" />
          </div>
          <div className="h-10 w-32 bg-black/[0.05] animate-pulse rounded-xl" />
        </div>
        <ListSkeleton count={4} />
      </div>
    );
  }

  // Error
  if (isError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Failed to load medications</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Medication Coach
          </h1>
          <p className="text-ink-secondary mt-1">
            Track medications, log doses, and monitor adherence
          </p>
        </div>
        <Button onClick={() => setShowForm(true)} className="gap-2">
          <Plus className="w-4 h-4" />
          Add Medication
        </Button>
      </div>

      {/* Add Medication Form (optionally pre-filled from a suggestion) */}
      {(showForm || prefillName !== null) && !editingMed && (
        <MedicationForm
          key={prefillName ?? 'new'}
          mode="add"
          initialValues={prefillName ? { name: prefillName } : undefined}
          onSubmit={handleCreate}
          onCancel={() => {
            setShowForm(false);
            setPrefillName(null);
          }}
          isSubmitting={createMedication.isPending}
        />
      )}

      {/* Edit Medication Form (opened from a reconciliation suggestion) */}
      {editingMed && (
        <MedicationForm
          key={editingMed.id}
          mode="edit"
          initialValues={editingMed}
          onSubmit={handleUpdate}
          onCancel={() => setEditingMed(null)}
          isSubmitting={updateMedication.isPending}
        />
      )}

      {/* Medication List */}
      {!medications || medications.length === 0 ? (
        <EmptyState
          icon={Pill}
          title="No medications"
          description="Add your medications to start tracking doses and adherence."
          action={
            !showForm && (
              <Button onClick={() => setShowForm(true)} className="gap-2">
                <Plus className="w-4 h-4" />
                Add Your First Medication
              </Button>
            )
          }
        />
      ) : (
        <StaggerGroup className="space-y-3">
          {medications.map((med, index) => (
            <StaggerItem key={med.id}>
              <MedicationCard
                medication={med}
                onQuickLog={handleQuickLog}
                onViewDetail={handleViewDetail}
                index={index}
              />
            </StaggerItem>
          ))}
        </StaggerGroup>
      )}

      {/* Reconciliation panel (HC-M19): read-only comparison against a
          document; suggestions only pre-fill the forms above. */}
      <MedReconcilePanel
        medications={medications ?? []}
        onReviewAdd={handleReviewAdd}
        onReviewEntry={handleReviewEntry}
      />

      {/* Achievements */}
      <AchievementsWidget />

      {/* Badge Toast */}
      <BadgeToast badge={badgeQueue[0] ?? null} onDismiss={dismissBadge} />

      {/* Dose Logging Modal */}
      {loggingMed && (
        <DoseLoggingModal
          medicationName={loggingMed.name}
          onSubmit={(data) => {
            logDose.mutate(
              { medicationId: loggingMed.id, data },
              {
                onSuccess: (response) => {
                  setLoggingMed(null);
                  const badges = response?.newly_earned_badges;
                  if (badges && badges.length > 0) {
                    setBadgeQueue((q) => [...q, ...badges]);
                  }
                },
              }
            );
          }}
          onClose={() => setLoggingMed(null)}
          isSubmitting={logDose.isPending}
        />
      )}
    </div>
  );
}
