/**
 * Follow-ups Page (HC-M15, UI-PG-CARE)
 *
 * Follow-up checklist derived from visit notes. Candidates extracted from a
 * selected document are shown at the top and become tasks only when the user
 * explicitly accepts them ("Add to checklist"). Every task shows the
 * clinician's exact recorded words ("The note says: ...") — these are the
 * note's instructions, never app recommendations.
 *
 * Done and Ignore show at once, with an Undo toast. A card keeps the group it
 * was first shown in, so a status change never moves the dates below it (plan
 * G10); the groups re-form on the next visit.
 */

import { useEffect, useRef, useState } from 'react';
import { m } from 'framer-motion';
import { useQueryClient } from '@tanstack/react-query';
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
import { notify } from '@/components/ui/toast';
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

/** The key useCareTasks() writes the unfiltered list under (services/careTasks.ts). */
const TASKS_QUERY_KEY = ['care-tasks', { status: null }] as const;

const SAVE_FAILED = "Couldn't save that change. Try again.";

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
    <div className="flex items-start justify-between gap-4 p-4 rounded-xl border border-black/6 bg-surface-muted">
      <div className="min-w-0">
        <p className="font-medium text-ink">{candidate.title}</p>
        {candidate.due_date && (
          <p data-t0 className="text-sm text-ink-secondary mt-1 flex items-center gap-1.5">
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
  onDone,
  onIgnore,
  onReopen,
  isUpdating,
}: {
  task: CarePlanTask;
  onDone: (task: CarePlanTask) => void;
  onIgnore: (task: CarePlanTask) => void;
  onReopen: (task: CarePlanTask) => void;
  isUpdating: boolean;
}) {
  const isClosed = task.status === 'done' || task.status === 'ignored';
  // The first label of a card shows at once. Only a later change of status fades the new label in (M8).
  const hasMounted = useRef(false);
  useEffect(() => {
    hasMounted.current = true;
  }, []);
  return (
    <div
      data-care-task=""
      className="flex flex-col gap-3 p-4 rounded-xl border border-black/6 bg-surface-elevated/60 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
    >
      <div className="min-w-0">
        {/* The state morph (M8): a 180 ms opacity crossfade of the label. The label row has a fixed height, so a change of
            status moves nothing below it. Nothing with data-t0 sits inside this element. */}
        <m.span
          key={task.status}
          data-care-status={task.status}
          initial={hasMounted.current ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="block h-5 text-xs font-medium text-ink-tertiary"
        >
          {STATUS_LABELS[task.status]}
        </m.span>
        <p className={isClosed ? 'font-medium text-ink-secondary' : 'font-medium text-ink'}>
          {task.title}
        </p>
        {task.due_date && (
          <p data-t0 className="text-sm text-ink-secondary mt-1 flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            Due {formatDueDate(task.due_date)}
          </p>
        )}
        <SourceQuote quote={task.source_quote} />
        {task.user_note && (
          <p className="text-sm text-ink-tertiary mt-1">Note to self: {task.user_note}</p>
        )}
      </div>
      {/* On wide screens the column keeps one width in both states, so the text beside it does not re-wrap. */}
      <div className="flex gap-2 shrink-0 sm:min-w-52 sm:justify-end">
        {isClosed ? (
          <Button
            size="sm"
            variant="secondary"
            className="gap-1.5"
            onClick={() => onReopen(task)}
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
              onClick={() => onDone(task)}
              disabled={isUpdating}
            >
              <CheckCircle className="w-4 h-4" />
              Done
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="gap-1.5"
              onClick={() => onIgnore(task)}
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
  /** The group each task was first shown in (task id -> status at that time). */
  const [shownGroup, setShownGroup] = useState<Record<string, CareTaskStatus>>({});
  const documentPickerRef = useRef<HTMLSelectElement>(null);
  const queryClient = useQueryClient();

  const { data: tasks, isLoading, isError } = useCareTasks();
  const { data: documents = [] } = useDocuments({ profile_id: profileId });
  const { data: candidates = [], isLoading: candidatesLoading } =
    useCareTaskCandidates(selectedDocId || undefined);

  const acceptTask = useAcceptCareTask();
  const updateTask = useUpdateCareTask();

  // A task keeps the group it was first shown in. A task that arrives later is recorded when it first appears.
  useEffect(() => {
    if (!tasks) return;
    setShownGroup((known) => {
      const unseen = tasks.filter((task) => !(task.id in known));
      if (unseen.length === 0) return known;
      return { ...known, ...Object.fromEntries(unseen.map((task) => [task.id, task.status])) };
    });
  }, [tasks]);

  /**
   * Shows a status change at once, then sends it. A failed save puts that task back as it was and says so. The
   * server's answer refreshes the list (useUpdateCareTask), so the list ends on the saved state.
   *
   * The callbacks are attached with mutateAsync, which reports every save. mutate() reports only the latest one,
   * so a second save started meanwhile (the Undo of another card) would drop this save's error.
   */
  const changeStatus = async (taskId: string, status: CareTaskStatus, onSaved?: () => void) => {
    // A refetch still in flight would answer with the old status and overwrite the change shown here.
    await queryClient.cancelQueries({ queryKey: TASKS_QUERY_KEY });
    const previous = queryClient.getQueryData<CarePlanTask[]>(TASKS_QUERY_KEY)?.find((task) => task.id === taskId)?.status;
    const show = (shown: CareTaskStatus) =>
      queryClient.setQueryData<CarePlanTask[]>(TASKS_QUERY_KEY, (current) =>
        current?.map((task) => (task.id === taskId ? { ...task, status: shown } : task))
      );
    show(status);
    await updateTask.mutateAsync({ taskId, data: { status } }).then(onSaved, () => {
      if (previous) show(previous);
      void queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
      notify({ message: SAVE_FAILED });
    });
  };

  /** Done or Ignore: the Undo toast returns the task to the status it had before. */
  const closeTask = (task: CarePlanTask, status: 'done' | 'ignored', message: string) => {
    const previous = task.status;
    void changeStatus(task.id, status, () => {
      notify({
        message,
        action: { label: 'Undo', onClick: () => void changeStatus(task.id, previous) },
      });
    });
  };

  const handleAccept = (candidate: CareTaskCandidate) => {
    if (!candidate.source_entity_id || !candidate.source_document_id) return;
    acceptTask.mutate({
      source_entity_id: candidate.source_entity_id,
      source_document_id: candidate.source_document_id,
      source_quote: candidate.source_quote,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <div className="h-8 w-48 bg-black/5 animate-pulse rounded-lg" />
          <div className="h-4 w-64 bg-black/5 animate-pulse rounded-lg" />
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
    items: (tasks ?? []).filter((task) => (shownGroup[task.id] ?? task.status) === status),
  })).filter((group) => group.items.length > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
          Follow-ups
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
          <p className="text-sm text-ink-secondary">
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
            ref={documentPickerRef}
            className="w-full max-w-md px-3 py-2 rounded-xl border border-black/10 bg-surface-elevated text-sm text-ink focus-visible:ring-2 focus-visible:ring-accent"
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
          title="No follow-ups yet"
          description="Accept follow-up suggestions from a visit note above to build your checklist."
          action={
            <Button variant="secondary" onClick={() => documentPickerRef.current?.focus()}>
              Choose a document
            </Button>
          }
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
                  onDone={(item) => closeTask(item, 'done', 'Marked as done.')}
                  onIgnore={(item) => closeTask(item, 'ignored', 'Marked as ignored.')}
                  onReopen={(item) => void changeStatus(item.id, 'open')}
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
