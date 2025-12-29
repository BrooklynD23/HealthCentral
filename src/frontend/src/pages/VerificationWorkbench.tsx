import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  CheckCircle,
  AlertTriangle,
  Edit3,
  Eye,
  ChevronDown,
  FileText,
  Info,
} from 'lucide-react';
import { Button, Card, CardContent, CardHeader, CardTitle, Badge } from '@/components/ui';
import { cn } from '@/utils/cn';
import { useReducedMotion } from '@/hooks/useReducedMotion';

const mockAnalytes = [
  {
    id: '1',
    name: 'Hemoglobin',
    value: '14.2',
    unit: 'g/dL',
    refRange: '12.0-17.5',
    status: 'normal',
    confidence: 'high',
    edited: false,
  },
  {
    id: '2',
    name: 'White Blood Cell Count',
    value: '11.8',
    unit: 'K/uL',
    refRange: '4.5-11.0',
    status: 'high',
    confidence: 'high',
    edited: false,
  },
  {
    id: '3',
    name: 'Platelet Count',
    value: '245',
    unit: 'K/uL',
    refRange: '150-400',
    status: 'normal',
    confidence: 'medium',
    edited: false,
  },
  {
    id: '4',
    name: 'Glucose, Fasting',
    value: '98',
    unit: 'mg/dL',
    refRange: '70-99',
    status: 'normal',
    confidence: 'high',
    edited: true,
  },
  {
    id: '5',
    name: 'Creatinine',
    value: '1.1',
    unit: 'mg/dL',
    refRange: '0.7-1.3',
    status: 'normal',
    confidence: 'low',
    edited: false,
  },
];

export function VerificationWorkbench() {
  const prefersReducedMotion = useReducedMotion();
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'high':
        return 'text-status-attention';
      case 'low':
        return 'text-status-caution';
      default:
        return 'text-ink';
    }
  };

  const getConfidenceBadge = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return <Badge variant="verified">High Confidence</Badge>;
      case 'medium':
        return <Badge variant="caution">Medium</Badge>;
      case 'low':
        return <Badge variant="attention">Low Confidence</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold text-ink tracking-tight">
            Verification Workbench
          </h1>
          <p className="text-ink-secondary mt-1">
            Review and correct extracted values from your documents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="caution" className="gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            2 items need review
          </Badge>
          <Button variant="secondary" className="gap-2">
            <Eye className="w-4 h-4" />
            View Source
          </Button>
          <Button className="gap-2">
            <CheckCircle className="w-4 h-4" />
            Mark All Verified
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <Card>
            <CardHeader className="border-b border-black/[0.04]">
              <CardTitle className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-ink-secondary" />
                Blood Test Results - Quest Diagnostics
                <Badge variant="default">Dec 15, 2024</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-black/[0.04] bg-surface-muted/50">
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Test Name
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Value
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Reference Range
                      </th>
                      <th className="text-left text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Status
                      </th>
                      <th className="text-right text-xs font-medium text-ink-secondary uppercase tracking-wide px-4 py-3">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {mockAnalytes.map((analyte, index) => (
                      <motion.tr
                        key={analyte.id}
                        initial={prefersReducedMotion ? {} : { opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={cn(
                          'border-b border-black/[0.04] transition-colors cursor-pointer',
                          selectedRow === analyte.id
                            ? 'bg-accent-subtle'
                            : 'hover:bg-surface-muted/50'
                        )}
                        onClick={() => setSelectedRow(analyte.id)}
                      >
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-ink">
                              {analyte.name}
                            </span>
                            {analyte.edited && (
                              <Badge variant="info" className="text-xs gap-1">
                                <Edit3 className="w-3 h-3" />
                                Edited
                              </Badge>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span
                            className={cn(
                              'font-mono font-semibold',
                              getStatusColor(analyte.status)
                            )}
                          >
                            {analyte.value}
                          </span>
                          <span className="text-ink-secondary ml-1 text-sm">
                            {analyte.unit}
                          </span>
                        </td>
                        <td className="px-4 py-4 text-sm text-ink-secondary font-mono">
                          {analyte.refRange} {analyte.unit}
                        </td>
                        <td className="px-4 py-4">
                          {getConfidenceBadge(analyte.confidence)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label="Edit value"
                            >
                              <Edit3 className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={(e) => {
                                e.stopPropagation();
                                setExpandedRow(
                                  expandedRow === analyte.id ? null : analyte.id
                                );
                              }}
                              aria-label="Expand details"
                            >
                              <ChevronDown
                                className={cn(
                                  'w-4 h-4 transition-transform',
                                  expandedRow === analyte.id && 'rotate-180'
                                )}
                              />
                            </Button>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-[3/4] rounded-xl bg-surface-muted flex items-center justify-center">
                <div className="text-center p-6">
                  <FileText className="w-12 h-12 text-ink-tertiary mx-auto mb-3" />
                  <p className="text-sm text-ink-secondary">
                    Select a row to preview the source document location
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-status-info-subtle border-status-info/20">
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Info className="w-5 h-5 text-status-info flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-medium text-ink text-sm mb-1">
                    Verification Tips
                  </h4>
                  <p className="text-xs text-ink-secondary leading-relaxed">
                    Click any value to edit. Low confidence items are flagged
                    for your review. All changes are tracked with "Edited"
                    badges.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
