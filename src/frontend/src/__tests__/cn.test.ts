import { describe, it, expect } from 'vitest';
import { cn } from '@/utils/cn';

describe('cn', () => {
  it('lets outline-hidden replace outline-none (tailwind-merge 3 knows v4 outline utilities)', () => {
    expect(cn('outline-none', 'outline-hidden')).toBe('outline-hidden');
  });
});
