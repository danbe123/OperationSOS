import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/* The chosen state must differ from the other two by more than its colour, and what decided that was
 * a specificity tie: `.state-set` and `.btn` are one class each, so whichever stylesheet the build
 * put last won the ground, and `.btn` won. jsdom has no cascade and the suite runs with `css: false`,
 * so the fill itself is measured in the browser (`e2e/situation.spec.ts`, all six palettes); what is
 * checked here is the thing that made it lose — a rule that cannot outrank the one it fights. */

/** The sheet with its comments taken out, so a selector is only ever read as a selector. */
const read = (file: string) => readFileSync(resolve(process.cwd(), file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
/** A class-only selector's weight is the number of classes in it; the sheet uses no ids. */
const classes = (selector: string) => (selector.match(/\./g) ?? []).length;
/** The declarations of the first rule whose selector list contains `selector`. */
function rule(css: string, selector: string): string {
  const found = [...css.matchAll(/([^{}]+)\{([^}]*)\}/g)].find((m) => m[1].split(',').some((s) => s.trim() === selector));
  expect(found, `no rule for ${selector}`).toBeTruthy();
  return found![2];
}

describe('the chosen state button', () => {
  const sheet = read('src/screens/situation.css');
  const components = read('src/styles/components.css');

  it('asks for the sunken ground with a rule that outranks the plain button', () => {
    expect(rule(sheet, '.state-btn.state-set')).toContain('background: var(--sunken)');
    expect(classes('.state-btn.state-set')).toBeGreaterThan(classes('.btn'));
    // and the rule it has to beat really is the one-class one it kept losing to
    expect(rule(components, '.btn')).toContain('background: var(--panel)');
  });

  it('carries a 3 px inset edge in its own colour, in all three states', () => {
    for (const tone of ['ok', 'warn', 'danger']) {
      const declarations = rule(sheet, `.state-btn.state-set.state-${tone}`);
      expect(declarations, tone).toContain(`box-shadow: inset 0 -3px 0 var(--${tone})`);
      expect(declarations, tone).toContain(`border-color: var(--${tone})`);
      expect(classes(`.state-btn.state-set.state-${tone}`)).toBeGreaterThan(classes('.btn'));
    }
  });

  it('takes its colours from tokens only', () => {
    const colours = sheet.match(/#[0-9a-f]{3,8}|\brgba?\(/gi) ?? [];
    expect(colours).toEqual([]);
  });
});
