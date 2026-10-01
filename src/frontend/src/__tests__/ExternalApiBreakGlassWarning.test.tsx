/**
 * HC-EXT-003 — D12 (owner, 2026-09-27): break-glass is allowed only with a UI
 * warning. The backend reports `redaction_break_glass` on
 * GET /settings/model/external-api (HC-EXT-004).
 *
 * Positive assertions come first; absence is asserted synchronously on a
 * completed render, never via waitFor(... not ...) (recurring-failures #1).
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ExternalApiBreakGlassWarning } from '../components/settings/ExternalApiBreakGlassWarning';

describe('ExternalApiBreakGlassWarning', () => {
  it('HC-EXT-003 shows an alert that says data may leave unredacted and is audited', () => {
    render(<ExternalApiBreakGlassWarning active />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/privacy protection override is on/i);
    expect(alert).toHaveTextContent(/reduced or no redaction/i);
    expect(alert).toHaveTextContent(/audit log/i);
  });

  it('HC-EXT-003b renders nothing when break-glass is off', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('HC-EXT-003c renders nothing when an older backend sends no flag', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
