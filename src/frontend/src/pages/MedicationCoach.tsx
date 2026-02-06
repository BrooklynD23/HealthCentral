import { useState } from 'react';
import {
  Pill,
  Plus,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { Button, Card, CardContent } from '@/components/ui';
import {
  MedicationCard,
  MedicationForm,
  DoseLoggingModal,
} from '@/components/medication-coach';
import {
  useMedications,
  useCreateMedication,
  useLogDose,
} from '@/services/medications';
import { useNavigate } from 'react-router-dom';
import type { MedicationCreate, Medication } from '@/services/types';

export function MedicationCoach() {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [loggingMed, setLoggingMed] = useState<Medication | null>(null);

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
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
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
        <Card>
          <CardContent className="py-16">
            <div className="text-center">
              <Pill className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
              <p className="text-lg font-medium text-ink mb-1">
                No medications
              </p>
              <p className="text-ink-secondary mb-4">
                Add your medications to start tracking doses and adherence.
              </p>
              {!showForm && (
                <Button onClick={() => setShowForm(true)} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Add Your First Medication
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {medications.map((med, index) => (
            <MedicationCard
              key={med.id}
              medication={med}
              onQuickLog={handleQuickLog}
              onViewDetail={handleViewDetail}
              index={index}
            />
          ))}
        </div>
      )}

      {/* Dose Logging Modal */}
      {loggingMed && (
        <DoseLoggingModal
          medicationName={loggingMed.name}
          onSubmit={(data) => {
            logDose.mutate(
              { medicationId: loggingMed.id, data },
              { onSuccess: () => setLoggingMed(null) }
            );
          }}
          onClose={() => setLoggingMed(null)}
          isSubmitting={logDose.isPending}
        />
      )}
    </div>
  );
}
