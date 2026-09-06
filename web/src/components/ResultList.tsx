import type { SearchResult } from '../api/types';
import { useAppLink } from '../links';
import { cleanBadge, cleanTitle } from '../api/results';
import { Badge } from './Badge';

/** A result is one target: the whole row is the link, not the sixteen pixels of its underlined
 * title, and the badge rides above it on its own line — glued to the front of the title it read as
 * one long sentence ("NHS Medicines A to Z Kiwix build December 2025 How and when to take
 * memantine - NHS"), with no way to see where the answer came from. */
export function ResultList({ results, label = 'Results' }: { results: SearchResult[]; label?: string }) {
  const follow = useAppLink();
  if (results.length === 0) return null;
  return (
    <ul className="list results" aria-label={label}>
      {results.map((r, i) => (
        <li key={`${r.url}#${i}`}>
          <a className="result-row" href={r.url} onClick={(e) => { if (follow(r.url)) e.preventDefault(); }}>
            <span className="result-source"><Badge>{cleanBadge(r.badge)}</Badge></span>
            <span className="result-title">{cleanTitle(r.title)}</span>
            {r.snippet && <span className="result-snippet">{r.snippet}</span>}
          </a>
        </li>
      ))}
    </ul>
  );
}
