/**
 * AboutPage: the public About page at /about (UI-ABOUT; plan §4.2 About row, motion §2.6 S1-S4, data-t0 §2.7).
 *
 * Public by design: it sits outside ProtectedRoute and AppLayout, so a visitor with no profile can read it. It reads
 * no data and no session, so it imports no service, no auth store and no query hook, and makes no request. Every
 * asset is local (no remote font, image or embed).
 *
 * Motion (§4.2):
 * - T0 (still, data-t0), outside every ShowcaseReveal: the safety statement, the not-medical-advice text, the
 *   local-first statement and the "Example data, not yours" label.
 * - S4: the hero is RangeRibbon over EXAMPLE_TREND, unchanged and not wrapped, so its own clip-path draw (M10, 640 ms)
 *   is the one draw. The plan's S4 row says 1.2 s; the recorded L1 reading is that the ribbon keeps M10.
 * - S1: ShowcaseReveal around the non-T0 sections only (how it works, capstone).
 * - S2: BeamBorder round the single call to action.
 * - S3: ThinkingOrb (64 px) in the how-it-works part; its status prop is the visible line.
 *
 * The route has no shell, so there is no Safety Rail, as on /setup. The page's own safety statement stands in for it.
 */
import { Link } from 'react-router-dom';
import { RangeRibbon } from '@/components/results/RangeRibbon';
import { BeamBorder } from '@/components/ui/BeamBorder';
import { Button } from '@/components/ui/Button';
import { ShowcaseReveal } from '@/components/ui/ShowcaseReveal';
import { ThinkingOrb } from '@/components/ui/ThinkingOrb';
import type { TrendData } from '@/services/types';

/**
 * Made-up numbers for an invented test. It is not a real analyte, so the page states no clinical reference value, and
 * it names no person. Three points are checked and the last is not, so the ribbon shows both marks.
 */
const EXAMPLE_TREND: TrendData = {
  analyte_canonical: 'example-analyte',
  analyte_display_name: 'Example analyte',
  unit: 'units',
  ref_low: 40,
  ref_high: 60,
  summary: '',
  data_points: [
    { date: '2026-01-12', value: 46, unit: 'units', is_abnormal: false, flag: null, doc_id: 'example', extraction_confidence: null, user_verified: true },
    { date: '2026-03-02', value: 53, unit: 'units', is_abnormal: false, flag: null, doc_id: 'example', extraction_confidence: null, user_verified: true },
    { date: '2026-05-18', value: 62, unit: 'units', is_abnormal: true, flag: null, doc_id: 'example', extraction_confidence: null, user_verified: true },
    { date: '2026-08-03', value: 56, unit: 'units', is_abnormal: false, flag: null, doc_id: 'example', extraction_confidence: null, user_verified: false },
  ],
};

const STEPS: Array<{ name: string; text: string }> = [
  { name: 'Import', text: 'Add a lab report from a file on this device. Its text is read here.' },
  { name: 'Review values', text: 'Check each value against the page it was read from, and correct anything that was misread.' },
  { name: 'Results', text: 'See each value over time, next to the reference range used for that chart.' },
  { name: 'Ask', text: 'Ask a question about your results. Answers point to the sources they come from.' },
];

export function AboutPage() {
  return (
    <div className="min-h-screen bg-surface px-4 py-10 text-ink sm:px-6 sm:py-16">
      <main className="mx-auto w-full max-w-3xl space-y-10">
        <header className="space-y-3">
          <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">About Asclexis</h1>
          <p className="text-lg text-ink-secondary">
            A local-first companion that explains your own medical results, with sources. It helps you ask better
            questions. Your healthcare provider can tell you what your results mean for you.
          </p>
        </header>

        <section aria-label="What Asclexis is and is not" className="space-y-3">
          <p data-t0 data-about-safety>
            Asclexis is not a medical device. It does not diagnose a condition, and it does not suggest doses or changes
            to any treatment.
          </p>
          <p data-t0 data-about-not-advice>
            Education, not medical advice. It explains what your report says and where each value came from, so you can
            ask your healthcare provider what it means for you.
          </p>
          <p data-t0 data-about-local-first>
            Your records stay on this device, in an encrypted file for each profile. There is no cloud copy to restore
            from. The one exception is an optional external AI setting, which is off unless you turn it on.
          </p>
        </section>

        <section aria-labelledby="about-example-label" className="space-y-3">
          <p id="about-example-label" data-t0 data-about-example-label className="text-sm font-medium text-ink">
            Example data, not yours
          </p>
          <RangeRibbon trend={EXAMPLE_TREND} />
        </section>

        <ShowcaseReveal id="about">
          <section data-about-group="how-it-works" aria-labelledby="about-how-heading" className="space-y-4">
            <h2 id="about-how-heading" className="font-display text-2xl font-semibold tracking-tight">
              How it works
            </h2>
            <ThinkingOrb size={64} status="How it reads a report" />
            <ol aria-labelledby="about-how-heading" className="space-y-3">
              {STEPS.map((step, index) => (
                <li key={step.name} className="flex gap-3">
                  <span aria-hidden="true" className="w-6 shrink-0 text-ink-secondary">
                    {index + 1}.
                  </span>
                  <p>
                    <span className="font-medium">{step.name}.</span> <span className="text-ink-secondary">{step.text}</span>
                  </p>
                </li>
              ))}
            </ol>
          </section>

          <section data-about-group="capstone" aria-labelledby="about-capstone-heading" className="space-y-3">
            <h2 id="about-capstone-heading" className="font-display text-2xl font-semibold tracking-tight">
              Capstone project
            </h2>
            <p className="text-ink-secondary">
              Asclexis is a capstone project. This page is part of the demo: the chart above uses made-up numbers, and
              nothing on this page reads your records.
            </p>
          </section>
        </ShowcaseReveal>

        <BeamBorder active className="inline-block rounded-xl p-1">
          <Button asChild size="lg">
            <Link to="/">Open Asclexis</Link>
          </Button>
        </BeamBorder>
      </main>
    </div>
  );
}
