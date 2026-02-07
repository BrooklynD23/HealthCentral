/**
 * Model Settings API Service
 *
 * React Query hooks for model configuration:
 * - Hardware detection
 * - Tier selection and download
 * - External API configuration
 *
 * Phase 4B: Settings page integration.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from './api';

// Types

export interface HardwareInfo {
  ram_total_gb: number;
  ram_available_gb: number;
  cpu_cores: number;
  cpu_name: string | null;
  disk_free_gb: number;
  gpu_available: boolean;
  gpu_vram_gb: number | null;
  gpu_name: string | null;
  recommended_tier: string;
  max_supported_tier: string;
  detection_timestamp: string;
}

export interface TierStatus {
  tier: string;
  name: string;
  model: string | null;
  description: string;
  available: boolean;
  downloaded: boolean;
  requirements: Record<string, unknown>;
  can_run: boolean;
}

export interface ModelSettings {
  current_tier: string;
  preferred_tier: string | null;
  recommended_tier: string;
  auto_detect_enabled: boolean;
  hardware_info: HardwareInfo;
  tier_availability: Record<string, TierStatus>;
}

export interface DownloadProgress {
  tier: string;
  status: 'pending' | 'downloading' | 'completed' | 'failed';
  progress: number;
  downloaded_bytes: number;
  total_bytes: number;
  path: string | null;
  error: string | null;
}

export interface TiersListResponse {
  tiers: TierStatus[];
  recommended_tier: string;
}

const QUERY_KEY = 'model-settings';

// API functions

async function getModelSettings(): Promise<ModelSettings> {
  return apiGet<ModelSettings>('/model-settings');
}

async function detectHardware(): Promise<HardwareInfo> {
  return apiPost<HardwareInfo>('/model-settings/detect');
}

async function setTier(tier: string): Promise<ModelSettings> {
  return apiPost<ModelSettings, { tier: string }>('/model-settings/tier', { tier });
}

async function getTiers(): Promise<TiersListResponse> {
  return apiGet<TiersListResponse>('/model-settings/tiers');
}

async function getDownloadProgress(): Promise<Record<string, DownloadProgress>> {
  return apiGet<Record<string, DownloadProgress>>('/model-settings/download-progress');
}

async function startDownload(tier: string): Promise<DownloadProgress> {
  return apiPost<DownloadProgress, { tier: string }>('/model-settings/download', { tier });
}

// React Query hooks

/**
 * Query hook for fetching current model settings.
 */
export function useModelSettings() {
  return useQuery({
    queryKey: [QUERY_KEY],
    queryFn: getModelSettings,
    staleTime: 30_000,
  });
}

/**
 * Mutation hook for running hardware detection.
 */
export function useDetectHardware() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: detectHardware,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

/**
 * Mutation hook for setting model tier.
 */
export function useSetTier() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tier: string) => setTier(tier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY] });
    },
  });
}

/**
 * Query hook for listing all tiers.
 */
export function useTiers() {
  return useQuery({
    queryKey: [QUERY_KEY, 'tiers'],
    queryFn: getTiers,
    staleTime: 60_000,
  });
}

/**
 * Query hook for download progress (polls while downloading).
 */
export function useDownloadProgress(enabled: boolean = false) {
  return useQuery({
    queryKey: [QUERY_KEY, 'download-progress'],
    queryFn: getDownloadProgress,
    enabled,
    refetchInterval: enabled ? 2000 : false,
  });
}

/**
 * Mutation hook for starting model download.
 */
export function useStartDownload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (tier: string) => startDownload(tier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEY, 'download-progress'] });
    },
  });
}
