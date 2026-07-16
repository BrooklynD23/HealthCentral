import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '@/services/api';
import {
  addPinboardItem,
  createPinboard,
  deletePinboard,
  exportPinboard,
  listPinboardItems,
  listPinboards,
  removePinboardItem,
  renamePinboard,
} from '@/services/pinboards';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

describe('Pinboards service contract', () => {
  beforeEach(() => vi.clearAllMocks());

  it('FE-PIN-API-001: lists and creates pinboards', async () => {
    await listPinboards();
    await createPinboard('Visit records');
    expect(api.apiGet).toHaveBeenCalledWith('/pinboards/');
    expect(api.apiPost).toHaveBeenCalledWith('/pinboards/', { name: 'Visit records' });
  });

  it('FE-PIN-API-002: renames and deletes a pinboard', async () => {
    await renamePinboard('board-1', 'Records to discuss');
    await deletePinboard('board-1');
    expect(api.apiPatch).toHaveBeenCalledWith('/pinboards/board-1', {
      name: 'Records to discuss',
    });
    expect(api.apiDelete).toHaveBeenCalledWith('/pinboards/board-1');
  });

  it('FE-PIN-API-003: adds, lists, and removes polymorphic items', async () => {
    await addPinboardItem('board-1', { item_type: 'document', item_id: 'doc-1' });
    await listPinboardItems('board-1');
    await removePinboardItem('board-1', 'item-1');
    expect(api.apiPost).toHaveBeenCalledWith('/pinboards/board-1/items', {
      item_type: 'document', item_id: 'doc-1',
    });
    expect(api.apiGet).toHaveBeenCalledWith('/pinboards/board-1/items');
    expect(api.apiDelete).toHaveBeenCalledWith('/pinboards/board-1/items/item-1');
  });

  it('FE-PIN-API-004: focused export carries explicit confirmation', async () => {
    await exportPinboard('board-1', { reason_for_visit: 'Review records', confirm: true });
    expect(api.apiPost).toHaveBeenCalledWith('/pinboards/board-1/export', {
      reason_for_visit: 'Review records', confirm: true,
    });
  });
});
