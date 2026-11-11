// HC-E2ETC-001: structural pin for the e2e type-check (E2E-TYPECHECK).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = resolve(__dirname, '../..');
const read = (p: string) => readFileSync(resolve(root, p), 'utf8');

describe('HC-E2ETC-001 e2e type-check wiring', () => {
  it('tsconfig.e2e.json extends the base config and includes e2e', () => {
    const cfg = JSON.parse(read('tsconfig.e2e.json'));
    expect(cfg.extends).toBe('./tsconfig.json');
    expect(cfg.include).toContain('e2e');
  });

  it('package.json has the typecheck:e2e script', () => {
    const pkg = JSON.parse(read('package.json'));
    expect(pkg.scripts['typecheck:e2e']).toBe('tsc -p tsconfig.e2e.json');
  });

  it('ci.yml runs the e2e type-check', () => {
    expect(read('../../.github/workflows/ci.yml')).toContain('npm run typecheck:e2e');
  });
});
