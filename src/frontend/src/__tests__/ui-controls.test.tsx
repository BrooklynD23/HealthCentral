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
import userEvent from '@testing-library/user-event';
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Checkbox } from '@/components/ui/Checkbox';
import { Switch } from '@/components/ui/Switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
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

  it('HC-UIPC-001: the link variant is accent text with an underline and no filled background', () => {
    render(<Button variant="link">Read more</Button>);
    const classes = screen.getByRole('button', { name: 'Read more' }).className.split(/\s+/);
    expect(classes).toContain('text-accent');
    expect(classes).toContain('underline');
    expect(classes).not.toContain('bg-accent');
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

describe('HC-UIPC-003 Switch', () => {
  it('has role="switch" and Space toggles aria-checked', async () => {
    const user = userEvent.setup();
    render(<Switch aria-label="Reminders" />);
    const toggle = screen.getByRole('switch', { name: 'Reminders' });
    expect(toggle).toHaveAttribute('aria-checked', 'false');

    toggle.focus();
    await user.keyboard(' ');
    expect(toggle).toHaveAttribute('aria-checked', 'true');

    await user.keyboard(' ');
    expect(toggle).toHaveAttribute('aria-checked', 'false');
  });

  it('disabled blocks the toggle', async () => {
    const user = userEvent.setup();
    render(<Switch aria-label="Reminders" disabled />);
    const toggle = screen.getByRole('switch', { name: 'Reminders' });

    await user.click(toggle);
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(toggle).toBeDisabled();
  });
});

describe('HC-UIPC-004 Tabs', () => {
  function renderTabs() {
    return render(
      <Tabs defaultValue="one">
        <TabsList aria-label="Sections">
          <TabsTrigger value="one">One</TabsTrigger>
          <TabsTrigger value="two">Two</TabsTrigger>
          <TabsTrigger value="three">Three</TabsTrigger>
        </TabsList>
        <TabsContent value="one">Panel one</TabsContent>
        <TabsContent value="two">Panel two</TabsContent>
        <TabsContent value="three">Panel three</TabsContent>
      </Tabs>
    );
  }

  it('ArrowRight and ArrowLeft move focus between tabs (roving)', async () => {
    const user = userEvent.setup();
    renderTabs();
    const one = screen.getByRole('tab', { name: 'One' });
    const two = screen.getByRole('tab', { name: 'Two' });

    one.focus();
    await user.keyboard('{ArrowRight}');
    expect(two).toHaveFocus();

    await user.keyboard('{ArrowLeft}');
    expect(one).toHaveFocus();
  });

  it('the tabpanel is aria-labelledby the id of the tab that controls it', async () => {
    const user = userEvent.setup();
    renderTabs();
    const one = screen.getByRole('tab', { name: 'One' });
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', one.id);

    one.focus();
    await user.keyboard('{ArrowRight}');
    const two = screen.getByRole('tab', { name: 'Two' });
    expect(two.id).not.toBe('');
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', two.id);
  });
});

describe('UI-PRIM-CONTROLS Card', () => {
  const CARD_VARIANTS = ['plain', 'interactive', 'inset'] as const;

  /** Class tokens of a Card rendered with the given variant. */
  function cardTokens(variant?: (typeof CARD_VARIANTS)[number]): string[] {
    const { container, unmount } = render(<Card variant={variant} data-testid="card" />);
    const tokens = (container.firstElementChild?.getAttribute('class') ?? '').split(/\s+/);
    unmount();
    return tokens;
  }

  it('E1: each variant has a border or a shadow, never both', () => {
    for (const variant of CARD_VARIANTS) {
      const tokens = cardTokens(variant);
      const hasBorder = tokens.includes('border');
      const hasShadow = tokens.some((token) => /(^|:)shadow-/.test(token));
      expect(hasBorder && hasShadow, variant).toBe(false);
    }
  });

  it('E1: plain is a border with no shadow, and interactive is a shadow with no border', () => {
    const plain = cardTokens('plain');
    expect(plain).toContain('border');
    expect(plain.some((token) => /(^|:)shadow-/.test(token))).toBe(false);

    const interactive = cardTokens('interactive');
    expect(interactive).not.toContain('border');
    expect(interactive).toContain('shadow-card');
  });

  it('only the interactive variant has a hover lift or hover shadow', () => {
    for (const variant of ['plain', 'inset'] as const) {
      const hoverTokens = cardTokens(variant).filter((token) => token.startsWith('hover:'));
      expect(hoverTokens, variant).toEqual([]);
    }
    expect(cardTokens('interactive')).toContain('hover:-translate-y-0.5');
  });

  it('keeps bg-surface-elevated on the default card (the UI-TOKENS contract)', () => {
    expect(cardTokens()).toContain('bg-surface-elevated');
  });

  it('renders every subcomponent export inside a card', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
        </CardHeader>
        <CardContent>Body</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>
    );
    expect(screen.getByRole('heading', { name: 'Title' })).toBeInTheDocument();
    expect(screen.getByText('Description')).toBeInTheDocument();
    expect(screen.getByText('Body')).toBeInTheDocument();
    expect(screen.getByText('Footer')).toBeInTheDocument();
  });
});

