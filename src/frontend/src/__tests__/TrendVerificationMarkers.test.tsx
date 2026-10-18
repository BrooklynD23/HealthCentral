import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TrendPointDot, UnverifiedTrendNote } from '@/components/TrendVerificationMarkers';

describe('HC-VER-FE-002: trend verification markers (D4)', () => {
  it('draws an unverified point hollow, with a readable "Unverified" title', () => {
    const { container } = render(
      <svg><TrendPointDot cx={10} cy={20} verified={false} /></svg>
    );
    const marker = container.querySelector('[data-verified="false"]');
    expect(marker).not.toBeNull();
    expect(marker?.querySelector('title')?.textContent).toBe('Unverified');
    expect(marker?.querySelector('circle')?.getAttribute('fill')).toBe('#FFFFFF');
  });

  it('draws a verified point filled, with no unverified title', () => {
    const { container } = render(
      <svg><TrendPointDot cx={10} cy={20} verified /></svg>
    );
    expect(container.querySelector('[data-verified="true"]')).not.toBeNull();
    expect(container.querySelector('[data-verified="false"]')).toBeNull();
    expect(container.querySelector('title')).toBeNull();
  });

  it('states the unverified count in text, and renders nothing when there are none', () => {
    const { rerender } = render(<UnverifiedTrendNote unverified={1} total={3} />);
    expect(screen.getByTestId('trend-unverified-note')).toHaveTextContent(
      '1 of 3 points on this chart are unverified'
    );
    rerender(<UnverifiedTrendNote unverified={0} total={3} />);
    expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
  });
});
