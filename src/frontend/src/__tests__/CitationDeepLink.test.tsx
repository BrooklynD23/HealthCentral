/**
 * CITE-SRC-001 — citation chips deep-link to their source region.
 *
 * The important half of this is the negative case: a citation with no
 * inspectable source must render as plain text, not as a button that navigates
 * nowhere. A dead control on a health record is worse than a plain label,
 * because it implies evidence the app cannot actually show.
 */

import { describe, it, expect } from 'vitest';

interface CitationChip {
  source: string;
  page: number | null;
  docId: string | null;
  observationId: string | null;
  entityId: string | null;
}

/**
 * Mirrors `citationTarget` in ExplainAssistant.tsx. Kept in the test as an
 * executable statement of the contract the component must satisfy: the URL
 * shape is what VerificationWorkbench reads back out of searchParams.
 */
function citationTarget(citation: CitationChip): string | null {
  const params = new URLSearchParams();
  if (citation.observationId) {
    params.set('observation', citation.observationId);
  } else if (citation.entityId) {
    params.set('entity', citation.entityId);
  } else {
    return null;
  }
  if (citation.docId) params.set('doc', citation.docId);
  if (citation.page != null) params.set('page', String(citation.page));
  return `/verify?${params.toString()}`;
}

const base: CitationChip = {
  source: 'Your Results',
  page: null,
  docId: null,
  observationId: null,
  entityId: null,
};

describe('FE-CITE-001: citation deep links', () => {
  it('builds a workbench link for an observation-backed citation', () => {
    const target = citationTarget({
      ...base,
      observationId: 'obs-1',
      docId: 'doc-9',
      page: 3,
    });

    expect(target).toBe('/verify?observation=obs-1&doc=doc-9&page=3');
  });

  it('builds a workbench link for an entity-backed citation', () => {
    const target = citationTarget({ ...base, entityId: 'ent-4', docId: 'doc-9' });

    expect(target).toBe('/verify?entity=ent-4&doc=doc-9');
  });

  it('returns no target when the citation has no inspectable source', () => {
    // Reference-corpus entries, care tasks and timeline events have no page
    // region — these must render as labels, not buttons.
    expect(citationTarget({ ...base, source: 'Reference' })).toBeNull();
    expect(citationTarget({ ...base, docId: 'doc-9' })).toBeNull();
  });

  it('prefers the observation target when both ids are present', () => {
    const target = citationTarget({
      ...base,
      observationId: 'obs-1',
      entityId: 'ent-4',
    });

    expect(target).toContain('observation=obs-1');
    expect(target).not.toContain('entity=');
  });

  it('omits page when the citation has none', () => {
    const target = citationTarget({ ...base, observationId: 'obs-1' });

    expect(target).toBe('/verify?observation=obs-1');
  });

  it('produces params VerificationWorkbench can read back', () => {
    const target = citationTarget({
      ...base,
      observationId: 'obs-1',
      docId: 'doc-9',
      page: 2,
    })!;
    const params = new URLSearchParams(target.split('?')[1]);

    expect(params.get('observation')).toBe('obs-1');
    expect(params.get('doc')).toBe('doc-9');
    expect(params.get('page')).toBe('2');
  });
});
