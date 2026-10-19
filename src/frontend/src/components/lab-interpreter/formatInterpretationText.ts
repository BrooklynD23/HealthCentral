/**
 * Display-side formatting for interpretation text.
 *
 * The backend keeps [KB:uuid] / [INT:uuid] markers on purpose (citation
 * validators gate on them); they are stripped here for display only.
 * Output is plain data, rendered as React nodes by callers (no HTML injection).
 */

export interface TextRun {
  bold: boolean;
  text: string;
}

const CITATION_MARKER = /\s*\[(KB|INT):[^\]\s]+\]/g;

function toRuns(line: string): TextRun[] {
  const runs: TextRun[] = [];
  const parts = line.split(/\*\*(.+?)\*\*/g);
  parts.forEach((part, i) => {
    if (part) runs.push({ bold: i % 2 === 1, text: part });
  });
  return runs;
}

export function formatInterpretationText(text: string): { paragraphs: TextRun[][] } {
  const stripped = text.replace(CITATION_MARKER, '');
  const paragraphs = stripped
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map(toRuns)
    .filter((runs) => runs.length > 0);
  return { paragraphs };
}
