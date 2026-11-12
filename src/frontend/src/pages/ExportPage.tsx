/**
 * ExportPage - Export data and generate summaries
 *
 * Sprint 4: Wired to real API for CSV/JSON export and summary generation.
 */

import { useState } from 'react';
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
import { Checkbox } from '@/components/ui/Checkbox';
import { Sheet } from '@/components/ui/Sheet';
import { cn } from '@/utils/cn';
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

/**
 * What the redaction level means today. Kept truthful: strict is pattern-based, the patient's own CSV and JSON
 * exports are exempt (owner decision D3), and the question lines come from POST /export/questions, which does no
 * redaction, so they and the text Copy Text copies are not redacted. Read-only: the level is not a setting here.
 */
const REDACTION_COPY =
  'Redaction level: strict. Personal identifiers that match known patterns are removed before this summary is saved or downloaded. CSV and JSON downloads are your own unredacted copy of your lab results. The question lines shown in this preview, and in text copied with Copy Text, are not redacted.';

function RedactionNote({ className }: { className?: string }) {
  return (
    <p data-t0 className={cn('text-xs text-ink-secondary leading-relaxed', className)}>
      {REDACTION_COPY}
    </p>
  );
}

/** The summary values. The inline preview and the Full Preview sheet both render this, so they cannot drift. */
function SummaryBody({
  summary,
  questions,
  showQuestions,
}: {
  summary: SummaryResponse;
  questions: QuestionItem[];
  showQuestions: boolean;
}) {
  return (
    <div className="prose prose-sm max-w-none">
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-black/8">
        <div className="w-12 h-12 shrink-0 rounded-xl bg-accent-subtle flex items-center justify-center">
          <FileText className="w-6 h-6 text-accent" />
        </div>
        <div className="min-w-0">
          <h2 className="text-lg font-display font-semibold text-ink m-0">
            Health Summary Report
          </h2>
          <p data-t0 className="text-sm text-ink-secondary m-0 flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5 shrink-0" />
            Generated {new Date(summary.generated_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      <section className="mb-6">
        <h3 className="text-base font-semibold text-ink mb-3">
          Results Summary
        </h3>
        <p className="text-sm text-ink-secondary leading-relaxed">
          Date range: <strong data-t0>{summary.date_range}</strong>
        </p>
        <p data-t0 className="text-sm text-ink-secondary leading-relaxed">
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
            <ul data-t0 className="text-sm text-ink space-y-2 m-0 list-none pl-0">
              {summary.key_findings.map((finding, i) => (
                <li key={i} className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-status-attention shrink-0 mt-0.5" />
                  <span className="min-w-0 break-words">{finding}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {showQuestions && questions.length > 0 && (
        <section className="mb-6">
          <h3 className="text-base font-semibold text-ink mb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4" />
            Questions for Your Clinician
          </h3>
          <ul data-t0 className="text-sm text-ink-secondary pl-4 space-y-2">
            {questions.map((q, i) => (
              <li key={i} className="break-words">{q.question}</li>
            ))}
          </ul>
        </section>
      )}

      <footer data-t0 className="pt-4 border-t border-black/8 text-xs text-ink-tertiary">
        <p className="m-0">
          This summary was generated by Asclexis based on
          uploaded laboratory reports. Reference ranges are as stated
          in each source document. This is not medical advice—discuss
          all results with your healthcare provider.
        </p>
      </footer>
    </div>
  );
}

export function ExportPage() {
  const profileId = useAuthStore((state) => state.profileId);

  const [sections, setSections] = useState(exportSections);
  const [copied, setCopied] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  // Whether the summary on screen was generated with Questions ticked (the download needs it to honour a later untick).
  const [summaryHadQuestions, setSummaryHadQuestions] = useState(false);
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

  const showQuestionsInSummary = sections.find((s) => s.id === 'questions')?.included ?? false;

  const handleCopy = async () => {
    if (summary) {
      // Same rule as the preview: question lines are copied only while the Questions section is ticked.
      const questionLines = showQuestionsInSummary ? questions.map((q) => `- ${q.question}`) : [];
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

      // Also generate questions if enabled. Await them before showing the summary so the preview does not
      // grow when they arrive; a questions failure must not hide the summary.
      let questionsResult: QuestionItem[] = [];
      if (includeQuestions) {
        try {
          questionsResult = await generateQuestions.mutateAsync();
        } catch (questionsError) {
          console.error('Failed to generate questions:', questionsError);
        }
      }
      setQuestions(questionsResult);
      setSummary(result);
      setSummaryHadQuestions(Boolean(includeQuestions));
    } catch (error) {
      console.error('Failed to generate summary:', error);
    }
  };

  const handleDownloadSummary = () => {
    if (summary) {
      // Questions unticked after generating with them: ask the download to leave them out, as the preview and Copy Text do.
      downloadSummary.mutate({
        summaryId: summary.summary_id,
        format: exportFormat,
        omitQuestions: summaryHadQuestions && !showQuestionsInSummary,
      });
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
    generateQuestions.isPending ||
    downloadSummary.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Export Summary
          </h1>
          <p className="text-ink-secondary mt-1">
            Generate a clinician-ready summary of your results
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
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
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
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
              <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
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
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
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
                <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
              ) : (
                <FileText className="w-4 h-4" />
              )}
              Generate Summary
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <Card>
            <CardHeader className="border-b border-black/4">
              <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <FileText className="w-5 h-5 text-ink-secondary" />
                  Summary Preview
                </div>
                <div className="flex flex-wrap items-center gap-2">
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
                  {/* The Sheet's trigger is this button, so Escape returns focus to it. */}
                  <Sheet
                    still
                    title="Full summary preview"
                    trigger={
                      <Button variant="ghost" size="sm" className="gap-1.5" disabled={!summary}>
                        <Eye className="w-4 h-4" />
                        Full Preview
                      </Button>
                    }
                  >
                    {summary && (
                      <div className="min-w-0 space-y-6">
                        <SummaryBody
                          summary={summary}
                          questions={questions}
                          showQuestions={showQuestionsInSummary}
                        />
                        <RedactionNote className="border-t border-black/8 pt-4" />
                      </div>
                    )}
                  </Sheet>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {/* First child, above the area that swaps between empty, spinner and summary, so it never moves. */}
              <RedactionNote className="mb-6 border-b border-black/8 pb-4" />
              {generateSummary.isPending || generateQuestions.isPending ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 motion-safe:animate-spin text-accent" />
                  <span className="ml-3 text-ink-secondary">Generating summary...</span>
                </div>
              ) : generateSummary.isError ? (
                <div className="flex items-center justify-center py-12 text-status-attention">
                  <AlertCircle className="w-6 h-6 mr-2" />
                  <span>Failed to generate summary. Please try again.</span>
                </div>
              ) : summary ? (
                <SummaryBody
                  summary={summary}
                  questions={questions}
                  showQuestions={showQuestionsInSummary}
                />
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
            <CardHeader className="border-b border-black/4">
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
                  className="w-full rounded-xl border border-black/12 bg-surface-elevated px-3 py-2 text-sm text-ink placeholder:text-ink-tertiary focus:outline-hidden focus:ring-2 focus:ring-accent"
                />
              </div>

              <div>
                <p className="text-sm font-medium text-ink mb-1.5">Sections</p>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {visitPrepSections.map((section) => (
                    <div key={section.id} className="flex min-w-0 items-center gap-2">
                      <Checkbox
                        id={`visit-prep-section-${section.id}`}
                        checked={section.included}
                        onCheckedChange={() => handleToggleVisitPrepSection(section.id)}
                      />
                      <label
                        htmlFor={`visit-prep-section-${section.id}`}
                        className="min-w-0 flex-1 cursor-pointer break-words py-1 text-sm text-ink-secondary"
                      >
                        {section.label}
                      </label>
                    </div>
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
                      <div key={doc.id} className="flex min-w-0 items-center gap-2">
                        <Checkbox
                          id={`visit-prep-doc-${doc.id}`}
                          checked={selectedDocIds.includes(doc.id)}
                          onCheckedChange={() => handleToggleSelectedDoc(doc.id)}
                        />
                        <label
                          htmlFor={`visit-prep-doc-${doc.id}`}
                          className="min-w-0 flex-1 cursor-pointer truncate py-1 text-sm text-ink-secondary"
                        >
                          {doc.source || 'Lab Report'}
                          {doc.collection_date
                            ? ` — ${new Date(doc.collection_date).toLocaleDateString()}`
                            : ''}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex items-start gap-3 rounded-xl bg-surface-muted px-3 py-3">
                <Checkbox
                  id="visit-prep-confirm"
                  checked={visitPrepConfirmed}
                  onCheckedChange={(checked) => setVisitPrepConfirmed(checked === true)}
                />
                <label
                  htmlFor="visit-prep-confirm"
                  className="min-w-0 flex-1 cursor-pointer break-words text-sm text-ink"
                >
                  I understand this creates an exportable file containing my
                  health data and I want to generate it.
                </label>
              </div>

              {generateVisitPrep.isError && (
                <div className="flex items-center text-sm text-status-attention">
                  <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
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

              <div className="flex flex-wrap gap-3">
                <Button
                  className="gap-2"
                  onClick={handleGenerateVisitPrep}
                  disabled={!visitPrepConfirmed || generateVisitPrep.isPending}
                >
                  {generateVisitPrep.isPending ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
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
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Download Packet
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="border-b border-black/4">
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

              <div className="flex items-start gap-3 rounded-xl bg-surface-muted px-3 py-3">
                <Checkbox
                  id="fhir-confirm"
                  checked={fhirConfirmed}
                  onCheckedChange={(checked) => {
                    setFhirConfirmed(checked === true);
                    setFhirExport(null);
                  }}
                />
                <label
                  htmlFor="fhir-confirm"
                  className="min-w-0 flex-1 cursor-pointer break-words text-sm text-ink"
                >
                  I understand this creates an exportable file containing my
                  health data and I want to generate it.
                </label>
              </div>

              {generateFhirExport.isError && (
                <div className="flex items-center text-sm text-status-attention">
                  <AlertCircle className="w-4 h-4 mr-2 shrink-0" />
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

              <div className="flex flex-wrap gap-3">
                <Button
                  className="gap-2"
                  onClick={handleGenerateFhirExport}
                  disabled={!fhirConfirmed || generateFhirExport.isPending}
                >
                  {generateFhirExport.isPending ? (
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
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
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  Download Bundle
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="min-w-0 space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Include Sections</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {sections.map((section) => (
                <div
                  key={section.id}
                  className={cn(
                    'flex items-center gap-3 rounded-xl px-3',
                    'transition-colors duration-200',
                    section.included
                      ? 'bg-accent-subtle'
                      : 'bg-surface-muted hover:bg-surface-sunken'
                  )}
                >
                  <Checkbox
                    id={`export-section-${section.id}`}
                    checked={section.included}
                    onCheckedChange={() => handleToggleSection(section.id)}
                  />
                  <label
                    htmlFor={`export-section-${section.id}`}
                    className={cn(
                      'min-w-0 flex-1 cursor-pointer break-words py-3 text-sm font-medium',
                      section.included ? 'text-accent' : 'text-ink-secondary'
                    )}
                  >
                    {section.label}
                  </label>
                </div>
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
                        : 'bg-surface-elevated border border-black/12'
                    )}
                  >
                    {exportFormat === fmt && (
                      <div className="w-2 h-2 rounded-full bg-[var(--on-accent)]" />
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
                    className="flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-surface-muted"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink break-words">
                        {doc.source || 'Lab Report'}
                      </p>
                      <p className="text-xs text-ink-tertiary">
                        {doc.collection_date
                          ? new Date(doc.collection_date).toLocaleDateString()
                          : 'No date'}
                      </p>
                    </div>
                    <Badge
                      className="shrink-0"
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
                  <AlertCircle className="w-5 h-5 text-status-caution shrink-0 mt-0.5" />
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
