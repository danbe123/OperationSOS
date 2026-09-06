import type { SearchResult } from '../api/types';
import { useAppLink } from '../links';
import { sourceWord } from '../api/words';
import { Badge } from './Badge';

/** A result is one target: the whole row is the link, not the sixteen pixels of its underlined
 * title, and the badge rides inside it. */
export function ResultList({ results }: { results: SearchResult[] }) {
  const follow = useAppLink();
  if (results.length === 0) return null;
  return (
    <ul className="list results" aria-label="Results">
      {results.map((r, i) => (
        <li key={`${r.url}#${i}`}>
          <a className="result-row" href={r.url} onClick={(e) => { if (follow(r.url)) e.preventDefault(); }}>
            <span><Badge>{sourceWord(r.badge)}</Badge> <span className="result-title">{r.title}</span></span>
            {r.snippet && <span className="result-snippet">{r.snippet}</span>}
          </a>
        </li>
      ))}
    </ul>
  );
}
