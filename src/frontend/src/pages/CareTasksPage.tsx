/**
 * Care Tasks Page (HC-M15)
 *
 * Follow-up checklist derived from visit notes. Candidates extracted from a
 * selected document are shown at the top and become tasks only when the user
 * explicitly accepts them ("Add to checklist"). Every task shows the
 * clinician's exact recorded words ("The note says: ...") — these are the
 * note's instructions, never app recommendations.
 */

import { useState } from 'react';
import {
  AlertTriangle,
  Calendar,
  CheckCircle,
  ClipboardList,
  Plus,
  RotateCcw,
  XCircle,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge, ListSkeleton, EmptyState } from '@/components/ui';
import {
  useCareTasks,
  useCareTaskCandidates,
  useAcceptCareTask,
  useUpdateCareTask,
  useDocuments,
  type CarePlanTask,
  type CareTaskCandidate,
  type CareTaskStatus,
} from '@/services';
import { useAuthStore } from '@/stores/authStore';

const STATUS_ORDER: CareTaskStatus[] = ['needs_review', 'open', 'done', 'ignored'];

const STATUS_LABELS: Record<CareTaskStatus, string> = {
  needs_review: 'Needs review',
  open: 'Open',
  done: 'Done',
  ignored: 'Ignored',
};

function formatDueDate(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function SourceQuote({ quote }: { quote: string | null }) {
  if (!quote) return null;
  return (
    <p className="text-sm text-ink-secondary mt-2">
      <span className="font-medium">The note says:</span>{' '}
      <span className="italic">&ldquo;{quote}&rdquo;</span>
    </p>
  );
}

function CandidateCard({
  candidate,
  onAccept,
  isAccepting,
}: {
  candidate: CareTaskCandidate;
  onAccept: (candidate: CareTaskCandidate) => void;
  isAccepting: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4 p-4 rounded-xl border border-black/[0.06] bg-surface-muted">
      <div className="min-w-0">
        <p className="font-medium text-ink">{candidate.title}</p>
        {candidate.due_date && (
          <p className="text-sm text-ink-secondary mt-1 flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            Suggested due {formatDueDate(candidate.due_date)}
          </p>
        )}
        {candidate.suggested_status === 'needs_review' && (
          <p className="text-sm text-ink-secondary mt-1">
            No clear date in the note — review the timing yourself.
          </p>
        )}
        <SourceQuote quote={candidate.source_quote} />
      </div>
      <Button
        size="sm"
        className="gap-1.5 shrink-0"
        onClick={() => onAccept(candidate)}
        disabled={isAccepting || !candidate.source_entity_id}
      >
        <Plus className="w-4 h-4" />
        Add to checklist
      </Button>
    </div>
  );
}

function TaskCard({
  task,
  onSetStatus,
  isUpdating,
}: {
  task: CarePlanTask;
  onSetStatus: (taskId: string, status: CareTaskStatus) => void;
  isUpdating: boolean;
}) {
  const isClosed = task.status === 'done' || task.status === 'ignored';
  return (
    <div className="flex items-start justify-between gap-4 p-4 rounded-xl border border-black/[0.06] bg-white/60">
      <div className="min-w-0">
        <p className={isClosed ? 'font-medium text-ink-secondary line-through' : 'font-medium text-ink'}>
          {task.title}
        </p>
        {task.due_date && (
          <p className="text-sm text-ink-secondary mt-1 flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            Due {formatDueDate(task.due_date)}
          </p>
        )}
        <SourceQuote quote={task.source_quote} />
        {task.user_note && (
          <p className="text-sm text-ink-tertiary mt-1">Note to self: {task.user_note}</p>
        )}
      </div>
      <div className="flex gap-2 shrink-0">
        {isClosed ? (
          <Button
            size="sm"
            variant="secondary"
            className="gap-1.5"
            onClick={() => onSetStatus(task.id, 'open')}
            disabled={isUpdating}
          >
            <RotateCcw className="w-4 h-4" />
            Reopen
          </Button>
        ) : (
          <>
            <Button
              size="sm"
              className="gap-1.5"
              onClick={() => onSetStatus(task.id, 'done')}
              disabled={isUpdating}
            >
              <CheckCircle className="w-4 h-4" />
              Done
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="gap-1.5"
              onClick={() => onSetStatus(task.id, 'ignored')}
              disabled={isUpdating}
            >
              <XCircle className="w-4 h-4" />
              Ignore
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

export function CareTasksPage() {
  const profileId = useAuthStore((state) => state.profileId) || '';
  const [selectedDocId, setSelectedDocId] = useState('');

  const { data: tasks, isLoading, isError } = useCareTasks();
  const { data: documents = [] } = useDocuments({ profile_id: profileId });
  const { data: candidates = [], isLoading: candidatesLoading } =
    useCareTaskCandidates(selectedDocId || undefined);

  const acceptTask = useAcceptCareTask();
  const updateTask = useUpdateCareTask();

  const handleAccept = (candidate: CareTaskCandidate) => {
    if (!candidate.source_entity_id || !candidate.source_document_id) return;
    acceptTask.mutate({
      source_entity_id: candidate.source_entity_id,
      source_document_id: candidate.source_document_id,
      source_quote: candidate.source_quote,
    });
  };

  const handleSetStatus = (taskId: string, status: CareTaskStatus) => {
    updateTask.mutate({ taskId, data: { status } });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="h-8 w-48 bg-black/[0.05] animate-pulse rounded-lg" />
          <div className="h-4 w-64 bg-black/[0.05] animate-pulse rounded-lg" />
        </div>
        <ListSkeleton count={4} />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-status-attention mx-auto mb-3" />
          <p className="text-ink-secondary">Failed to load care tasks</p>
        </div>
      </div>
    );
  }

  const grouped = STATUS_ORDER.map((status) => ({
    status,
    items: (tasks ?? []).filter((task) => task.status === status),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Care Tasks
        </h1>
        <p className="text-ink-secondary mt-1">
          Follow-up items from your visit notes. Each one shows the exact words
          your clinician recorded — nothing here is app advice.
        </p>
      </div>

      {/* Candidates panel */}
      <Card>
        <CardHeader>
          <CardTitle>Suggested from your documents</CardTitle>
          <p className="text-sm text-ink-secondary mt-1">
            Pick a document to see follow-up instructions found in it. Nothing
            is added to your checklist until you accept it.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <label className="block text-sm font-medium text-ink" htmlFor="care-task-doc-select">
            Document
          </label>
          <select
            id="care-task-doc-select"
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

          {selectedDocId && candidatesLoading && <ListSkeleton count={2} />}
          {selectedDocId && !candidatesLoading && candidates.length === 0 && (
            <p className="text-sm text-ink-secondary">
              No new follow-up suggestions in this document.
            </p>
          )}
          {candidates.map((candidate) => (
            <CandidateCard
              key={candidate.source_entity_id ?? candidate.title}
              candidate={candidate}
              onAccept={handleAccept}
              isAccepting={acceptTask.isPending}
            />
          ))}
        </CardContent>
      </Card>

      {/* Task checklist grouped by status */}
      {grouped.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No care tasks yet"
          description="Accept follow-up suggestions from a visit note above to build your checklist."
        />
      ) : (
        grouped.map((group) => (
          <section key={group.status} aria-label={STATUS_LABELS[group.status]}>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="font-display text-lg font-semibold text-ink">
                {STATUS_LABELS[group.status]}
              </h2>
              <Badge>{group.items.length}</Badge>
            </div>
            <div className="space-y-3">
              {group.items.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  onSetStatus={handleSetStatus}
                  isUpdating={updateTask.isPending}
                />
              ))}
            </div>
          </section>
        ))
      )}
    </div>
  );
}