describe('HC-UIPC-006 transition-all is banned on the primitives', () => {
  it('HC-UIPC-006: every Button variant and size, IconButton, Input, Textarea, Select trigger, Checkbox, Switch, Tabs and Card render without transition-all', () => {
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
        <Switch aria-label="Reminders" />
        <Card />
        <Card variant="interactive" />
        <Card variant="inset" />
        <Tabs defaultValue="one">
          <TabsList aria-label="Sections">
            <TabsTrigger value="one">One</TabsTrigger>
          </TabsList>
          <TabsContent value="one">Panel one</TabsContent>
        </Tabs>
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

  it('HC-UIPC-006: no source file in src/components/ui names transition-all, including primitives added later', () => {
    const files = readdirSync(UI_DIR).filter((name) => name.endsWith('.tsx'));
    // The named primitives must be among them, so an empty listing cannot pass.
    expect(files).toEqual(
      expect.arrayContaining(['Button.tsx', 'IconButton.tsx', 'Input.tsx', 'Textarea.tsx', 'Select.tsx', 'Checkbox.tsx', 'Switch.tsx', 'Tabs.tsx', 'Card.tsx'])
    );
    for (const file of files) {
      expect(primitiveSource(file), file).not.toMatch(/transition-all/);
    }
  });
});

// ---------------------------------------------------------------------------
// HC-UIPC-007 (vitest half). Per the L0 ruling on PR #365, the 16 ms focus-ring
// e2e and the stillness probe move to UI-SHELL. This half checks the class lists
// that decide the timing: jsdom does not run transitions or compute styles.
// ---------------------------------------------------------------------------

describe('HC-UIPC-007 focus ring and press timing (vitest half)', () => {
  /** Class tokens of the first Button rendered with the given props. */
  function buttonClasses(): string[] {
    const { container, unmount } = render(<Button>Save</Button>);
    const classes = (container.querySelector('button')?.getAttribute('class') ?? '').split(/\s+/);
    unmount();
    return classes;
  }

  /** The properties named by the Button's transition-[...] utility, or undefined. */
  function transitionProperties(classes: string[]): string[] | undefined {
    const token = classes.find((name) => name.startsWith('transition-['));
    return token?.slice('transition-['.length, -1).split(',');
  }

  it('HC-UIPC-007: the focus ring (a box-shadow) is not transitioned, so it shows on the first frame', () => {
    const properties = transitionProperties(buttonClasses());
    expect(properties).toBeDefined();
    expect(properties).not.toContain('box-shadow');
    expect(properties).not.toContain('all');
  });

  it('HC-UIPC-007: the Button declares its focus ring on :focus-visible', () => {
    expect(buttonClasses()).toContain('focus-visible:ring-2');
  });

  it('HC-UIPC-007: no primitive draws its focus ring in a translucent colour (ring-accent/20 and the like)', () => {
    // A 20% ring measures 1.35:1 on white, under WCAG 1.4.11's 3:1. The global
    // *:focus-visible ring (globals.css) is solid accent, so a primitive that
    // overrides it with an alpha ring removes the only visible focus.
    const files = readdirSync(UI_DIR).filter((name) => name.endsWith('.tsx'));
    expect(files).toEqual(expect.arrayContaining(['Switch.tsx', 'Tabs.tsx', 'Input.tsx']));
    const translucentRings = files.flatMap((file) =>
      (primitiveSource(file).match(/focus-visible:ring-[\w-]+\/\d+/g) ?? []).map((ring) => `${file}: ${ring}`)
    );
    expect(translucentRings).toEqual([]);
  });

  it('HC-UIPC-007: press (M1) is colour only under reduced motion', () => {
    const classes = buttonClasses();
    expect(classes).toContain('active:scale-[.97]');
    expect(classes).toContain('motion-reduce:active:scale-100');
  });
});
