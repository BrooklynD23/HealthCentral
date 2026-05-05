import { useState, useCallback } from 'react';
import {
  Pill,
  Plus,
  AlertTriangle,
} from 'lucide-react';
import { Button, StaggerGroup, StaggerItem, ListSkeleton, EmptyState } from '@/components/ui';
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
  useLogDose,
} from '@/services/medications';
import { useNavigate } from 'react-router-dom';
import type { MedicationCreate, Medication, BadgeInfo } from '@/services/types';

export function MedicationCoach() {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [loggingMed, setLoggingMed] = useState<Medication | null>(null);
  const [earnedBadge, setEarnedBadge] = useState<BadgeInfo | null>(null);
  const dismissBadge = useCallback(() => setEarnedBadge(null), []);

  const {
    data: medications,
    isLoading,
    isError,
  } = useMedications(true);

  const createMedication = useCreateMedication();
  const logDose = useLogDose();

  const handleCreate = (data: MedicationCreate) => {
    createMedication.mutate(data, {
      onSuccess: () => setShowForm(false),
    });
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

      {/* Add Medication Form */}
      {showForm && (
        <MedicationForm
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          isSubmitting={createMedication.isPending}
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

      {/* Achievements */}
      <AchievementsWidget />

      {/* Badge Toast */}
      <BadgeToast badge={earnedBadge} onDismiss={dismissBadge} />

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
                    setEarnedBadge(badges[0]);
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
