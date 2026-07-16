import { FormEvent, useEffect, useState } from 'react';
import { Download, FolderOpen, Loader2, Plus, Trash2 } from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Input } from '@/components/ui';
import {
  downloadVisitPrep,
  useCreatePinboard,
  useDeletePinboard,
  useExportPinboard,
  usePinboardItems,
  usePinboards,
  useRemovePinboardItem,
  useRenamePinboard,
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
  const createBoard = useCreatePinboard();
  const renameBoard = useRenamePinboard();
  const deleteBoard = useDeletePinboard();
  const removeItem = useRemovePinboardItem();
  const exportBoard = useExportPinboard();
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

  const handleRename = () => {
    if (!selected) return;
    const name = window.prompt('Pinboard name', selected.name)?.trim();
    if (name) renameBoard.mutate({ pinboardId: selected.id, name });
  };

  const handleDelete = () => {
    if (selected && window.confirm(`Delete "${selected.name}"?`)) {
      deleteBoard.mutate(selected.id);
    }
  };

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
    return <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin" /></div>;
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
        <Input value={newName} onChange={(event) => setNewName(event.target.value)}
          placeholder="New pinboard name" aria-label="New pinboard name" />
        <Button type="submit" className="gap-1.5" disabled={!newName.trim() || createBoard.isPending}>
          <Plus className="h-4 w-4" /> Create
        </Button>
      </form>

      {pinboards.length === 0 ? (
        <EmptyState icon={FolderOpen} title="No pinboards yet"
          description="Create one, then pin records from the inbox or timeline." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
          <Card><CardContent className="p-2">
            {pinboards.map((board) => (
              <button key={board.id} type="button" onClick={() => selectBoard(board.id)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm ${
                  board.id === selectedId ? 'bg-accent-subtle text-accent' : 'text-ink-secondary hover:bg-surface-muted'
                }`}>
                {board.name}
              </button>
            ))}
          </CardContent></Card>

          {selected && <div className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>{selected.name}</CardTitle>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={handleRename}>Rename</Button>
                  <Button variant="ghost" size="icon" aria-label="Delete pinboard" onClick={handleDelete}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {items.length === 0 ? <p className="text-sm text-ink-secondary">No pinned items yet.</p> : (
                  <ul className="divide-y divide-black/[0.05]">
                    {items.map((item) => <li key={item.id} className="flex items-center justify-between py-3">
                      <div><p className="text-sm font-medium text-ink">{ITEM_LABELS[item.item_type]}</p>
                        <p className="font-mono text-xs text-ink-tertiary">{item.item_id}</p></div>
                      <Button variant="ghost" size="icon" aria-label="Remove pinned item"
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
    </div>
  );
}
