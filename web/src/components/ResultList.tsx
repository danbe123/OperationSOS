import type { SearchResult } from '../api/types';
import { useAppLink } from '../links';
import { cleanBadge, cleanSnippet, cleanTitle, highlightParts } from '../api/results';
import { Badge } from './Badge';

/** The engine marks what it matched with `<b>`; the screen renders that as bold text, never as HTML
 * it was handed. Before this the tags were printed as words: "&lt;b&gt;Adders&lt;/b&gt; The
 * &lt;b&gt;adder&lt;/b&gt; is the only venomous snake…", on every snippet of every query. */
export function Snippet({ text }: { text: string }) {
  const clean = cleanSnippet(text);
  if (!clean) return null;
  return (
    <span className="result-snippet">
      {highlightParts(clean).map((part, i) => (part.match ? <b key={i}>{part.text}</b> : <span key={i}>{part.text}</span>))}
    </span>
  );
}

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
            {r.snippet && <Snippet text={r.snippet} />}
          </a>
        </li>
      ))}
    </ul>
  );
}
