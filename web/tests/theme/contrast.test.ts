import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';

const css = readFileSync(new URL('../../src/styles/tokens.css', import.meta.url), 'utf8');
const type = readFileSync(new URL('../../src/styles/type.css', import.meta.url), 'utf8');

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
  // Dim is the state the engine raises when the power is off at night, so it is a palette in its own
  // right and carries the same 7:1 floor. It used to be a brightness filter, which broke both.
  'vault dim': block(':root[data-dim="on"],\n:root[data-theme="vault"][data-dim="on"]'),
  'field dim': block(':root[data-theme="field"][data-dim="on"]'),
  'blackout dim': block(':root[data-theme="blackout"][data-dim="on"]'),
};

describe('theme contrast', () => {
  for (const [name, vars] of Object.entries(themes)) {
    // Every colour a reader has to read a word in, on both the page and a raised surface.
    for (const token of ['--ink', '--ink-muted', '--link', '--signal', '--danger', '--warn', '--ok']) {
      // --sunken as well as the page and the panel: inputs, table headers and the situation sheet's
      // chosen state button are all filled with it, and a state read on the wrong ground is a state
      // nobody measured.
      for (const bg of ['--ground', '--panel', '--sunken']) {
        it(`${name}: ${token} on ${bg} is at least 7:1`, () => {
          expect(vars[token], `${token} defined`).toMatch(/^#[0-9a-f]{6}$/);
          expect(vars[bg], `${bg} defined`).toMatch(/^#[0-9a-f]{6}$/);
          expect(contrast(vars[token], vars[bg])).toBeGreaterThanOrEqual(7);
        });
      }
    }
    it(`${name}: text on the primary action is at least 7:1`, () => {
      expect(contrast(vars['--on-signal'], vars['--signal'])).toBeGreaterThanOrEqual(7);
    });
  }

  for (const name of ['blackout', 'blackout dim']) {
    it(`${name} separates its three states by luminance, since it has one hue`, () => {
      const { '--danger': off, '--warn': patchy, '--ok': working } = themes[name];
      expect(luminance(off)).toBeLessThan(luminance(patchy));
      expect(luminance(patchy)).toBeLessThan(luminance(working));
    });
  }

  it('dim actually dims: every dim ground is darker than the theme it dims', () => {
    for (const [name, base] of [['vault', 'vault'], ['field', 'field'], ['blackout', 'blackout']] as const) {
      const dim = themes[`${name} dim`];
      expect(luminance(dim['--ground'])).toBeLessThanOrEqual(luminance(themes[base]['--ground']));
      expect(luminance(dim['--panel'])).toBeLessThanOrEqual(luminance(themes[base]['--panel']));
    }
  });

  it('dim never dims with a filter: a filtered body becomes the containing block for every overlay', () => {
    expect(css).not.toMatch(/data-dim[^{]*\{[^}]*filter:/);
  });

  it('print forces the field palette', () => {
    const printAt = css.indexOf('@media print');
    expect(printAt).toBeGreaterThan(-1);
    const printBlock = css.slice(printAt, css.indexOf('/* end print */', printAt));
    expect(printBlock).toContain('--ground: #f3efe4');
    expect(printBlock).toContain('--ink: #1b1b1b');
  });

  it('body text never carries the display face or a text shadow', () => {
    expect(type).toMatch(/\.html,[^{]*\{[^}]*font-family:\s*var\(--font-body\)[^}]*text-shadow:\s*none/);
  });
});
