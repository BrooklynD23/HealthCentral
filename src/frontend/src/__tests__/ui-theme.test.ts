import { describe, it, expect } from 'vitest';
import { DARK_MODE_ENABLED, resolveTheme, currentTheme } from '../theme/theme';

describe('UI-THEME', () => {
  it('HC-UITH-001: dark mode is off, so every pref resolves to light', () => {
    expect(DARK_MODE_ENABLED).toBe(false);
    expect(resolveTheme('system', true, false)).toBe('light');
    expect(resolveTheme('dark', true, false)).toBe('light');
  });

  it('HC-UITH-002: when enabled, system follows the OS and explicit pref wins', () => {
    expect(resolveTheme('system', true, true)).toBe('dark');
    expect(resolveTheme('system', false, true)).toBe('light');
    expect(resolveTheme('light', true, true)).toBe('light');
    expect(resolveTheme('dark', false, true)).toBe('dark');
  });

  it('HC-UITH-003: a throwing storage falls back to system and never throws', () => {
    const throwing = {
      getItem: () => {
        throw new Error('blocked');
      },
    } as unknown as Storage;
    // enabled=true + osDark=true: 'dark' proves the fallback pref is 'system'
    expect(currentTheme(throwing, true, true)).toBe('dark');
    expect(currentTheme(throwing, false, true)).toBe('light');
  });
});
