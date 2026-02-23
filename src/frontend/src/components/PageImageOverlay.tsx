/**
 * PageImageOverlay — renders a PDF page image with bounding-box highlights.
 *
 * OCR-BOX-001: Visual provenance for OCR-extracted observations.
 * Falls back to text-only when no bbox data or image unavailable.
 */

import { useState, useRef, useCallback, type FC } from 'react';
import { AlertTriangle, ImageOff } from 'lucide-react';
import { Card, CardContent } from '@/components/ui';
import { cn } from '@/utils/cn';
import { getPageImageUrl } from '@/services/documents';
import type { BoundingBox } from '@/services/types';

export interface PageImageOverlayProps {
  documentId: string;
  pageNumber: number;
  /** Bounding box in page-relative coordinates [x0, y0, x1, y1] */
  bbox: BoundingBox | null;
  /** Fallback text when image cannot load */
  fallbackText?: string;
}

export const PageImageOverlay: FC<PageImageOverlayProps> = ({
  documentId,
  pageNumber,
  bbox,
  fallbackText = 'Source location not available.',
}) => {
  const [imageError, setImageError] = useState(false);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState<{
    naturalWidth: number;
    naturalHeight: number;
    displayWidth: number;
    displayHeight: number;
  } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const imageUrl = getPageImageUrl(documentId, pageNumber);

  const handleImageLoad = useCallback(
    (e: React.SyntheticEvent<HTMLImageElement>) => {
      const img = e.currentTarget;
      setImageLoaded(true);
      setImageDimensions({
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        displayWidth: img.clientWidth,
        displayHeight: img.clientHeight,
      });
    },
    []
  );

  const handleImageError = useCallback(() => {
    setImageError(true);
  }, []);

  // Compute scaled bbox rectangle for overlay
  const overlayStyle = (() => {
    if (!bbox || !imageDimensions) return null;
    const { naturalWidth, naturalHeight, displayWidth, displayHeight } =
      imageDimensions;
    if (naturalWidth === 0 || naturalHeight === 0) return null;

    const scaleX = displayWidth / naturalWidth;
    const scaleY = displayHeight / naturalHeight;

    return {
      left: bbox.x0 * scaleX,
      top: bbox.y0 * scaleY,
      width: (bbox.x1 - bbox.x0) * scaleX,
      height: (bbox.y1 - bbox.y0) * scaleY,
    };
  })();

  if (imageError) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="text-center text-ink-secondary">
            <ImageOff className="w-8 h-8 mx-auto mb-2 text-ink-tertiary" />
            <p className="text-sm">{fallbackText}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-2">
        <p className="text-xs text-ink-secondary mb-2 px-1">
          Page {pageNumber} — Source Location
        </p>
        <div ref={containerRef} className="relative inline-block w-full">
          <img
            src={imageUrl}
            alt={`Page ${pageNumber} of document`}
            className={cn(
              'w-full h-auto rounded border border-black/[0.06]',
              !imageLoaded && 'opacity-0'
            )}
            onLoad={handleImageLoad}
            onError={handleImageError}
            // Auth header sent via cookie; for token-based auth, use a fetched blob
            crossOrigin="use-credentials"
          />

          {/* Loading placeholder */}
          {!imageLoaded && (
            <div className="w-full h-48 bg-surface-muted rounded animate-pulse" />
          )}

          {/* Bounding box highlight overlay */}
          {imageLoaded && overlayStyle && (
            <div
              className="absolute border-2 border-accent bg-accent/10 rounded-sm pointer-events-none"
              style={{
                left: `${overlayStyle.left}px`,
                top: `${overlayStyle.top}px`,
                width: `${overlayStyle.width}px`,
                height: `${overlayStyle.height}px`,
              }}
              role="img"
              aria-label="Highlighted source region on document page"
            />
          )}

          {/* No bbox available */}
          {imageLoaded && !bbox && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-ink-tertiary px-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Bounding box data not available for this observation.</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
