import { describe, it, expect } from 'vitest';
import { chipsFor, cleanBadge, markTitle } from '../../src/api/results';
import type { SearchResult } from '../../src/api/types';

const row = (source: string, badge: string, title = 'x'): SearchResult => ({ source, badge, title, snippet: '', url: `/${source}/${title}`, score: 1, kind: 'article' });

describe('cleanBadge', () => {
  it('is the source in a word: the catalogue tail gone, and a "Name: what it is" title its name', () => {
    expect(cleanBadge('WikiMed: Wikipedia medical encyclopedia')).toBe('Wikipedia medicine');   // its name, then the household's word for it
    expect(cleanBadge('Prepare: UK official emergency guidance (Kiwix build, December 2025)')).toBe('Prepare');
    expect(cleanBadge('Wikipedia (100 articles, test) (Kiwix build, December 2025)')).toBe('Wikipedia');
    expect(cleanBadge('Playbook')).toBe('Guide');
    expect(cleanBadge('NHS Medicines A to Z')).toBe('NHS Medicines A to Z');
  });
});

describe('chipsFor', () => {
  it('leads with the box\'s own chip whatever the engine ranked first, then the sources in their order', () => {
    const chips = chipsFor([row('reference', 'Wikipedia'), row('playbooks', 'Page'), row('nhs', 'NHS'), row('playbooks', 'Guide'), row('nhs', 'NHS', 'y')]);
    expect(chips.map((c) => [c.title, c.count])).toEqual([['From this box', 2], ['Wikipedia', 1], ['NHS', 2]]);
  });
});

describe('markTitle', () => {
  it('marks the query\'s words in a title, loosely by stem, and nothing else', () => {
    expect(markTitle('Severe bleeding', 'bleed')).toEqual([{ text: 'Severe ', match: false }, { text: 'bleeding', match: true }]);
    expect(markTitle('Solar panels in a power cut', 'power cut')).toEqual([
      { text: 'Solar panels in a ', match: false }, { text: 'power cut', match: true },
    ]);
    expect(markTitle('Water', '')).toEqual([{ text: 'Water', match: false }]);
    expect(markTitle('Tinned food', 'tins')).toEqual([{ text: 'Tinned', match: true }, { text: ' food', match: false }]);
  });
});
