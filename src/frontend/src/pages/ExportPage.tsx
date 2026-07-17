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
  Calendar,
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
  useGenerateVisitPrep,
  useDownloadVisitPrep,
  useGenerateFhirExport,
  useDownloadFhirExport,
  useDocuments,
} from '@/services';
import { useObservations } from '@/services/observations';
import { useAuthStore } from '@/stores/authStore';
import type {
  SummaryResponse,
  QuestionItem,
  ExportFormat,
  VisitPrepFormat,
  VisitPrepResponse,
  FhirExportResponse,
} from '@/services/export';

const exportSections = [
  { id: 'summary', label: 'Results Summary', included: true },
  { id: 'trends', label: 'Trend Analysis', included: true },
  { id: 'flagged', label: 'Flagged Values', included: true },
  { id: 'questions', label: 'Questions for Clinician', included: false },
];

const visitPrepSectionDefaults = [
  { id: 'medications', label: 'Current medications', included: true },
  { id: 'labs', label: 'Recent abnormal verified labs', included: true },
  { id: 'visits', label: 'Recent visits & diagnoses', included: true },
  { id: 'tasks', label: 'Open follow-up items', included: true },
  { id: 'questions', label: 'Questions for your provider', included: true },
];

export function ExportPage() {
  const prefersReducedMotion = useReducedMotion();
  const profileId = useAuthStore((state) => state.profileId);

  const [sections, setSections] = useState(exportSections);
  const [copied, setCopied] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('text');

  // Visit prep packet state (HC-M18)
  const [visitPrepSections, setVisitPrepSections] = useState(visitPrepSectionDefaults);
  const [reasonForVisit, setReasonForVisit] = useState('');
  const [visitPrepConfirmed, setVisitPrepConfirmed] = useState(false);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [visitPrep, setVisitPrep] = useState<VisitPrepResponse | null>(null);

  // FHIR R4 export state (HC-M22)
  const [fhirConfirmed, setFhirConfirmed] = useState(false);
  const [fhirExport, setFhirExport] = useState<FhirExportResponse | null>(null);

  // API hooks
  const exportCSV = useExportCSV();
  const exportJSON = useExportJSON();
  const generateSummary = useGenerateSummary();
  const downloadSummary = useDownloadSummary();
  const generateQuestions = useGenerateQuestions();
  const generateVisitPrep = useGenerateVisitPrep();
  const downloadVisitPrep = useDownloadVisitPrep();
  const generateFhirExport = useGenerateFhirExport();
  const downloadFhirExport = useDownloadFhirExport();
  const { data: documents } = useDocuments({ profile_id: profileId || '' });
  const { data: allObservations } = useObservations({ profile_id: profileId || '' });

  // Data quality: count low-confidence observations (UX-CONF-001)
  const lowConfidenceCount = allObservations?.filter(
    (obs) => obs.extraction_confidence != null && obs.extraction_confidence < 0.8
  ).length ?? 0;

  const handleToggleSection = (id: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, included: !s.included } : s))
    );
  };

  const handleCopy = async () => {
    if (summary) {
      const questionLines = questions.map((q) => `- ${q.question}`);
      const text = [
        ...summary.key_findings,
        ...(questionLines.length
          ? ['', 'Questions for your clinician:', ...questionLines]
          : []),
      ].join('\n');
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
      downloadSummary.mutate({ summaryId: summary.summary_id, format: exportFormat });
    }
  };

  const handleToggleVisitPrepSection = (id: string) => {
    setVisitPrepSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, included: !s.included } : s))
    );
    setVisitPrep(null);
  };

  const handleToggleSelectedDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
    setVisitPrep(null);
  };

  const visitPrepIncluded = (id: string) =>
    visitPrepSections.find((s) => s.id === id)?.included ?? true;

  const handleGenerateVisitPrep = async () => {
    if (!visitPrepConfirmed) return;
    try {
      const result = await generateVisitPrep.mutateAsync({
        reason_for_visit: reasonForVisit.trim() || undefined,
        include_medications: visitPrepIncluded('medications'),
        include_labs: visitPrepIncluded('labs'),
        include_visits: visitPrepIncluded('visits'),
        include_tasks: visitPrepIncluded('tasks'),
        include_questions: visitPrepIncluded('questions'),
        selected_doc_ids: selectedDocIds.length ? selectedDocIds : undefined,
        confirm: true,
      });
      setVisitPrep(result);
    } catch (error) {
      console.error('Failed to generate visit prep packet:', error);
    }
  };

  const handleDownloadVisitPrep = () => {
    if (visitPrep) {
      const format: VisitPrepFormat =
        exportFormat === 'text' ? 'markdown' : exportFormat;
      downloadVisitPrep.mutate({ packetId: visitPrep.packet_id, format });
    }
  };

  const handleGenerateFhirExport = async () => {
    if (!fhirConfirmed) return;
    try {
      const result = await generateFhirExport.mutateAsync({ confirm: true });
      setFhirExport(result);
    } catch (error) {
      console.error('Failed to generate FHIR export:', error);
    }
  };

  const handleDownloadFhirExport = () => {
    if (fhirExport) {
      downloadFhirExport.mutate(fhirExport.export_id);
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
          {(allObservations?.some((obs) => !obs.user_verified) ?? false) && (
            <Badge variant="caution">Contains unverified values</Badge>
          )}
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
        <div className="col-span-2 space-y-6">
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

          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-ink-secondary" />
                Visit Prep Packet
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <p className="text-sm text-ink-secondary">
                One packet for your next appointment: your reason for the
                visit, current medications, recent abnormal verified labs,
                open follow-up items, and questions for your provider.
                Unverified data is excluded, and personal identifiers are
                redacted before download.
              </p>

              <div>
                <label
                  htmlFor="reason-for-visit"
                  className="block text-sm font-medium text-ink mb-1.5"
                >
                  Reason for visit (optional)
                </label>
                <textarea
                  id="reason-for-visit"
                  value={reasonForVisit}
                  onChange={(e) => {
                    setReasonForVisit(e.target.value);
                    setVisitPrep(null);
                  }}
                  rows={2}
                  placeholder="e.g. Persistent headaches for two weeks"
                  className="w-full rounded-xl border border-black/[0.12] bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-tertiary focus:outline-none focus:ring-2 focus:ring-accent"
                />
              </div>

              <div>
                <p className="text-sm font-medium text-ink mb-1.5">Sections</p>
                <div className="grid grid-cols-2 gap-1.5">
                  {visitPrepSections.map((section) => (
                    <label
                      key={section.id}
                      className="flex items-center gap-2 text-sm text-ink-secondary cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={section.included}
                        onChange={() => handleToggleVisitPrepSection(section.id)}
                        className="rounded border-black/[0.2] text-accent focus:ring-accent"
                      />
                      {section.label}
                    </label>
                  ))}
                </div>
              </div>

              {documents && documents.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-ink mb-1.5">
                    Attach source documents (optional)
                  </p>
                  <div className="space-y-1.5 max-h-36 overflow-y-auto">
                    {documents.slice(0, 10).map((doc) => (
                      <label
                        key={doc.id}
                        className="flex items-center gap-2 text-sm text-ink-secondary cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={selectedDocIds.includes(doc.id)}
                          onChange={() => handleToggleSelectedDoc(doc.id)}
                          className="rounded border-black/[0.2] text-accent focus:ring-accent"
                        />
                        <span className="truncate">
                          {doc.source || 'Lab Report'}
                          {doc.collection_date
                            ? ` — ${new Date(doc.collection_date).toLocaleDateString()}`
                            : ''}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <label className="flex items-start gap-2 text-sm text-ink cursor-pointer rounded-xl bg-surface-muted px-3 py-3">
                <input
                  type="checkbox"
                  checked={visitPrepConfirmed}
                  onChange={(e) => setVisitPrepConfirmed(e.target.checked)}
                  className="mt-0.5 rounded border-black/[0.2] text-accent focus:ring-accent"
                />
                <span>
                  I understand this creates an exportable file containing my
                  health data and I want to generate it.
                </span>
              </label>

              {generateVisitPrep.isError && (
                <div className="flex items-center text-sm text-status-attention">
                  <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                  Failed to generate the packet. Please try again.
                </div>
              )}

              {visitPrep && (
                <div className="rounded-xl bg-surface-muted p-4 text-sm text-ink-secondary">
                  <p className="font-medium text-ink mb-1">Packet ready</p>
                  <p>
                    Sections: {visitPrep.section_titles.join(', ')}
                    {visitPrep.redaction_count > 0 &&
                      ` — ${visitPrep.redaction_count} personal identifier${
                        visitPrep.redaction_count !== 1 ? 's' : ''
                      } redacted`}
                  </p>
                </div>
              )}

              <div className="flex gap-3">
                <Button
                  className="gap-2"
                  onClick={handleGenerateVisitPrep}
                  disabled={!visitPrepConfirmed || generateVisitPrep.isPending}
                >
                  {generateVisitPrep.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <FileText className="w-4 h-4" />
                  )}
                  Generate Packet
                </Button>
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={handleDownloadVisitPrep}
                  disabled={!visitPrep || downloadVisitPrep.isPending}
                >
                  {downloadVisitPrep.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Download Packet
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <FileJson className="w-5 h-5 text-ink-secondary" />
                FHIR Export (R4)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <p className="text-sm text-ink-secondary">
                Export your verified health record as a FHIR R4 Bundle
                (JSON file) so other systems can read it. Only
                user-verified data is included, and personal identifiers
                are redacted before download. Export only — this file is
                never sent anywhere automatically.
              </p>

              <label className="flex items-start gap-2 text-sm text-ink cursor-pointer rounded-xl bg-surface-muted px-3 py-3">
                <input
                  type="checkbox"
                  checked={fhirConfirmed}
                  onChange={(e) => {
                    setFhirConfirmed(e.target.checked);
                    setFhirExport(null);
                  }}
                  className="mt-0.5 rounded border-black/[0.2] text-accent focus:ring-accent"
                />
                <span>
                  I understand this creates an exportable file containing my
                  health data and I want to generate it.
                </span>
              </label>

              {generateFhirExport.isError && (
                <div className="flex items-center text-sm text-status-attention">
                  <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                  Failed to generate the FHIR export. Please try again.
                </div>
              )}

              {fhirExport && (
                <div className="rounded-xl bg-surface-muted p-4 text-sm text-ink-secondary">
                  <p className="font-medium text-ink mb-1">Bundle ready</p>
                  <p>
                    {Object.entries(fhirExport.resource_counts)
                      .map(([type, count]) => `${count} ${type}`)
                      .join(', ')}
                    {fhirExport.redaction_count > 0 &&
                      ` — ${fhirExport.redaction_count} personal identifier${
                        fhirExport.redaction_count !== 1 ? 's' : ''
                      } redacted`}
                  </p>
                </div>
              )}

              <div className="flex gap-3">
                <Button
                  className="gap-2"
                  onClick={handleGenerateFhirExport}
                  disabled={!fhirConfirmed || generateFhirExport.isPending}
                >
                  {generateFhirExport.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <FileJson className="w-4 h-4" />
                  )}
                  Generate Bundle
                </Button>
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={handleDownloadFhirExport}
                  disabled={!fhirExport || downloadFhirExport.isPending}
                >
                  {downloadFhirExport.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Download Bundle
                </Button>
              </div>
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
                  aria-pressed={section.included}
                  aria-label={`${section.included ? 'Exclude' : 'Include'} ${section.label}`}
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
              <CardTitle className="text-base">Download Format</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(['text', 'html', 'pdf'] as ExportFormat[]).map((fmt) => (
                <button
                  key={fmt}
                  onClick={() => setExportFormat(fmt)}
                  className={cn(
                    'w-full flex items-center justify-between px-3 py-3 rounded-xl',
                    'transition-colors duration-200',
                    exportFormat === fmt
                      ? 'bg-accent-subtle'
                      : 'bg-surface-muted hover:bg-surface-sunken'
                  )}
                >
                  <span
                    className={cn(
                      'text-sm font-medium',
                      exportFormat === fmt ? 'text-accent' : 'text-ink-secondary'
                    )}
                  >
                    {fmt === 'text' ? 'Plain Text (.txt)' : fmt === 'html' ? 'HTML (.html)' : 'PDF (.pdf)'}
                  </span>
                  <div
                    className={cn(
                      'w-5 h-5 rounded-full flex items-center justify-center',
                      exportFormat === fmt
                        ? 'bg-accent'
                        : 'bg-white border border-black/[0.12]'
                    )}
                  >
                    {exportFormat === fmt && (
                      <div className="w-2 h-2 rounded-full bg-white" />
                    )}
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

          {lowConfidenceCount > 0 && (
            <Card className="border-status-caution/30">
              <CardContent className="p-4">
                <div className="flex gap-3">
                  <AlertCircle className="w-5 h-5 text-status-caution flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-ink mb-1">
                      Data Quality Note
                    </p>
                    <p className="text-xs text-ink-secondary leading-relaxed">
                      {lowConfidenceCount} observation{lowConfidenceCount !== 1 ? 's have' : ' has'} lower
                      extraction confidence (&lt; 80%). Review these in the
                      Verification Workbench before sharing with your clinician.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="text-xs text-ink-tertiary text-center px-4">
            Export includes only information from your uploaded documents. No
            external data is added.
          </div>
        </div>
      </div>
    </div>
  );
}
