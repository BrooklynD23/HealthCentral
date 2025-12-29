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
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const exportSections = [
  { id: 'summary', label: 'Results Summary', included: true },
  { id: 'trends', label: 'Trend Analysis', included: true },
  { id: 'flagged', label: 'Flagged Values', included: true },
  { id: 'questions', label: 'Questions for Clinician', included: false },
];

export function ExportPage() {
  const prefersReducedMotion = useReducedMotion();
  const [sections, setSections] = useState(exportSections);
  const [copied, setCopied] = useState(false);

  const handleToggleSection = (id: string) => {
    setSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, included: !s.included } : s))
    );
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText('Summary content would be copied here...');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
          <Button variant="secondary" className="gap-2">
            <Printer className="w-4 h-4" />
            Print
          </Button>
          <Button className="gap-2">
            <Download className="w-4 h-4" />
            Download PDF
          </Button>
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
                      Generated December 28, 2024
                    </p>
                  </div>
                </div>

                <section className="mb-6">
                  <h3 className="text-base font-semibold text-ink mb-3">
                    Results Summary
                  </h3>
                  <p className="text-sm text-ink-secondary leading-relaxed">
                    This report summarizes laboratory results from{' '}
                    <strong>4 documents</strong> spanning June 2024 to December
                    2024. Results are organized by test panel with reference
                    ranges as reported by each laboratory.
                  </p>
                </section>

                <section className="mb-6">
                  <h3 className="text-base font-semibold text-ink mb-3">
                    Complete Blood Count (CBC)
                  </h3>
                  <div className="rounded-xl bg-surface-muted p-4">
                    <table className="w-full text-sm m-0">
                      <thead>
                        <tr className="border-b border-black/[0.08]">
                          <th className="text-left font-medium text-ink-secondary py-2">
                            Test
                          </th>
                          <th className="text-left font-medium text-ink-secondary py-2">
                            Result
                          </th>
                          <th className="text-left font-medium text-ink-secondary py-2">
                            Reference
                          </th>
                          <th className="text-left font-medium text-ink-secondary py-2">
                            Status
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-black/[0.04]">
                          <td className="py-2 text-ink">Hemoglobin</td>
                          <td className="py-2 font-mono">14.2 g/dL</td>
                          <td className="py-2 text-ink-secondary">
                            12.0-17.5 g/dL
                          </td>
                          <td className="py-2">
                            <Badge variant="verified">Normal</Badge>
                          </td>
                        </tr>
                        <tr className="border-b border-black/[0.04]">
                          <td className="py-2 text-ink">WBC Count</td>
                          <td className="py-2 font-mono text-status-attention">
                            11.8 K/uL
                          </td>
                          <td className="py-2 text-ink-secondary">
                            4.5-11.0 K/uL
                          </td>
                          <td className="py-2">
                            <Badge variant="attention">High</Badge>
                          </td>
                        </tr>
                        <tr>
                          <td className="py-2 text-ink">Platelets</td>
                          <td className="py-2 font-mono">245 K/uL</td>
                          <td className="py-2 text-ink-secondary">
                            150-400 K/uL
                          </td>
                          <td className="py-2">
                            <Badge variant="verified">Normal</Badge>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="mb-6">
                  <h3 className="text-base font-semibold text-ink mb-3">
                    Values Outside Reference Range
                  </h3>
                  <div className="rounded-xl bg-status-attention-subtle p-4">
                    <p className="text-sm text-ink m-0">
                      <strong>WBC Count (11.8 K/uL):</strong> Slightly above the
                      reference range of 4.5-11.0 K/uL as stated in the Quest
                      Diagnostics report dated December 15, 2024.
                    </p>
                  </div>
                </section>

                {sections.find((s) => s.id === 'questions')?.included && (
                  <section className="mb-6">
                    <h3 className="text-base font-semibold text-ink mb-3 flex items-center gap-2">
                      <MessageSquare className="w-4 h-4" />
                      Questions for Your Clinician
                    </h3>
                    <ul className="text-sm text-ink-secondary pl-4 space-y-2">
                      <li>
                        Should I be concerned about the elevated WBC count?
                      </li>
                      <li>
                        Are there any lifestyle changes that could affect these
                        results?
                      </li>
                      <li>When should I schedule follow-up testing?</li>
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
              {[
                { name: 'Quest Diagnostics', date: 'Dec 15, 2024' },
                { name: 'LabCorp', date: 'Dec 10, 2024' },
                { name: 'Primary Care', date: 'Nov 28, 2024' },
              ].map((doc, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between px-3 py-2.5 rounded-xl bg-surface-muted"
                >
                  <div>
                    <p className="text-sm font-medium text-ink">{doc.name}</p>
                    <p className="text-xs text-ink-tertiary">{doc.date}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-ink-tertiary" />
                </div>
              ))}
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
