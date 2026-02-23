/**
 * Tests for PageImageOverlay component (OCR-BOX-001).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PageImageOverlay } from '../components/PageImageOverlay';

// Mock framer-motion (project pattern)
vi.mock('framer-motion', () => {
  const createMotionComponent = (tag: string) => {
    const Component = ({ children, ...props }: Record<string, unknown> & { children?: React.ReactNode }) => {
      const domProps = Object.fromEntries(
        Object.entries(props).filter(
          ([key]) =>
            !['initial', 'animate', 'exit', 'transition', 'variants', 'whileHover', 'whileTap', 'layout'].includes(key)
        )
      );
      const Tag = tag as keyof JSX.IntrinsicElements;
      return <Tag {...domProps}>{children}</Tag>;
    };
    Component.displayName = `motion.${tag}`;
    return Component;
  };
  return {
    motion: new Proxy({}, { get: (_, prop: string) => createMotionComponent(prop) }),
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  };
});

// Mock auth store
vi.mock('@/stores/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: Record<string, unknown>) => unknown) =>
    selector({ token: 'test-token', profileId: 'test-profile' })
  ),
}));

// Mock documents service
vi.mock('@/services/documents', () => ({
  getPageImageUrl: (docId: string, page: number) =>
    `http://localhost:8000/api/v1/documents/${docId}/pages/${page}/image`,
}));

describe('PageImageOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders an image with the correct src', () => {
    render(
      <PageImageOverlay
        documentId="doc-123"
        pageNumber={2}
        bbox={null}
      />
    );

    const img = screen.getByRole('img', { name: /page 2/i });
    expect(img).toBeDefined();
    expect((img as HTMLImageElement).src).toContain('/documents/doc-123/pages/2/image');
  });

  it('shows page number label', () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={3} bbox={null} />
    );

    expect(screen.getByText(/page 3/i)).toBeDefined();
  });

  it('shows fallback when image fails to load', () => {
    render(
      <PageImageOverlay
        documentId="doc-1"
        pageNumber={1}
        bbox={null}
        fallbackText="Custom fallback text"
      />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    fireEvent.error(img);

    expect(screen.getByText('Custom fallback text')).toBeDefined();
  });

  it('shows default fallback text on error', () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={null} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    fireEvent.error(img);

    expect(screen.getByText('Source location not available.')).toBeDefined();
  });

  it('renders bbox overlay after image loads when bbox provided', () => {
    const bbox = { x0: 100, y0: 200, x1: 300, y1: 250 };

    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={bbox} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });

    // Simulate image load with dimensions
    Object.defineProperty(img, 'naturalWidth', { value: 600 });
    Object.defineProperty(img, 'naturalHeight', { value: 800 });
    Object.defineProperty(img, 'clientWidth', { value: 600 });
    Object.defineProperty(img, 'clientHeight', { value: 800 });

    fireEvent.load(img);

    // Overlay should be present
    const overlay = screen.getByRole('img', {
      name: /highlighted source region/i,
    });
    expect(overlay).toBeDefined();
  });

  it('shows "bbox not available" text when no bbox and image loaded', () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={null} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });

    Object.defineProperty(img, 'naturalWidth', { value: 600 });
    Object.defineProperty(img, 'naturalHeight', { value: 800 });
    Object.defineProperty(img, 'clientWidth', { value: 600 });
    Object.defineProperty(img, 'clientHeight', { value: 800 });

    fireEvent.load(img);

    expect(
      screen.getByText(/bounding box data not available/i)
    ).toBeDefined();
  });
});
