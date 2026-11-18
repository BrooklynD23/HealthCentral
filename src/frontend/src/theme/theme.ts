/**
 * Theme resolution (UI-THEME).
 *
 * Dark mode stays off until UI-DARK-FLIP flips DARK_MODE_ENABLED. The inline
 * pre-paint script in index.html mirrors resolveTheme(); keep them in sync.
 */
export const DARK_MODE_ENABLED = false;

export type ThemePref = 'light' | 'dark' | 'system';

/** Single storage key. No UI writes it yet. */
export const THEME_STORAGE_KEY = 'asclexis-theme';

export function resolveTheme(
  pref: ThemePref,
  osDark: boolean,
  enabled: boolean,
): 'light' | 'dark' {
  if (!enabled) return 'light';
  if (pref === 'system') return osDark ? 'dark' : 'light';
  return pref;
}

/** Missing or invalid value, or a throwing storage, gives 'system'. */
export function readThemePref(
  storage?: Pick<Storage, 'getItem'>,
): ThemePref {
  try {
    const s = storage ?? window.localStorage;
    const v = s.getItem(THEME_STORAGE_KEY);
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system';
  } catch {
    return 'system';
  }
}

/** Never throws. */
export function currentTheme(
  storage: Pick<Storage, 'getItem'> | undefined,
  osDark: boolean,
  enabled: boolean = DARK_MODE_ENABLED,
): 'light' | 'dark' {
  return resolveTheme(readThemePref(storage), osDark, enabled);
}
