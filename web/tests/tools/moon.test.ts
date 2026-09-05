import { describe, it, expect } from 'vitest';
import { moonPhase } from '../../src/tools/moon';

describe('moonPhase', () => {
  it('names the full moons of 3 January and 1 February 2026', () => {
    const jan = moonPhase(new Date(Date.UTC(2026, 0, 3, 10)));
    expect(jan.name).toBe('Full moon');
    expect(jan.illumination).toBeGreaterThan(0.98);
    expect(moonPhase(new Date(Date.UTC(2026, 1, 1, 22))).name).toBe('Full moon');   // 1 February 2026 22:09 UTC
  });
  it('names the new moon of 18 January 2026 and tracks waxing', () => {
    const n = moonPhase(new Date(Date.UTC(2026, 0, 18, 19)));
    expect(n.name).toBe('New moon');
    expect(n.illumination).toBeLessThan(0.02);
    const later = moonPhase(new Date(Date.UTC(2026, 0, 25)));
    expect(later.waxing).toBe(true);
    expect(later.name).toBe('First quarter');
  });
});
