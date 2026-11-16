/**
 * UI-PRIM-CONTROLS-MINORS (HC-UPCM-001 .. 010): three latent defects in the control primitives.
 *
 * 1. IconButton `loading` grew a second glyph (spinner beside the icon): a layout shift.
 * 2. Button `asChild` + `loading` set `disabled` on an <a> or Link, which ignore it, so the control stayed
 *    clickable while it said busy.
 * 3. Select and Checkbox had no direct test.
 *
 * No caller uses either loading path today, so nothing a patient sees changes.
 */
import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Link, Route, Routes } from 'react-router-dom';
import { Save } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { IconButton } from '@/components/ui/IconButton';
import { Checkbox } from '@/components/ui/Checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

// jsdom has no pointer-capture or scrollIntoView, and Radix Select calls them when it opens and picks.
// The same shim ui-care.test.tsx uses; it does not change what these tests assert.
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
  Element.prototype.releasePointerCapture = () => {};
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

describe('UI-PRIM-CONTROLS-MINORS IconButton', () => {
  it('HC-UPCM-001: loading swaps the icon for one spinner, with aria-busy and disabled', () => {
    const { container } = render(
      <IconButton aria-label="Save" loading>
        <Save data-testid="icon" />
      </IconButton>
    );
    const button = screen.getByRole('button', { name: 'Save' });
    expect(container.querySelectorAll('svg')).toHaveLength(1);
    expect(container.querySelector('svg.animate-spin')).not.toBeNull();
    expect(screen.queryByTestId('icon')).toBeNull();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toBeDisabled();
    expect((button.getAttribute('class') ?? '').split(/\s+/)).toEqual(
      expect.arrayContaining(['min-h-target', 'min-w-target'])
    );
  });

  it('HC-UPCM-002: not loading shows the icon and no spinner', () => {
    const { container } = render(
      <IconButton aria-label="Save">
        <Save data-testid="icon" />
      </IconButton>
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
    expect(container.querySelector('svg.animate-spin')).toBeNull();
    expect(screen.getByRole('button', { name: 'Save' })).not.toHaveAttribute('aria-busy');
  });
});

describe('UI-PRIM-CONTROLS-MINORS Button asChild', () => {
  it('HC-UPCM-003: asChild + loading blocks the click and marks the anchor busy and aria-disabled', () => {
    const spy = vi.fn();
    render(
      <Button asChild loading>
        <a href="/x" onClick={spy}>
          Go
        </a>
      </Button>
    );
    const link = screen.getByRole('link', { name: 'Go' });
    // fireEvent returns false when a handler called preventDefault on the event.
    const notCancelled = fireEvent.click(link);
    expect(spy).not.toHaveBeenCalled();
    expect(notCancelled).toBe(false);
    expect(link).toHaveAttribute('aria-disabled', 'true');
    expect(link).toHaveAttribute('aria-busy', 'true');
  });

  it('HC-UPCM-004: asChild + loading around a router Link does not navigate', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={['/start']}>
        <Routes>
          <Route
            path="/start"
            element={
              <Button asChild loading>
                <Link to="/next">Go next</Link>
              </Button>
            }
          />
          <Route path="/next" element={<p>Next page</p>} />
        </Routes>
      </MemoryRouter>
    );
    await user.click(screen.getByRole('link', { name: 'Go next' }));
    expect(screen.queryByText('Next page')).toBeNull();
    expect(screen.getByRole('link', { name: 'Go next' })).toBeInTheDocument();
  });

  it('HC-UPCM-005: asChild not loading lets the click through, with no aria-disabled', async () => {
    const user = userEvent.setup();
    const spy = vi.fn((e: React.MouseEvent) => e.preventDefault());
    render(
      <Button asChild>
        <a href="/x" onClick={spy}>
          Go
        </a>
      </Button>
    );
    const link = screen.getByRole('link', { name: 'Go' });
    await user.click(link);
    expect(spy).toHaveBeenCalledTimes(1);
    expect(link).not.toHaveAttribute('aria-disabled');
    expect(link).not.toHaveAttribute('aria-busy');
  });

  it('HC-UPCM-006: a plain Button loading keeps today\'s output (spinner before the label, disabled)', () => {
    const { container } = render(<Button loading>Save</Button>);
    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).not.toHaveAttribute('aria-disabled');
    expect(button).not.toHaveAttribute('data-loading');
    const first = button.firstElementChild;
    expect(first?.tagName.toLowerCase()).toBe('svg');
    expect(first?.getAttribute('class')).toContain('animate-spin');
    expect(first?.getAttribute('aria-hidden')).toBe('true');
    expect(container.querySelectorAll('svg')).toHaveLength(1);
    expect(button.lastChild?.textContent).toBe('Save');
  });
});

