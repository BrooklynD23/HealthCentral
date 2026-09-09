/**
 * HC-CAP-101..105 — per-tier capability disclosure in Settings.
 *
 * The tier list previously said only whether hardware could run a tier, never
 * what that tier would then be able to do. A user picking "low" had no way to
 * learn it will never support the agentic features.
 *
 * Disclosure, not gating: nothing is refused on these flags today.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { TierCapabilities } from '../components/settings/TierCapabilities';

const agentic = {
  context_size: 16384,
  multimodal: false,
  function_calling: true,
  agentic_capable: true,
};

const basic = {
  context_size: 2048,
  multimodal: false,
  function_calling: false,
  agentic_capable: false,
};

const noModel = {
  context_size: 0,
  multimodal: false,
  function_calling: false,
  agentic_capable: false,
};

describe('TierCapabilities', () => {
  it('HC-CAP-101 shows the context window in a human unit', () => {
    render(<TierCapabilities capabilities={agentic} />);
    expect(screen.getByText(/16K context/i)).toBeInTheDocument();
  });

  it('HC-CAP-102 says tool support is unconfirmed, never that it is absent', () => {
    render(<TierCapabilities capabilities={basic} />);
    // `function_calling` is a DECLARATION in TIER_MODEL_CONFIG, and most tiers
    // do not declare it. Rendering that silence as "no assistant tools" would
    // state a config gap as a model property — Phi-4-mini and BioMistral both
    // support tool calling regardless of what the config says.
    expect(screen.getByText(/tool support unconfirmed/i)).toBeInTheDocument();
    expect(screen.queryByText(/no assistant tools/i)).not.toBeInTheDocument();
  });

  it('HC-CAP-103 marks a tool-calling tier as supporting assistant features', () => {
    render(<TierCapabilities capabilities={agentic} />);
    expect(screen.getByText(/^assistant tools$/i)).toBeInTheDocument();
    expect(screen.queryByText(/unconfirmed/i)).not.toBeInTheDocument();
  });

  it('HC-CAP-104 renders the no-model tier without claiming a context window', () => {
    render(<TierCapabilities capabilities={noModel} />);
    expect(screen.queryByText(/0K context/i)).not.toBeInTheDocument();
    expect(screen.getByText(/no local model/i)).toBeInTheDocument();
  });

  it('HC-CAP-105 renders nothing rather than crashing when data is absent', () => {
    const { container } = render(<TierCapabilities capabilities={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
