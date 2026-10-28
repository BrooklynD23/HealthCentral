import {
  Bell,
  Brain,
  CheckCircle,
  ClipboardList,
  FileOutput,
  History,
  Inbox,
  MessageCircle,
  MoreHorizontal,
  Pill,
  Pin,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react';

/**
 * Every destination name in the shell lives in this file (plan §3.1, UI-SHELL).
 * The owner may rename them (open question UI-NAV-NAMES); change them here only.
 *
 * Transition entries (plan §3.1): "Results" points at /trends until UI-PG-RESULTS,
 * "Interpret" stays under Understand, and "Reminders" stays under Care until UI-MICRO.
 */

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export interface NavTab {
  label: string;
  /** Absent for More, which opens the sheet instead of a route. */
  to?: string;
  icon: LucideIcon;
}

export const navGroups: NavGroup[] = [
  {
    label: 'Records',
    items: [
      { label: 'Documents', to: '/inbox', icon: Inbox },
      { label: 'Review values', to: '/verify', icon: CheckCircle },
      { label: 'Timeline', to: '/timeline', icon: History },
      { label: 'Pinboards', to: '/pinboards', icon: Pin },
    ],
  },
  {
    label: 'Understand',
    items: [
      { label: 'Results', to: '/trends', icon: TrendingUp },
      { label: 'Interpret', to: '/interpret', icon: Brain },
      { label: 'Ask', to: '/explain', icon: MessageCircle },
    ],
  },
  {
    label: 'Care',
    items: [
      { label: 'Medications', to: '/medications', icon: Pill },
      { label: 'Reminders', to: '/notifications', icon: Bell },
      { label: 'Follow-ups', to: '/care-tasks', icon: ClipboardList },
    ],
  },
  {
    label: 'Share',
    items: [{ label: 'Doctor summary', to: '/export', icon: FileOutput }],
  },
];

/** The phone tab bar (plan §3.2): five slots, More opens the sheet of every group. */
export const navTabs: NavTab[] = [
  { label: 'Documents', to: '/inbox', icon: Inbox },
  { label: 'Review values', to: '/verify', icon: CheckCircle },
  { label: 'Results', to: '/trends', icon: TrendingUp },
  { label: 'Ask', to: '/explain', icon: MessageCircle },
  { label: 'More', icon: MoreHorizontal },
];

/** Prefix matching on whole path segments: /medications/abc keeps Medications active. */
export function isNavActive(pathname: string, to: string): boolean {
  return pathname === to || pathname.startsWith(`${to}/`);
}