describe('UI-PRIM-CONTROLS-MINORS Checkbox', () => {
  it('HC-UPCM-007: takes its name from its label and calls onCheckedChange(true) on click and on Space', async () => {
    const user = userEvent.setup();
    const onCheckedChange = vi.fn();
    render(
      <div>
        <label htmlFor="agree">I agree</label>
        <Checkbox id="agree" onCheckedChange={onCheckedChange} />
      </div>
    );
    const box = screen.getByRole('checkbox', { name: 'I agree' });
    await user.click(box);
    expect(onCheckedChange).toHaveBeenLastCalledWith(true);
    expect(box).toBeChecked();
    await user.click(box);
    expect(onCheckedChange).toHaveBeenLastCalledWith(false);
    expect(onCheckedChange).toHaveBeenCalledTimes(2);

    box.focus();
    await user.keyboard(' ');
    expect(onCheckedChange).toHaveBeenCalledTimes(3);
    expect(onCheckedChange).toHaveBeenLastCalledWith(true);
  });

  it('HC-UPCM-008: disabled blocks click and Space', async () => {
    const user = userEvent.setup();
    const onCheckedChange = vi.fn();
    render(<Checkbox aria-label="Locked" disabled onCheckedChange={onCheckedChange} />);
    const box = screen.getByRole('checkbox', { name: 'Locked' });
    expect(box).toBeDisabled();
    await user.click(box);
    box.focus();
    await user.keyboard(' ');
    expect(onCheckedChange).not.toHaveBeenCalled();
    expect(box).not.toBeChecked();
  });
});

function Pick({ disabled = false, onValueChange }: { disabled?: boolean; onValueChange: (v: string) => void }) {
  return (
    <div>
      <label htmlFor="cat">Category</label>
      <Select onValueChange={onValueChange} disabled={disabled}>
        <SelectTrigger id="cat">
          <SelectValue placeholder="Pick one" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="a">Alpha</SelectItem>
          <SelectItem value="b">Beta</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}

describe('UI-PRIM-CONTROLS-MINORS Select', () => {
  it('HC-UPCM-009: takes its name from its label, opens with Enter, and picking an option calls onValueChange', async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(<Pick onValueChange={onValueChange} />);
    const trigger = screen.getByRole('combobox', { name: 'Category' });
    trigger.focus();
    await user.keyboard('{Enter}');
    expect(await screen.findByRole('option', { name: 'Beta' })).toBeInTheDocument();
    await user.click(screen.getByRole('option', { name: 'Beta' }));
    expect(onValueChange).toHaveBeenCalledTimes(1);
    expect(onValueChange).toHaveBeenCalledWith('b');
    expect(screen.getByRole('combobox', { name: 'Category' })).toHaveTextContent('Beta');
  });

  it('HC-UPCM-010: disabled blocks opening by click, Enter and Space', async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    render(<Pick disabled onValueChange={onValueChange} />);
    const trigger = screen.getByRole('combobox', { name: 'Category' });
    expect(trigger).toBeDisabled();
    await user.click(trigger);
    expect(screen.queryByRole('option')).toBeNull();
    trigger.focus();
    await user.keyboard('{Enter}');
    await user.keyboard(' ');
    expect(screen.queryByRole('option')).toBeNull();
    expect(onValueChange).not.toHaveBeenCalled();
  });
});
