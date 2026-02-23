/**
 * Memory Store API Service
 *
 * ASSIST-MEM-002: React Query hooks for memory CRUD.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut, apiDelete } from './api';
import type { MemoryItem, MemoryItemCreate, MemoryItemUpdate } from './types';

const QUERY_KEY = 'memory-items';

// API functions
async function fetchMemoryItems(category?: string): Promise<MemoryItem[]> {
  const params: Record<string, string> = {};
  if (category) params.category = category;
  return apiGet<MemoryItem[]>('/memory/', params);
}

async function fetchMemoryItem(id: string): Promise<MemoryItem> {
  return apiGet<MemoryItem>(`/memory/${id}`);
}

async function createMemoryItem(data: MemoryItemCreate): Promise<MemoryItem> {
  return apiPost<MemoryItem>('/memory/', data);
}

async function updateMemoryItem({
  id,
  data,
}: {
  id: string;
  data: MemoryItemUpdate;
}): Promise<MemoryItem> {
  return apiPut<MemoryItem>(`/memory/${id}`, data);
}

async function deleteMemoryItem(id: string): Promise<void> {
  return apiDelete(`/memory/${id}`);
}

// React Query hooks
export function useMemoryItems(category?: string) {
  return useQuery({
    queryKey: [QUERY_KEY, category],
    queryFn: () => fetchMemoryItems(category),
  });
}

export function useMemoryItem(id: string | undefined) {
  return useQuery({
    queryKey: [QUERY_KEY, id],
    queryFn: () => fetchMemoryItem(id!),
    enabled: !!id,
  });
}

export function useCreateMemoryItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createMemoryItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useUpdateMemoryItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateMemoryItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

export function useDeleteMemoryItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteMemoryItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}
