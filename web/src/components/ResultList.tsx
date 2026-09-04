import type { SearchResult } from '../api/types';
import { useAppLink } from '../links';
import { Badge } from './Badge';

export function ResultList({ results }: { results: SearchResult[] }) {
  const follow = useAppLink();
  if (results.length === 0) return null;
  return (
    <ul className="list results" aria-label="Results">
      {results.map((r, i) => (
        <li key={`${r.url}#${i}`}>
          <a className="result-title" href={r.url} onClick={(e) => { if (follow(r.url)) e.preventDefault(); }}>
            <Badge>{r.badge}</Badge> {r.title}
          </a>
          {r.snippet && <div className="result-snippet">{r.snippet}</div>}
        </li>
      ))}
    </ul>
  );
}
