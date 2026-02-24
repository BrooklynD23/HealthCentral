/**
 * Tests for PageImageOverlay component (OCR-BOX-001).
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PageImageOverlay } from '../components/PageImageOverlay';
import { fetchPageImageBlob } from '@/services/documents';

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
  fetchPageImageBlob: vi.fn(async () => new Blob(['fake'], { type: 'image/png' })),
}));

describe('PageImageOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis.URL as unknown as { createObjectURL?: unknown }).createObjectURL = vi.fn(
      () => 'blob:page-image'
    );
    (globalThis.URL as unknown as { revokeObjectURL?: unknown }).revokeObjectURL = vi.fn();
  });

  it('renders an image with the fetched blob src', async () => {
    render(
      <PageImageOverlay
        documentId="doc-123"
        pageNumber={2}
        bbox={null}
      />
    );

    const img = screen.getByRole('img', { name: /page 2/i });
    expect(img).toBeDefined();
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });
    expect(vi.mocked(fetchPageImageBlob)).toHaveBeenCalledWith('doc-123', 2);
  });

  it('shows page number label', async () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={3} bbox={null} />
    );

    expect(screen.getByText(/page 3/i)).toBeDefined();
    const img = screen.getByRole('img', { name: /page 3/i });
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });
  });

  it('shows fallback when image fails to load', async () => {
    render(
      <PageImageOverlay
        documentId="doc-1"
        pageNumber={1}
        bbox={null}
        fallbackText="Custom fallback text"
      />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });
    fireEvent.error(img);

    expect(screen.getByText('Custom fallback text')).toBeDefined();
  });

  it('shows default fallback text on error', async () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={null} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });
    fireEvent.error(img);

    expect(screen.getByText('Source location not available.')).toBeDefined();
  });

  it('renders bbox overlay after image loads when bbox provided', async () => {
    const bbox = { x0: 100, y0: 200, x1: 300, y1: 250 };

    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={bbox} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });

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

  it('shows "bbox not available" text when no bbox and image loaded', async () => {
    render(
      <PageImageOverlay documentId="doc-1" pageNumber={1} bbox={null} />
    );

    const img = screen.getByRole('img', { name: /page 1/i });
    await waitFor(() => {
      expect(img.getAttribute('src')).toBe('blob:page-image');
    });

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
