import { useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { motion } from 'framer-motion';
import {
  Upload,
  FileText,
  Calendar,
  CheckCircle,
  AlertCircle,
  MoreVertical,
  Eye,
  Plus,
  Loader2,
  X,
  RefreshCcw,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  useDocuments,
  useImportDocument,
  useDeleteDocument,
  useReprocessDocument,
  useHighlightsSummary,
  ApiError,
  type Document,
  type DocumentImportResponse,
} from '@/services';
import { useAuthStore } from '@/stores/authStore';
import { PageImageOverlay } from '@/components/PageImageOverlay';
import { HighlightChips } from '@/components/documents/HighlightChips';
import { AddToPinboardButton } from '@/components/pinboards/AddToPinboardButton';
// CategoryBadge + EntityDetailView available in @/components/documents/
// Wire into document detail view when it's built (no detail page exists yet)

export function DocumentInbox() {
  const prefersReducedMotion = useReducedMotion();
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [previewDocId, setPreviewDocId] = useState<string | null>(null);
  const [lastImport, setLastImport] = useState<DocumentImportResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Get active profile from auth store
  const profileId = useAuthStore((state) => state.profileId) || '';
  
  // Fetch documents from API
  const { data: documents = [], isLoading, error } = useDocuments({ profile_id: profileId });
  const importDocument = useImportDocument();
  const deleteDocument = useDeleteDocument();
  const reprocessDocument = useReprocessDocument();

  // Highlight chips for recent documents (HC-M16) — organizational tags only
  const { data: highlightSummary = [] } = useHighlightsSummary();
  const highlightsByDoc = new Map(highlightSummary.map((s) => [s.doc_id, s.counts]));

  const closePreview = () => setPreviewDocId(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    for (const file of files) {
      await handleFileUpload(file);
    }
  };
  
  const handleFileUpload = async (file: File) => {
    if (!profileId) return;
    
    try {
      const result = await importDocument.mutateAsync({ file, profileId });
      setLastImport(result);
    } catch (err) {
      console.error('Failed to import document:', err);
    }
  };

  const handleReprocessDocument = (doc: Document) => {
    reprocessDocument.mutate(doc.id);
  };
  
  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      await handleFileUpload(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const getDocTypeBadge = (doc: Document) => {
    const typeMap: Record<string, string> = {
      'lab_pdf': 'Lab Report',
      'lab_image': 'Lab Image',
    };
    return typeMap[doc.doc_type] || doc.doc_type;
  };

  const handleDeleteDocument = (doc: Document) => {
    if (!window.confirm(`Remove "${doc.source || 'this document'}" from your library? This cannot be undone.`)) {
      return;
    }
    deleteDocument.mutate(doc.id);
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: prefersReducedMotion ? 0 : 0.05 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Document Inbox
          </h1>
          <p className="text-ink-secondary mt-1">
            Import and manage your medical documents
          </p>
        </div>
        <Button className="gap-2" onClick={handleBrowseClick}>
          <Plus className="w-4 h-4" />
          Import Document
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          multiple
          className="hidden"
          onChange={handleFileInputChange}
          aria-label="Upload medical documents"
        />
      </div>

      <Card
        className={cn(
          'border-2 border-dashed transition-all duration-200',
          isDragging
            ? 'border-accent bg-accent-subtle/50'
            : 'border-black/[0.08] hover:border-accent/50'
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <CardContent className="py-12">
          <div className="text-center">
            <div
              className={cn(
                'w-14 h-14 mx-auto rounded-2xl flex items-center justify-center mb-4 transition-colors',
                isDragging ? 'bg-accent text-white' : 'bg-surface-muted text-ink-secondary',
                importDocument.isPending && 'animate-pulse'
              )}
            >
              {importDocument.isPending ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : (
                <Upload className="w-6 h-6" />
              )}
            </div>
            <h3 className="font-medium text-ink mb-1">
              {importDocument.isPending 
                ? 'Importing document...' 
                : isDragging 
                  ? 'Drop files here' 
                  : 'Drag and drop files'}
            </h3>
            <p className="text-sm text-ink-secondary mb-4">
              or click to browse • PDF, images supported
            </p>
            <Button variant="secondary" size="sm" onClick={handleBrowseClick}>
              Browse Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-status-critical/20 bg-status-critical/5">
          <CardContent className="py-4 space-y-3">
            <div className="flex items-start gap-3 text-status-critical">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium text-ink">
                  {error instanceof ApiError && error.status === 401
                    ? 'Your session has ended or is invalid.'
                    : error instanceof ApiError && error.status === 403
                      ? 'Access denied — your profile may be locked.'
                      : 'Failed to load documents'}
                </p>
                <p className="text-sm text-ink-secondary">
                  {error instanceof ApiError && error.status === 401
                    ? 'For privacy, invalid sessions are cleared. Sign in again to continue.'
                    : error instanceof ApiError && error.status === 403
                      ? 'Unlock your profile or adjust access in Settings.'
                      : 'Check that the HealthCentral server is running and try again.'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2 pl-8">
              {(error instanceof ApiError && (error.status === 401 || error.status === 403)) && (
                <>
                  <Button variant="secondary" size="sm" className="gap-1.5" asChild>
                    <Link to="/setup">Sign in again</Link>
                  </Button>
                  <Button variant="secondary" size="sm" className="gap-1.5" asChild>
                    <Link to="/settings">Open Settings</Link>
                  </Button>
                </>
              )}
              <Button variant="secondary" size="sm" onClick={() => navigate(0)}>
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {lastImport && (
        <Card className="border-accent/20 bg-accent-subtle/40">
          <CardContent className="py-4 flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <p className="font-medium text-ink">Document imported: {lastImport.document.source || 'Untitled document'}</p>
              <p className="text-sm text-ink-secondary">
                {lastImport.observations_extracted} values extracted · status {lastImport.document.status.replace(/_/g, ' ')}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setPreviewDocId(lastImport.document.id)}>
                Preview
              </Button>
              <Button size="sm" onClick={() => navigate(`/verify?doc=${lastImport.document.id}&mode=all`)}>
                Review values
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Recent Documents</span>
            <Badge variant="default">{documents.length} total</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-ink-secondary">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
              Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="p-8 text-center text-ink-secondary">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No documents yet. Import your first lab report above.</p>
            </div>
          ) : (
            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="divide-y divide-black/[0.04]"
            >
              {documents.map((doc) => (
                <motion.div
                  key={doc.id}
                  variants={itemVariants}
                  className="flex items-center gap-4 p-4 hover:bg-surface-muted/50 transition-colors group"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-surface-muted flex items-center justify-center">
                    <FileText className="w-5 h-5 text-ink-secondary" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-ink truncate">{doc.source || 'Untitled Document'}</h4>
                    <div className="flex items-center gap-3 mt-1 text-sm text-ink-secondary">
                      <span>{getDocTypeBadge(doc)}</span>
                      <span className="text-ink-tertiary">•</span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {new Date(doc.imported_at).toLocaleDateString()}
                      </span>
                    </div>
                    {highlightsByDoc.has(doc.id) && (
                      <HighlightChips
                        counts={highlightsByDoc.get(doc.id)!}
                        max={4}
                        className="mt-1.5"
                      />
                    )}
                  </div>

                  <Badge variant={doc.doc_type === 'lab_pdf' ? 'accent' : 'default'}>
                    {getDocTypeBadge(doc)}
                  </Badge>

                  {doc.status === 'verified' ? (
                    <Badge variant="verified" className="gap-1">
                      <CheckCircle className="w-3 h-3" />
                      Verified
                    </Badge>
                  ) : doc.status === 'pending_ocr' ? (
                    <Badge variant="default" className="gap-1" title="OCR processing is required. In Settings, enable document OCR and install Tesseract (or your admin must set OCR_ENABLED).">
                      <AlertCircle className="w-3 h-3" />
                      OCR Required
                    </Badge>
                  ) : (
                    <Badge variant="caution" className="gap-1">
                      <AlertCircle className="w-3 h-3" />
                      {doc.status === 'pending' ? 'Pending' : 'Needs Review'}
                    </Badge>
                  )}

                  <div className="flex items-center gap-1 sm:opacity-0 sm:group-hover:opacity-100 sm:transition-opacity">
                    <AddToPinboardButton items={[{ item_type: 'document', item_id: doc.id }]} />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="View document"
                      onClick={() => setPreviewDocId(doc.id)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                    <DropdownMenu.Root>
                      <DropdownMenu.Trigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          aria-label="More options"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </Button>
                      </DropdownMenu.Trigger>
                      <DropdownMenu.Portal>
                        <DropdownMenu.Content
                          className="min-w-[12rem] rounded-xl border border-black/[0.08] bg-white p-1 shadow-lg z-[100]"
                          sideOffset={8}
                          align="end"
                        >
                          <DropdownMenu.Item
                            className="rounded-lg px-3 py-2 text-sm outline-none cursor-pointer hover:bg-surface-muted focus:bg-surface-muted"
                            onSelect={() => navigate(`/verify?doc=${doc.id}&mode=all`)}
                          >
                            Review extracted values
                          </DropdownMenu.Item>
                          {(doc.status === 'pending_ocr' || doc.status === 'extraction_failed' || doc.status === 'parsed') && (
                            <DropdownMenu.Item
                              className="rounded-lg px-3 py-2 text-sm outline-none cursor-pointer hover:bg-surface-muted focus:bg-surface-muted"
                              onSelect={() => handleReprocessDocument(doc)}
                            >
                              <span className="inline-flex items-center gap-2">
                                <RefreshCcw className="w-3.5 h-3.5" />
                                Continue OCR / Retry extraction
                              </span>
                            </DropdownMenu.Item>
                          )}
                          <DropdownMenu.Item
                            className="rounded-lg px-3 py-2 text-sm outline-none cursor-pointer text-status-critical hover:bg-status-critical/10 focus:bg-status-critical/10"
                            onSelect={() => handleDeleteDocument(doc)}
                          >
                            Delete…
                          </DropdownMenu.Item>
                        </DropdownMenu.Content>
                      </DropdownMenu.Portal>
                    </DropdownMenu.Root>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </CardContent>
      </Card>

      {previewDocId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="document-preview-title"
          onClick={closePreview}
        >
          <Card
            className="w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-elevated"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader className="flex flex-row items-center justify-between flex-shrink-0 border-b border-black/[0.04]">
              <CardTitle id="document-preview-title" className="text-lg">
                Document preview
              </CardTitle>
              <Button type="button" variant="ghost" size="icon" onClick={closePreview} aria-label="Close">
                <X className="w-5 h-5" />
              </Button>
            </CardHeader>
            <CardContent className="overflow-y-auto p-4">
              <PageImageOverlay documentId={previewDocId} pageNumber={1} bbox={null} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
