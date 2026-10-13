/**
 * Gamification service hooks (GAMIFICATION-V2 task 2): profile-keyed queries,
 * streak invalidation after a dose log.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as api from '@/services/api';
import { useAuthStore } from '@/stores/authStore';
import { useBadges, useStreaks } from '@/services/gamification';
import { useLogDose } from '@/services/medications';
import { useSaveTimezone } from '@/services/modelSettings';

vi.mock('@/services/api', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiPatch: vi.fn(),
}));

const streak = (current: number) => ({
  current_streak_days: current,
  longest_streak_days: current,
  timezone: 'UTC',
  as_of_date: '2026-03-04',
  active_days_last_28: current,
  weeks_with_log_last_4: 1,
});

function setup() {
  // staleTime matches App.tsx: a fresh cache must still not leak across profiles.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 5 * 60 * 1000 } },
  });
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return { queryClient, wrapper };
}

const login = (profileId: string) =>
  useAuthStore.setState({ token: `t-${profileId}`, profileId, isAuthenticated: true });

describe('gamification hooks', () => {
  beforeEach(() => {
    vi.mocked(api.apiGet).mockReset();
    vi.mocked(api.apiPost).mockReset();
    login('profile-a');
  });

  it('useStreaks fetches /gamification/streaks', async () => {
    vi.mocked(api.apiGet).mockResolvedValue(streak(3));
    const { wrapper } = setup();
    const { result } = renderHook(() => useStreaks(), { wrapper });
    await waitFor(() => expect(result.current.data?.current_streak_days).toBe(3));
    expect(api.apiGet).toHaveBeenCalledWith('/gamification/streaks');
  });

  it('profile switch without logout never shows the previous profile streak', async () => {
    let resolveB: (v: unknown) => void = () => {};
    vi.mocked(api.apiGet)
      .mockResolvedValueOnce(streak(9))
      .mockReturnValueOnce(new Promise((r) => { resolveB = r; }));
    const { wrapper } = setup();
    const seen: Array<number | undefined> = [];
    const { result } = renderHook(() => {
      const q = useStreaks();
      seen.push(q.data?.current_streak_days);
      return q;
    }, { wrapper });
    await waitFor(() => expect(result.current.data?.current_streak_days).toBe(9));

    seen.length = 0;
    act(() => login('profile-b'));
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));
    expect(result.current.data).toBeUndefined();
    await act(async () => resolveB(streak(1)));
    await waitFor(() => expect(result.current.data?.current_streak_days).toBe(1));
    expect(seen).not.toContain(9);
  });

  it('profile switch without logout refetches badges for the new profile', async () => {
    vi.mocked(api.apiGet)
      .mockResolvedValueOnce({ badges: [{ id: 'a-only' }] })
      .mockResolvedValueOnce({ badges: [] });
    const { wrapper } = setup();
    const { result } = renderHook(() => useBadges(), { wrapper });
    await waitFor(() => expect(result.current.data?.badges).toHaveLength(1));

    act(() => login('profile-b'));
    await waitFor(() => expect(result.current.data?.badges).toHaveLength(0));
    expect(api.apiGet).toHaveBeenCalledTimes(2);
  });

  it('logging a dose invalidates the profile streak', async () => {
    vi.mocked(api.apiPost).mockResolvedValue({ dose: {}, newly_earned_badges: [] });
    vi.mocked(api.apiGet).mockImplementation(async (path: string) =>
      path === '/gamification/streaks' ? streak(3) : { badges: [] });
    const { wrapper } = setup();
    // Mount the real hooks so their real keys must prefix-match the invalidation.
    const { result } = renderHook(
      () => ({ s: useStreaks(), b: useBadges(), log: useLogDose() }), { wrapper });
    await waitFor(() => expect(result.current.s.data && result.current.b.data).toBeTruthy());
    expect(api.apiGet).toHaveBeenCalledTimes(2);
    await act(async () => {
      await result.current.log.mutateAsync({ medicationId: 'm1', data: {} as never });
    });
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(4));
    expect(vi.mocked(api.apiGet).mock.calls.slice(2).map((c) => c[0]).sort())
      .toEqual(['/gamification/badges', '/gamification/streaks']);
  });

  it('saving a time zone invalidates the streak (day boundaries and UTC hint change)', async () => {
    vi.mocked(api.apiPut).mockResolvedValue({ timezone: 'Europe/Berlin' });
    vi.mocked(api.apiGet).mockResolvedValue(streak(3));
    const { wrapper } = setup();
    const { result } = renderHook(() => ({ s: useStreaks(), save: useSaveTimezone() }), { wrapper });
    await waitFor(() => expect(result.current.s.data).toBeTruthy());
    await act(async () => {
      await result.current.save.mutateAsync('Europe/Berlin');
    });
    await waitFor(() => expect(api.apiGet).toHaveBeenCalledTimes(2));
  });
});
