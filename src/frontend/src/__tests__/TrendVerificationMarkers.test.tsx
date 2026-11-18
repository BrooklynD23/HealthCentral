import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UnverifiedTrendNote } from '@/components/TrendVerificationMarkers';

describe('HC-VER-FE-002: trend verification markers (D4)', () => {
  it('states the unverified count in text, and renders nothing when there are none', () => {
    const { rerender } = render(<UnverifiedTrendNote unverified={1} total={3} />);
    expect(screen.getByTestId('trend-unverified-note')).toHaveTextContent(
      '1 of 3 points on this chart are unverified'
    );
    rerender(<UnverifiedTrendNote unverified={0} total={3} />);
    expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
  });
});
