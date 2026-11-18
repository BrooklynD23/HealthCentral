import { createElement, Fragment, useEffect, useSyncExternalStore, type ReactNode } from 'react';

/**
 * The command palette's open state and keys (plan §3.3, UI-PALETTE). This file stays in the main bundle so the
 * palette's own chunk (CommandPalette.tsx) loads on the first open, not at app start. It uses no router and no
 * QueryClient, so TopBar can import it on its own.
 */

/** The header button (desktop) or search link (phone) the palette returns focus to. TopBar sets the attribute on both. */
export const PALETTE_TRIGGER_SELECTOR = '[data-palette-trigger]';

let isOpen = false;
let hasOpened = false;
/** Counts opens, so the palette body can start fresh on each one (even a reopen inside the close hold). */
let openCount = 0;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function openPalette() {
  if (isOpen) return;
  isOpen = true;
  hasOpened = true;
  openCount += 1;
  emit();
}

export function closePalette() {
  if (!isOpen) return;
  isOpen = false;
  emit();
}

/** The open state and keys belong to the shell: when the shell unmounts, the next one starts closed and unfetched. */
function resetPalette() {
  if (!isOpen && !hasOpened) return;
  isOpen = false;
  hasOpened = false;
  emit();
}

export function usePaletteOpen(): boolean {
  return useSyncExternalStore(subscribe, () => isOpen, () => false);
}

/** Changes on every open. */
export function usePaletteSession(): number {
  return useSyncExternalStore(subscribe, () => openCount, () => 0);
}

/** Renders its children only after the first open, so a lazy palette inside it is not fetched before then. */
export function PaletteMount({ children }: { children: ReactNode }) {
  const opened = useSyncExternalStore(subscribe, () => hasOpened, () => false);
  return opened ? createElement(Fragment, null, children) : null;
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  if (target.matches('input, textarea, select')) return true;
  // jsdom does not implement isContentEditable, so the attribute is read as well.
  const editable = target.getAttribute('contenteditable');
  return target.isContentEditable || (editable !== null && editable !== 'false');
}

/** Another modal (a dose sheet, a confirmation) owns the keyboard while it is open. */
function otherModalOpen(): boolean {
  return document.querySelector('[role="dialog"][aria-modal="true"], [role="alertdialog"]') !== null;
}

/** Ctrl/Cmd K toggles the palette. `/` opens it unless focus is in a text field. Mount once, in the top bar. */
export function usePaletteShortcuts() {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing) return;
      const key = event.key.toLowerCase();
      if (key === 'k' && (event.ctrlKey || event.metaKey) && !event.altKey) {
        if (!isOpen && otherModalOpen()) return;
        event.preventDefault();
        if (isOpen) closePalette();
        else openPalette();
      } else if (key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey) {
        if (isOpen || isTypingTarget(event.target) || otherModalOpen()) return;
        event.preventDefault();
        openPalette();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      resetPalette();
    };
  }, []);
}
