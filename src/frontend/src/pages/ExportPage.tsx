/**
 * ExportPage - Export data and generate summaries
 *
 * Sprint 4: Wired to real API for CSV/JSON export and summary generation.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Download,
  Copy,
  Check,
  Eye,
  ChevronRight,
  Calendar,
  Printer,
  MessageSquare,
  FileJson,
  FileSpreadsheet,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import {
  useExportCSV,
  useExportJSON,
  useGenerateSummary,
  useDownloadSummary,
  useGenerateQuestions,
  useDocuments,
} from '@/services';
import { useAuthStore } from '@/stores/authStore';
import type { SummaryResponse, QuestionItem } from '@/services/export';

const exportSections = [
  { id: 'summary', label: 'Results Summary', included: true },
  { id: 'trends', label: 'Trend Analysis', included: true },
  { id: 'flagged', label: 'Flagged Values', included: true },
  { id: 'questions', label: 'Questions for Clinician', included: false },
];

export function ExportPage() {
  const prefersReducedMotion = useReducedMotion();
  const profileId = useAuthStore((state) => state.profileId);

  const [sections, setSections] = useState(exportSections);
  const [copied, setCopied] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);

  // API hooks
  const exportCSV = useExportCSV();
  const exportJSON = useExportJSON();
  const generateSummary = useGenerateSummary();
  const downloadSummary = useDownloadSummary();
  const generateQuestions = useGenerateQuestions();
  const { data: documents } = useDocuments({ profile_id: profileId || '' });

  const handleToggleSection = (id: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, included: !s.included } : s))
    );
  };

  const handleCopy = async () => {
    if (summary) {
      const text = summary.key_findings.join('\n');
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExportCSV = () => {
    exportCSV.mutate(undefined);
  };

  const handleExportJSON = () => {
    exportJSON.mutate(undefined);
  };

  const handleGenerateSummary = async () => {
    const includeQuestions = sections.find((s) => s.id === 'questions')?.included;
    const includeTrends = sections.find((s) => s.id === 'trends')?.included;

    try {
      const result = await generateSummary.mutateAsync({
        include_trends: includeTrends,
        include_questions: includeQuestions,
        format: 'text',
      });
      setSummary(result);

      // Also generate questions if enabled
      if (includeQuestions) {
        const questionsResult = await generateQuestions.mutateAsync();
        setQuestions(questionsResult);
      }
    } catch (error) {
      console.error('Failed to generate summary:', error);
    }
  };

  const handleDownloadSummary = () => {
    if (summary) {
      downloadSummary.mutate(summary.summary_id);
    }
  };

  const isLoading =
    exportCSV.isPending ||
    exportJSON.isPending ||
    generateSummary.isPending ||
    downloadSummary.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Export Summary
          </h1>
          <p className="text-ink-secondary mt-1">
            Generate a clinician-ready summary of your results
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            className="gap-2"
            onClick={handleExportCSV}
            disabled={isLoading}
          >
            {exportCSV.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileSpreadsheet className="w-4 h-4" />
            )}
            Download CSV
          </Button>
          <Button
            variant="secondary"
            className="gap-2"
            onClick={handleExportJSON}
            disabled={isLoading}
          >
            {exportJSON.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileJson className="w-4 h-4" />
            )}
            Download JSON
          </Button>
          {summary ? (
            <Button
              className="gap-2"
              onClick={handleDownloadSummary}
              disabled={isLoading}
            >
              {downloadSummary.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
              Download Summary
            </Button>
          ) : (
            <Button
              className="gap-2"
              onClick={handleGenerateSummary}
              disabled={isLoading}
            >
              {generateSummary.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Generate Summary
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-ink-secondary" />
                  Summary Preview
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopy}
                    className="gap-1.5"
                    disabled={!summary}
                  >
                    {copied ? (
                      <>
                        <Check className="w-4 h-4 text-status-verified" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        Copy Text
                      </>
                    )}
                  </Button>
                  <Button variant="ghost" size="sm" className="gap-1.5">
                    <Eye className="w-4 h-4" />
                    Full Preview
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {generateSummary.isPending ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-accent" />
                  <span className="ml-3 text-ink-secondary">Generating summary...</span>
                </div>
              ) : generateSummary.isError ? (
                <div className="flex items-center justify-center py-12 text-status-attention">
                  <AlertCircle className="w-6 h-6 mr-2" />
                  <span>Failed to generate summary. Please try again.</span>
                </div>
              ) : summary ? (
                <motion.div
                  initial={prefersReducedMotion ? {} : { opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="prose prose-sm max-w-none"
                >
                  <div className="flex items-center gap-3 mb-6 pb-4 border-b border-black/[0.08]">
                    <div className="w-12 h-12 rounded-xl bg-accent-subtle flex items-center justify-center">
                      <FileText className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                      <h2 className="text-lg font-display font-semibold text-ink m-0">
                        Health Summary Report
                      </h2>
                      <p className="text-sm text-ink-secondary m-0 flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5" />
                        Generated {new Date(summary.generated_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <section className="mb-6">
                    <h3 className="text-base font-semibold text-ink mb-3">
                      Results Summary
                    </h3>
                    <p className="text-sm text-ink-secondary leading-relaxed">
                      Date range: <strong>{summary.date_range}</strong>
                    </p>
                    <p className="text-sm text-ink-secondary leading-relaxed">
                      {summary.abnormal_count > 0 ? (
                        <>
                          <span className="text-status-attention font-medium">
                            {summary.abnormal_count} abnormal
                          </span>{' '}
                          value{summary.abnormal_count !== 1 ? 's' : ''} found.
                        </>
                      ) : (
                        'All values within reference ranges.'
                      )}
                    </p>
                  </section>

                  {summary.key_findings.length > 0 && (
                    <section className="mb-6">
                      <h3 className="text-base font-semibold text-ink mb-3">
                        Key Findings
                      </h3>
                      <div className="rounded-xl bg-surface-muted p-4">
                        <ul className="text-sm text-ink space-y-2 m-0 list-none pl-0">
                          {summary.key_findings.map((finding, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <AlertCircle className="w-4 h-4 text-status-attention flex-shrink-0 mt-0.5" />
                              {finding}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </section>
                  )}

                  {sections.find((s) => s.id === 'questions')?.included && questions.length > 0 && (
                    <section className="mb-6">
                      <h3 className="text-base font-semibold text-ink mb-3 flex items-center gap-2">
                        <MessageSquare className="w-4 h-4" />
                        Questions for Your Clinician
                      </h3>
                      <ul className="text-sm text-ink-secondary pl-4 space-y-2">
                        {questions.map((q, i) => (
                          <li key={i}>{q.question}</li>
                        ))}
                      </ul>
                    </section>
                  )}

                  <footer className="pt-4 border-t border-black/[0.08] text-xs text-ink-tertiary">
                    <p className="m-0">
                      This summary was generated by HealthCentral based on
                      uploaded laboratory reports. Reference ranges are as stated
                      in each source document. This is not medical advice—discuss
                      all results with your healthcare provider.
                    </p>
                  </footer>
                </motion.div>
              ) : (
                <div className="text-center py-12">
                  <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-4" />
                  <p className="text-ink-secondary">
                    Click "Generate Summary" to create a clinician-ready report.
                  </p>
                  <p className="text-sm text-ink-tertiary mt-2">
                    You can also download your data as CSV or JSON.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Include Sections</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => handleToggleSection(section.id)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-3 rounded-xl',
                    'transition-colors duration-200',
                    section.included
                      ? 'bg-accent-subtle'
                      : 'bg-surface-muted hover:bg-surface-sunken'
                  )}
                >
                  <span
                    className={cn(
                      'text-sm font-medium',
                      section.included ? 'text-accent' : 'text-ink-secondary'
                    )}
                  >
                    {section.label}
                  </span>
                  <div
                    className={cn(
                      'w-5 h-5 rounded-md flex items-center justify-center',
                      section.included
                        ? 'bg-accent text-white'
                        : 'bg-white border border-black/[0.12]'
                    )}
                  >
                    {section.included && <Check className="w-3 h-3" />}
                  </div>
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Source Documents</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {documents && documents.length > 0 ? (
                documents.slice(0, 5).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">
                        {doc.source || 'Lab Report'}
                      </p>
                      <p className="text-xs text-ink-tertiary">
                        {doc.collection_date
                          ? new Date(doc.collection_date).toLocaleDateString()
                          : 'No date'}
                      </p>
                    </div>
                    <Badge
                      variant={doc.status === 'parsed' ? 'verified' : 'default'}
                    >
                      {doc.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <p className="text-sm text-ink-tertiary text-center py-4">
                  No documents imported yet.
                </p>
              )}
            </CardContent>
          </Card>

          <div className="text-xs text-ink-tertiary text-center px-4">
            Export includes only information from your uploaded documents. No
            external data is added.
          </div>
        </div>
      </div>
    </div>
  );
}
