import { describe, it, expect } from 'vitest';
import { doseFor, sourceUrl } from '../../src/tools/dose';

describe('doseFor', () => {
  it('reads the NHS paracetamol infant liquid bands', () => {
    const d = doseFor('liquid-120', 8);
    if (!d.ok) throw new Error(d.reason);
    expect(d.amount).toBe('5ml');
    expect(d.mg).toBe('120mg');
    expect(d.maxPerDay).toBe('4 doses in 24 hours');
    expect(d.intervalHours).toBe(4);
    expect(d.source.path).toContain('paracetamol-for-children');
    expect(doseFor('liquid-120', 4 * 12 + 11)).toMatchObject({ ok: true, amount: '10ml' });
  });
  it('carries the weight and vaccination notes for young babies', () => {
    const p = doseFor('liquid-120', 2);
    if (!p.ok) throw new Error(p.reason);
    expect(p.maxPerDay).toBe('2 doses in 24 hours');
    expect(p.notes[0]).toMatch(/over 4kg/);
    const i = doseFor('liquid-100', 4);
    if (!i.ok) throw new Error(i.reason);
    expect(i.amount).toBe('2.5ml');
    expect(i.notes[0]).toMatch(/more than 5kg/);
  });
  it('refuses ages below the table or at 18 and over instead of extrapolating', () => {
    expect(doseFor('liquid-120', 1)).toMatchObject({ ok: false, reason: expect.stringMatching(/not given under 2 months/) });
    expect(doseFor('liquid-100', 2)).toMatchObject({ ok: false, reason: expect.stringMatching(/not given under 3 months/) });
    expect(doseFor('liquid-250', 5 * 12)).toMatchObject({ ok: false });
    expect(doseFor('tablet-200', 18 * 12)).toMatchObject({ ok: false, reason: expect.stringMatching(/adult/) });
  });
  it('reads the ibuprofen liquid and tablet bands', () => {
    expect(doseFor('liquid-100', 10 * 12 + 6)).toMatchObject({ ok: true, amount: '15ml', mg: '300mg', intervalHours: 6 });
    expect(doseFor('liquid-100', 7)).toMatchObject({ ok: true, maxPerDay: '3 to 4 doses in 24 hours' });
    expect(doseFor('tablet-200', 14 * 12)).toMatchObject({ ok: true, amount: '1 or 2 tablets', mg: '200mg to 400mg' });
    expect(doseFor('melt-250', 10 * 12)).toMatchObject({ ok: true, amount: '2 tablets' });
  });
  it('points at the installed NHS book', () => {
    const d = doseFor('liquid-120', 8);
    expect(sourceUrl(d.source)).toBe('/read/nhs_medicines/www.nhs.uk/medicines/paracetamol-for-children/');
    expect(sourceUrl(d.source, 'nhs_uk')).toBe('/read/nhs_uk/www.nhs.uk/medicines/paracetamol-for-children/');
  });
});
