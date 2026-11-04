import { FormEvent, useEffect, useRef, useState } from 'react';
import { Download, FolderOpen, Loader2, Plus, Trash2 } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Input } from '@/components/ui';
import { AlertDialog } from '@/components/ui/AlertDialog';
import { Dialog } from '@/components/ui/Dialog';
import {
  downloadVisitPrep,
  useCreatePinboard,
  useDeletePinboard,
  useExportPinboard,
  usePinboardItems,
  usePinboards,
  useRemovePinboardItem,
  useRenamePinboard,
  type Pinboard,
} from '@/services';

const ITEM_LABELS = {
  document: 'Document',
  observation: 'Observation',
  care_task: 'Care task',
  question: 'Doctor question',
};

export function PinboardsPage() {
  const { data: pinboards = [], isLoading } = usePinboards();
  const [selectedId, setSelectedId] = useState('');
  const [newName, setNewName] = useState('');
  const [reason, setReason] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [lastExportBoardId, setLastExportBoardId] = useState<string | null>(null);
  // Rename and Delete ask through dialogs. The target is the board that was selected when the dialog opened.
  const [renameTarget, setRenameTarget] = useState<Pinboard | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [renameFailed, setRenameFailed] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Pinboard | null>(null);
  const [deleteFailed, setDeleteFailed] = useState(false);
  const [deletedId, setDeletedId] = useState<string | null>(null);
  const renameButton = useRef<HTMLButtonElement>(null);
  const deleteButton = useRef<HTMLButtonElement>(null);
  const createBoard = useCreatePinboard();
  const renameBoard = useRenamePinboard();
  const deleteBoard = useDeletePinboard();
  const removeItem = useRemovePinboardItem();
  const exportBoard = useExportPinboard();
  const newNameInput = useRef<HTMLInputElement>(null);
  const { data: items = [] } = usePinboardItems(selectedId || undefined);

  const selectBoard = (boardId: string) => {
    setSelectedId(boardId);
    setReason('');
    setConfirmed(false);
    setLastExportBoardId(null);
    exportBoard.reset();
  };

  useEffect(() => {
    if (!selectedId && pinboards[0]) selectBoard(pinboards[0].id);
    if (selectedId && !pinboards.some((board) => board.id === selectedId)) {
      selectBoard(pinboards[0]?.id ?? '');
    }
    // Selection changes intentionally reset export confirmation and results.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pinboards, selectedId]);

  const selected = pinboards.find((board) => board.id === selectedId);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!newName.trim()) return;
    const board = await createBoard.mutateAsync(newName.trim());
    setNewName('');
    selectBoard(board.id);
  };

  // The dialogs open from buttons, not from Radix triggers, so Radix has no element to give focus back to and focus
  // would fall to <body>. It goes back to the button that opened the dialog. After the render: while the dialog is
  // still open its focus trap would pull the focus straight back.
  const focusLater = (target: () => HTMLElement | null | undefined) =>
    requestAnimationFrame(() => target()?.focus());

  const handleRename = () => {
    if (!selected) return;
    setRenameTarget(selected);
    setRenameValue(selected.name);
    setRenameFailed(false);
  };

  const closeRename = () => {
    setRenameTarget(null);
    setRenameFailed(false);
    focusLater(() => renameButton.current);
  };

  const submitRename = async (event: FormEvent) => {
    event.preventDefault();
    const name = renameValue.trim();
    if (!renameTarget || !name || renameBoard.isPending) return;
    try {
      await renameBoard.mutateAsync({ pinboardId: renameTarget.id, name });
      closeRename();
    } catch {
      // The dialog stays open with the name the patient typed, and says so.
      setRenameFailed(true);
    }
  };

  const handleDelete = () => {
    if (!selected) return;
    setDeleteTarget(selected);
    setDeleteFailed(false);
  };

  const closeDelete = () => {
    setDeleteTarget(null);
    setDeleteFailed(false);
    focusLater(() => deleteButton.current);
  };

  const confirmDelete = async () => {
    if (!deleteTarget || deleteBoard.isPending) return;
    const { id } = deleteTarget;
    try {
      await deleteBoard.mutateAsync(id);
    } catch {
      setDeleteFailed(true);
      return;
    }
    setDeleteTarget(null);
    setDeleteFailed(false);
    setDeletedId(id);
  };

  // After a delete, focus goes to the Delete button of the board that takes its place, or to the new-pinboard box when
  // none is left, so a keyboard user is never dropped on <body>. It waits for the list to drop the board and for the
  // next one to be selected: until then the panel (and its buttons) is replaced, and a focus() would hit a dead node.
  useEffect(() => {
    if (!deletedId || deleteTarget) return;
    if (pinboards.some((board) => board.id === deletedId)) return;
    if (pinboards.length === 0) newNameInput.current?.focus();
    else if (selected && selected.id !== deletedId) deleteButton.current?.focus();
    else return;
    setDeletedId(null);
  }, [deletedId, deleteTarget, pinboards, selected]);

  const handleDownload = async () => {
    if (!exportBoard.data) return;
    const { blob, extension } = await downloadVisitPrep(exportBoard.data.packet_id, 'markdown');
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `pinboard-packet-${exportBoard.data.packet_id.slice(0, 8)}${extension}`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16" role="status" aria-live="polite">
        <Loader2 className="h-6 w-6 motion-safe:animate-spin" />
        <span className="sr-only">Loading pinboards...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">Pinboards</h1>
        <p className="mt-1 text-ink-secondary">
          Keep selected records and follow-up items together for your own review.
        </p>
      </div>

      <form onSubmit={handleCreate} className="flex max-w-xl gap-2">
        <Input ref={newNameInput} value={newName} onChange={(event) => setNewName(event.target.value)}
          placeholder="New pinboard name" aria-label="New pinboard name" />
        <Button type="submit" className="gap-1.5" disabled={!newName.trim() || createBoard.isPending}>
          <Plus className="h-4 w-4" /> Create
        </Button>
      </form>

      {pinboards.length === 0 ? (
        <EmptyState icon={FolderOpen} title="No pinboards yet"
          description="Create one, then pin records from the inbox or timeline."
          action={<Button variant="secondary" onClick={() => newNameInput.current?.focus()}>Name a pinboard</Button>} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
          <Card><CardContent className="p-2">
            {pinboards.map((board) => (
              <button key={board.id} type="button" onClick={() => selectBoard(board.id)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm [overflow-wrap:anywhere] ${
                  board.id === selectedId ? 'bg-accent-subtle text-accent' : 'text-ink-secondary hover:bg-surface-muted'
                }`}>
                {board.name}
              </button>
            ))}
          </CardContent></Card>

          {selected && <div className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between gap-3">
                <CardTitle className="min-w-0 [overflow-wrap:anywhere]">{selected.name}</CardTitle>
                <div className="flex shrink-0 gap-2">
                  <Button ref={renameButton} variant="secondary" size="sm" onClick={handleRename}>Rename</Button>
                  <Button ref={deleteButton} variant="ghost" size="icon" aria-label="Delete pinboard" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {items.length === 0 ? <p className="text-sm text-ink-secondary">No pinned items yet.</p> : (
                  <ul className="divide-y divide-border">
                    {items.map((item) => <li key={item.id} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0 flex-1 [overflow-wrap:anywhere]">
                        <p data-t0 data-pinboard-item-label className="text-sm font-medium text-ink">{ITEM_LABELS[item.item_type]}</p>
                        <p data-t0 data-pinboard-item-id className="font-mono text-xs text-ink-tertiary">{item.item_id}</p></div>
                      <Button variant="ghost" size="icon" className="shrink-0" aria-label="Remove pinned item"
                        onClick={() => removeItem.mutate({ pinboardId: selected.id, itemId: item.id })}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </li>)}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card><CardHeader><CardTitle>Focused packet</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <Input value={reason} onChange={(event) => setReason(event.target.value)}
                  placeholder="Optional record-keeping note" aria-label="Packet note" />
                <label className="flex items-center gap-2 text-sm text-ink-secondary">
                  <input type="checkbox" checked={confirmed}
                    onChange={(event) => setConfirmed(event.target.checked)} />
                  I confirm I want to assemble these selected records into an export.
                </label>
                <div className="flex gap-2">
                  <Button disabled={!confirmed || exportBoard.isPending}
                    onClick={() => exportBoard.mutate(
                      { pinboardId: selected.id,
                        request: { reason_for_visit: reason || null, confirm: true } },
                      { onSuccess: () => setLastExportBoardId(selected.id) },
                    )}>
                    Create packet
                  </Button>
                  {exportBoard.data && lastExportBoardId === selected.id && <Button variant="secondary" className="gap-1.5" onClick={() => void handleDownload()}>
                    <Download className="h-4 w-4" /> Download
                  </Button>}
                </div>
              </CardContent>
            </Card>
          </div>}
        </div>
      )}

      <Dialog
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeRename();
        }}
        title="Rename pinboard"
      >
        <form onSubmit={(event) => void submitRename(event)} className="space-y-4">
          <Input
            label="Pinboard name"
            value={renameValue}
            onChange={(event) => {
              setRenameValue(event.target.value);
              setRenameFailed(false);
            }}
            onFocus={(event) => event.currentTarget.select()}
          />
          {renameFailed && (
            <p role="alert" className="text-sm text-status-critical">
              Could not rename the pinboard. Try again.
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="secondary" onClick={closeRename}>
              Cancel
            </Button>
            <Button type="submit" disabled={!renameValue.trim() || renameBoard.isPending}>
              Save
            </Button>
          </div>
        </form>
      </Dialog>

      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeDelete();
        }}
        title="Delete this pinboard?"
        className="[overflow-wrap:anywhere]"
        description={`Delete "${deleteTarget?.name ?? 'this pinboard'}"? This cannot be undone.`}
      >
        {deleteFailed && (
          <p role="alert" className="mb-3 text-sm text-status-critical">
            Could not delete the pinboard. Try again.
          </p>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" data-alert-cancel onClick={closeDelete}>
            Cancel
          </Button>
          <Button type="button" variant="danger" disabled={deleteBoard.isPending} onClick={() => void confirmDelete()}>
            Delete
          </Button>
        </div>
      </AlertDialog>
    </div>
  );
}
