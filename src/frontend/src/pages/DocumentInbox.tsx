import { useState, useRef } from 'react';
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
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { useDocuments, useImportDocument, type Document } from '@/services';
import { useAuthStore } from '@/stores/authStore';

export function DocumentInbox() {
  const prefersReducedMotion = useReducedMotion();
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Get active profile from auth store
  const profileId = useAuthStore((state) => state.profileId) || '';
  
  // Fetch documents from API
  const { data: documents = [], isLoading, error } = useDocuments({ profile_id: profileId });
  const importDocument = useImportDocument();

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
      await importDocument.mutateAsync({ file, profileId });
    } catch (err) {
      console.error('Failed to import document:', err);
    }
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
      <div className="flex flex-wrap items-center justify-between gap-3">
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
        role="region"
        aria-label="Document upload area"
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
          <CardContent className="py-4">
            <div className="flex items-center gap-3 text-status-critical">
              <AlertCircle className="w-5 h-5" />
              <span>Failed to load documents. Please try again.</span>
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
              role="list"
              aria-label="Document list"
              className="divide-y divide-black/[0.04]"
            >
              {documents.map((doc) => (
                <motion.div
                  key={doc.id}
                  variants={itemVariants}
                  role="listitem"
                  className="flex flex-col gap-3 p-4 transition-colors hover:bg-surface-muted/50 group md:flex-row md:items-center md:gap-4"
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
                  </div>

                  <Badge variant={doc.doc_type === 'lab_pdf' ? 'accent' : 'default'}>
                    {getDocTypeBadge(doc)}
                  </Badge>

                  {doc.status === 'verified' ? (
                    <Badge variant="verified" className="gap-1" aria-label="Status: Verified">
                      <CheckCircle className="w-3 h-3" />
                      Verified
                    </Badge>
                  ) : doc.status === 'pending_ocr' ? (
                    <Badge variant="default" className="gap-1" aria-label="Status: OCR Required" title="OCR processing is required. Enable OCR in Settings or install Tesseract to extract data from this document.">
                      <AlertCircle className="w-3 h-3" />
                      OCR Required
                    </Badge>
                  ) : (
                    <Badge variant="caution" className="gap-1" aria-label={`Status: ${doc.status === 'pending' ? 'Pending' : 'Needs Review'}`}>
                      <AlertCircle className="w-3 h-3" />
                      {doc.status === 'pending' ? 'Pending' : 'Needs Review'}
                    </Badge>
                  )}

                  <div className="flex items-center gap-1 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                    <Button variant="ghost" size="icon" aria-label="View document">
                      <Eye className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="More options">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
