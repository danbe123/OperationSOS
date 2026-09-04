import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../src/theme/themes.css', import.meta.url), 'utf8');

function block(selector: string): Record<string, string> {
  const start = css.indexOf(selector);
  expect(start, `selector ${selector} present`).toBeGreaterThan(-1);
  const open = css.indexOf('{', start);
  const close = css.indexOf('}', open);
  const vars: Record<string, string> = {};
  for (const m of css.slice(open + 1, close).matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) vars[m[1]] = m[2].trim();
  return vars;
}
function luminance(hex: string): number {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const themes: Record<string, Record<string, string>> = {
  vault: block(':root,\n:root[data-theme="vault"]'),
  field: block(':root[data-theme="field"]'),
  blackout: block(':root[data-theme="blackout"]'),
};

describe('theme contrast', () => {
  for (const [name, vars] of Object.entries(themes)) {
    for (const token of ['--text', '--text-muted', '--link', '--danger']) {
      for (const bg of ['--bg', '--bg-2']) {
        it(`${name}: ${token} on ${bg} is at least 7:1`, () => {
          expect(vars[token], `${token} defined`).toMatch(/^#[0-9a-f]{6}$/);
          expect(vars[bg], `${bg} defined`).toMatch(/^#[0-9a-f]{6}$/);
          expect(contrast(vars[token], vars[bg])).toBeGreaterThanOrEqual(7);
        });
      }
    }
  }
  it('print forces the field palette', () => {
    const printAt = css.indexOf('@media print');
    expect(printAt).toBeGreaterThan(-1);
    const printBlock = css.slice(printAt, css.indexOf('/* end print */', printAt));
    expect(printBlock).toContain('--bg: #f4efe4');
    expect(printBlock).toContain('--text: #1a1a1a');
  });
  it('body text never carries the display face or a text shadow', () => {
    expect(css).toMatch(/\.html,\s*\.checklist,\s*\.card-html[^{]*\{[^}]*font-family:\s*var\(--font-body\)[^}]*text-shadow:\s*none/);
  });
});
