// UI-SHELL (HC-UISH-001): the navigation config holds the plan §3.1 groups and
// the transition entries, prefix matching marks the active destination, and
// every destination name lives in navConfig.ts only (plan §7.5, "Files").

import { describe, it, expect } from 'vitest';
import { navGroups, navTabs, isNavActive } from '@/components/layout/navConfig';
import appLayoutSource from '@/components/layout/AppLayout.tsx?raw';
import sidebarSource from '@/components/layout/Sidebar.tsx?raw';
import mobileTabBarSource from '@/components/layout/MobileTabBar.tsx?raw';
import moreSheetSource from '@/components/layout/MoreSheet.tsx?raw';
import topBarSource from '@/components/layout/TopBar.tsx?raw';
import profileMenuSource from '@/components/layout/ProfileMenu.tsx?raw';
import safetyRailSource from '@/components/layout/SafetyRail.tsx?raw';
import safetyModeToggleSource from '@/components/layout/SafetyModeToggle.tsx?raw';

describe('UI-SHELL navConfig (HC-UISH-001)', () => {
  it('HC-UISH-001: destinations are grouped as plan §3.1 with the transition entries and no Overview', () => {
    const groups = navGroups.map((group) => ({
      label: group.label,
      items: group.items.map((item) => [item.label, item.to]),
    }));

    expect(groups).toEqual([
      {
        label: 'Records',
        items: [
          ['Documents', '/inbox'],
          ['Review values', '/verify'],
          ['Timeline', '/timeline'],
          ['Pinboards', '/pinboards'],
        ],
      },
      {
        label: 'Understand',
        // Transition (plan §3.1): Results points at /trends until UI-PG-RESULTS, and Interpret stays listed.
        items: [
          ['Results', '/trends'],
          ['Interpret', '/interpret'],
          ['Ask', '/explain'],
        ],
      },
      {
        label: 'Care',
        // Transition: Reminders stays listed under Care until UI-MICRO and lands on /notifications.
        items: [
          ['Medications', '/medications'],
          ['Reminders', '/notifications'],
          ['Follow-ups', '/care-tasks'],
        ],
      },
      {
        label: 'Share',
        items: [['Doctor summary', '/export']],
      },
    ]);
  });

  it('HC-UISH-001: the phone tab bar has Documents, Review values, Results, Ask and More, in that order', () => {
    expect(navTabs.map((tab) => tab.label)).toEqual([
      'Documents',
      'Review values',
      'Results',
      'Ask',
      'More',
    ]);
    expect(navTabs.find((tab) => tab.label === 'More')?.to).toBeUndefined();
  });

  it('HC-UISH-001: prefix matching marks Medications active on /medications/abc and not on /medicationsx', () => {
    expect(isNavActive('/medications/abc', '/medications')).toBe(true);
    expect(isNavActive('/medications', '/medications')).toBe(true);
    expect(isNavActive('/medicationsx', '/medications')).toBe(false);
    expect(isNavActive('/inbox', '/medications')).toBe(false);
  });

  it('HC-UISH-001: every destination name is written only in navConfig.ts', () => {
    const names = navGroups.flatMap((group) => group.items.map((item) => item.label));
    const shellFiles: Record<string, string> = {
      'AppLayout.tsx': appLayoutSource,
      'Sidebar.tsx': sidebarSource,
      'MobileTabBar.tsx': mobileTabBarSource,
      'MoreSheet.tsx': moreSheetSource,
      'TopBar.tsx': topBarSource,
      'ProfileMenu.tsx': profileMenuSource,
      'SafetyRail.tsx': safetyRailSource,
      'SafetyModeToggle.tsx': safetyModeToggleSource,
    };
    for (const [file, source] of Object.entries(shellFiles)) {
      for (const name of names) {
        expect(source, `${file} must not hard-code "${name}"`).not.toContain(`'${name}'`);
        expect(source, `${file} must not hard-code "${name}"`).not.toContain(`>${name}<`);
      }
    }
  });
});
