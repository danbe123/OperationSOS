import { describe, it, expect } from 'vitest';
import { chipsFor, cleanBadge, cleanSnippet, markTitle, sectionOf } from '../../src/api/results';
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
  it('puts the chips in the order the engine first ranks each source, the box\'s own one chip among them', () => {
    const chips = chipsFor([row('reference', 'Wikipedia'), row('playbooks', 'Page'), row('nhs', 'NHS'), row('playbooks', 'Guide'), row('nhs', 'NHS', 'y')]);
    expect(chips.map((c) => [c.title, c.count])).toEqual([['Wikipedia', 1], ['From this box', 2], ['NHS', 2]]);
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

describe('sectionOf and the snippet heading', () => {
  it('names the section of one of the box\'s own passages from its anchor, and nothing for a page or an article', () => {
    expect(sectionOf('/m/water#what-to-do')).toBe('What to do');
    expect(sectionOf('/medical/card/shock#stop-or-escalate')).toBe('Stop or escalate');
    expect(sectionOf('/m/power#uk-specifics')).toBe('UK specifics');
    expect(sectionOf('/doc/nrr#page=3')).toBe('');
    expect(sectionOf('/read/wikipedia_en_all_maxi/Power_cut')).toBe('');
  });
  it('strips the heading the snippet opens with, and only that', () => {
    expect(cleanSnippet('Key facts - <b>Heat</b> one room to at least 18 °C in the day', 'Key facts')).toBe('<b>Heat</b> one room to at least 18 °C in the day');
    expect(cleanSnippet('What to do 1. Fill every clean container while the mains still run', 'What to do')).toBe('1. Fill every clean container while the mains still run');
    expect(cleanSnippet('…<b>Treat</b> every line as live even in a <b>power cut</b>', 'Fallen power lines')).toBe('…<b>Treat</b> every line as live even in a <b>power cut</b>');
  });
});
