/**
 * UI-PRIM-CONTROLS (HC-UIPC-001 .. 007): the control primitives.
 *
 * Plan: docs/plans/2026-10-23-frontend-revamp-plan.md §7.4 (UI-PRIM-CONTROLS),
 * design rules §2.4 (E1: a border or a shadow, never both) and §2.6 (M1 press,
 * M9 indicator, the global transition ban).
 *
 * jsdom has no layout, so the 44 px target is checked as the min-size utilities
 * on the element plus their definitions in globals.css. What this cannot see is
 * a utility that is defined but overridden by a parent's layout; the e2e row
 * HC-UIPC-007 measures computed style in a real browser.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Checkbox } from '@/components/ui/Checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

const UI_DIR = resolve(__dirname, '..', 'components', 'ui');
const GLOBALS_CSS = resolve(__dirname, '..', 'styles', 'globals.css');

const VARIANTS = ['primary', 'secondary', 'ghost', 'danger', 'link'] as const;
const SIZES = ['sm', 'md', 'lg', 'icon'] as const;

/** True when a class token is `transition-all`, bare or behind variants (hover:transition-all). */
function hasTransitionAll(className: string): boolean {
  return className
    .split(/\s+/)
    .some((token) => token.slice(token.lastIndexOf(':') + 1) === 'transition-all');
}

/** Source text of one primitive file under src/components/ui. */
function primitiveSource(name: string): string {
  return readFileSync(join(UI_DIR, name), 'utf8');
}

describe('UI-PRIM-CONTROLS Button', () => {
  it('HC-UIPC-001: loading sets aria-busy="true" and disables the button', () => {
    render(<Button loading>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toBeDisabled();
  });

  it('HC-UIPC-001: a button that is not loading has no aria-busy and is enabled', () => {
    render(<Button>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).not.toHaveAttribute('aria-busy');
    expect(button).toBeEnabled();
  });

  it('HC-UIPC-001: loading shows a spinner and keeps the label', () => {
    const { container } = render(<Button loading>Save</Button>);
    expect(container.querySelector('svg.animate-spin')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Save' })).toHaveTextContent('Save');
  });

  it('HC-UIPC-001: the link variant renders as a button element', () => {
    render(<Button variant="link">Read more</Button>);
    expect(screen.getByRole('button', { name: 'Read more' })).toBeInTheDocument();
  });
});

describe('UI-PRIM-CONTROLS IconButton', () => {
  it('HC-UIPC-002: a labelled IconButton renders with its aria-label', () => {
    render(
      <IconButton aria-label="Add dose">
        <Plus />
      </IconButton>
    );
    expect(screen.getByRole('button', { name: 'Add dose' })).toBeInTheDocument();
  });

  it('HC-UIPC-002: an IconButton without aria-label is a type error', () => {
    // @ts-expect-error aria-label is required on IconButton; tsc fails if this stops being an error
    const unlabelled = <IconButton><Plus /></IconButton>;
    expect(unlabelled).toBeDefined();
  });

  it('HC-UIPC-002: an IconButton carries the 44 px minimum target classes', () => {
    render(
      <IconButton aria-label="Add dose">
        <Plus />
      </IconButton>
    );
    const classes = screen.getByRole('button', { name: 'Add dose' }).className.split(/\s+/);
    expect(classes).toContain('min-h-target');
    expect(classes).toContain('min-w-target');
  });

  it('HC-UIPC-002: the min-h-target and min-w-target utilities are defined as 44 px', () => {
    const css = readFileSync(GLOBALS_CSS, 'utf8');
    expect(css).toMatch(/@utility min-h-target\s*\{\s*min-height:\s*44px;\s*\}/);
    expect(css).toMatch(/@utility min-w-target\s*\{\s*min-width:\s*44px;\s*\}/);
  });
});

describe('HC-UIPC-005 field error state', () => {
  it('Input: aria-invalid goes "true" then absent when the error prop clears, and the label stays associated', () => {
    const { rerender } = render(<Input label="Profile name" error="Name is required" />);
    expect(screen.getByLabelText('Profile name')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('Profile name')).toHaveAccessibleDescription('Name is required');

    rerender(<Input label="Profile name" />);
    const input = screen.getByLabelText('Profile name');
    expect(input).not.toHaveAttribute('aria-invalid');
    expect(input).not.toHaveAccessibleDescription('Name is required');
    expect(screen.queryByText('Name is required')).toBeNull();
  });

  it('Textarea: the same field contract as Input', () => {
    const { rerender } = render(<Textarea label="Notes" error="Too long" />);
    expect(screen.getByLabelText('Notes')).toHaveAttribute('aria-invalid', 'true');

    rerender(<Textarea label="Notes" />);
    expect(screen.getByLabelText('Notes')).not.toHaveAttribute('aria-invalid');
    expect(screen.queryByText('Too long')).toBeNull();
  });
});

describe('HC-UIPC-006 transition-all is banned on the primitives', () => {
  it('HC-UIPC-006: every Button variant and size, IconButton, Input, Textarea, Select trigger and Checkbox render without transition-all', () => {
    const { container } = render(
      <div>
        {VARIANTS.flatMap((variant) =>
          SIZES.map((size) => (
            <Button key={`${variant}-${size}`} variant={variant} size={size}>
              x
            </Button>
          ))
        )}
        <IconButton aria-label="Add dose">
          <Plus />
        </IconButton>
        <Input label="Dose" />
        <Textarea label="Notes" />
        <Select>
          <SelectTrigger aria-label="Category">
            <SelectValue placeholder="Pick one" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="a">A</SelectItem>
          </SelectContent>
        </Select>
        <Checkbox aria-label="Saved the code" />
      </div>
    );
    // Every element with a class attribute, wrappers and icons included.
    const classed = Array.from(container.querySelectorAll('[class]'));
    expect(classed.length).toBeGreaterThan(VARIANTS.length * SIZES.length);
    const offending = classed
      .filter((element) => hasTransitionAll(element.getAttribute('class') ?? ''))
      .map((element) => element.getAttribute('class'));
    expect(offending).toEqual([]);
  });

  it('HC-UIPC-006: the primitive source files do not name transition-all', () => {
    for (const file of ['Button.tsx', 'IconButton.tsx', 'Input.tsx', 'Textarea.tsx', 'Select.tsx', 'Checkbox.tsx']) {
      expect(primitiveSource(file), file).not.toMatch(/transition-all/);
    }
  });
});
