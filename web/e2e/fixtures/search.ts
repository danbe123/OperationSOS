import type { SearchResponse } from '../../src/api/types';
import { search } from '../../tests/fixtures/api';

/** A question in the household's own words, not the library's: the engine finds nothing for "the
 * water stops" by its words in the box's guides, and what it does find it finds by what the question
 * means. Those rows come back marked `via: "meaning"` (the screen says "related"), and the books
 * group is the Gutenberg catalogue's own source. */
export const MEANING_QUERY = 'the water stops';

export const meaningSearch: SearchResponse = {
  q: MEANING_QUERY, query: MEANING_QUERY,
  results: [
    { source: 'playbooks', badge: 'Page', title: 'Water disinfection', snippet: 'Boil the <b>water</b> for one minute, or add the tablets and wait.', url: '/p/water-disinfection#dosing', score: 0.4, kind: 'page' },
    { source: 'playbooks', badge: 'Page', title: 'Finding water', snippet: 'When the mains has gone, where it still is, and how to make it safe to drink.', url: '/p/finding-water', score: 0.3, kind: 'page', via: 'meaning' },
    { source: 'wikipedia', badge: 'Wikipedia (100 articles, test) (Kiwix build, December 2025)', title: 'Water', snippet: '<b>Water</b> is an inorganic compound.', url: '/read/wikipedia_en_100_mini_2026-01/A/Water', score: 0.2, kind: 'article' },
    { source: 'books', badge: 'Books', title: 'The Water-Babies', snippet: 'Charles Kingsley', url: '/book/gutenberg/2', score: 0.18, kind: 'book' },
    { source: 'books', badge: 'Books', title: 'Robinson Crusoe', snippet: 'Daniel Defoe', url: '/book/gutenberg/3', score: 0.16, kind: 'book', via: 'meaning' },
  ],
  groups: [
    { source: 'playbooks', badge: 'Playbooks', count: 2 }, { source: 'wikipedia', badge: 'Wikipedia', count: 1 }, { source: 'books', badge: 'Books', count: 2 },
  ],
  took_ms: 90, partial: false,
};

/** What `GET /api/search` answers: the one canned water search, or the meaning search for its own
 * question, narrowed to the sources a filter chip asked for, as the engine narrows them. */
export function searchFor(q: string, sources: string[]): SearchResponse {
  const base = q.trim().toLowerCase() === MEANING_QUERY ? meaningSearch : { ...search, q, query: q };
  if (sources.length === 0) return { ...base, q, query: q };
  const results = base.results.filter((r) => sources.includes(r.source));
  return { ...base, q, query: q, results, groups: base.groups.filter((g) => sources.includes(g.source)) };
}
