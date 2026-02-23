/**
 * MemoryManager — UI for viewing, creating, editing, and deleting assistant memory items.
 *
 * ASSIST-MEM-002: Card-based list with add/edit/delete, category filter, confirmation dialog.
 */

import { useState, type FC } from 'react';
import {
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  Brain,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { Button, Card, CardContent, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import {
  useMemoryItems,
  useCreateMemoryItem,
  useUpdateMemoryItem,
  useDeleteMemoryItem,
} from '@/services/memory';
import type { MemoryItem } from '@/services/types';

const CATEGORIES = ['medical', 'preferences', 'context', 'other'] as const;

export const MemoryManager: FC = () => {
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>(undefined);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Form state
  const [formKey, setFormKey] = useState('');
  const [formValue, setFormValue] = useState('');
  const [formCategory, setFormCategory] = useState('');

  const { data: items, isLoading, isError } = useMemoryItems(categoryFilter);
  const createMutation = useCreateMemoryItem();
  const updateMutation = useUpdateMemoryItem();
  const deleteMutation = useDeleteMemoryItem();

  const resetForm = () => {
    setFormKey('');
    setFormValue('');
    setFormCategory('');
    setShowAddForm(false);
    setEditingId(null);
  };

  const handleCreate = async () => {
    if (!formKey.trim() || !formValue.trim()) return;
    await createMutation.mutateAsync({
      key: formKey.trim(),
      value: formValue.trim(),
      category: formCategory || undefined,
    });
    resetForm();
  };

  const handleEdit = (item: MemoryItem) => {
    setEditingId(item.id);
    setFormKey(item.key);
    setFormValue(item.value);
    setFormCategory(item.category || '');
    setShowAddForm(false);
  };

  const handleUpdate = async () => {
    if (!editingId || !formKey.trim() || !formValue.trim()) return;
    await updateMutation.mutateAsync({
      id: editingId,
      data: {
        key: formKey.trim(),
        value: formValue.trim(),
        category: formCategory || undefined,
      },
    });
    resetForm();
  };

  const handleDelete = async (id: string) => {
    await deleteMutation.mutateAsync(id);
    setDeleteConfirmId(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="w-6 h-6 animate-spin text-accent" />
      </div>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <AlertTriangle className="w-8 h-8 text-status-attention mx-auto mb-2" />
          <p className="text-sm text-ink-secondary">Failed to load memory items.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-display font-semibold text-ink">
            Assistant Memory
          </h2>
          <Badge variant="default">{items?.length ?? 0}</Badge>
        </div>
        <Button
          size="sm"
          className="gap-1.5"
          onClick={() => {
            resetForm();
            setShowAddForm(true);
          }}
        >
          <Plus className="w-4 h-4" />
          Add
        </Button>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setCategoryFilter(undefined)}
          className={cn(
            'px-3 py-1 rounded-lg text-xs font-medium transition-colors',
            !categoryFilter
              ? 'bg-accent text-white'
              : 'bg-surface-muted text-ink-secondary hover:bg-surface-sunken'
          )}
        >
          All
        </button>
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategoryFilter(cat)}
            className={cn(
              'px-3 py-1 rounded-lg text-xs font-medium transition-colors capitalize',
              categoryFilter === cat
                ? 'bg-accent text-white'
                : 'bg-surface-muted text-ink-secondary hover:bg-surface-sunken'
            )}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Add/Edit form */}
      {(showAddForm || editingId) && (
        <Card>
          <CardContent className="p-4 space-y-3">
            <div>
              <label className="text-xs font-medium text-ink-secondary block mb-1">Key</label>
              <input
                type="text"
                value={formKey}
                onChange={(e) => setFormKey(e.target.value)}
                placeholder="e.g., allergy, preference"
                className="w-full px-3 py-2 text-sm border border-black/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                maxLength={255}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-ink-secondary block mb-1">Value</label>
              <textarea
                value={formValue}
                onChange={(e) => setFormValue(e.target.value)}
                placeholder="Enter memory content..."
                className="w-full px-3 py-2 text-sm border border-black/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent resize-none"
                rows={3}
                maxLength={10000}
              />
            </div>
            <div>
              <label className="text-xs font-medium text-ink-secondary block mb-1">Category</label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-black/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent bg-white"
              >
                <option value="">None</option>
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" size="sm" onClick={resetForm}>
                <X className="w-3.5 h-3.5 mr-1" />
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={editingId ? handleUpdate : handleCreate}
                disabled={
                  !formKey.trim() ||
                  !formValue.trim() ||
                  createMutation.isPending ||
                  updateMutation.isPending
                }
              >
                {(createMutation.isPending || updateMutation.isPending) ? (
                  <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />
                ) : (
                  <Save className="w-3.5 h-3.5 mr-1" />
                )}
                {editingId ? 'Update' : 'Save'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Items list */}
      {!items || items.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center">
            <Brain className="w-10 h-10 text-ink-tertiary mx-auto mb-2" />
            <p className="text-sm text-ink-secondary">
              No memory items yet. Add something the assistant should remember.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium text-ink truncate">
                        {item.key}
                      </p>
                      {item.category && (
                        <Badge variant="default" className="text-xs capitalize">
                          {item.category}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-ink-secondary whitespace-pre-wrap break-words">
                      {item.value}
                    </p>
                    <p className="text-xs text-ink-tertiary mt-1">
                      Updated {new Date(item.updated_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Edit ${item.key}`}
                      onClick={() => handleEdit(item)}
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </Button>
                    {deleteConfirmId === item.id ? (
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label="Confirm delete"
                          className="text-status-attention"
                          onClick={() => handleDelete(item.id)}
                          disabled={deleteMutation.isPending}
                        >
                          {deleteMutation.isPending ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label="Cancel delete"
                          onClick={() => setDeleteConfirmId(null)}
                        >
                          <X className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    ) : (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${item.key}`}
                        onClick={() => setDeleteConfirmId(item.id)}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
