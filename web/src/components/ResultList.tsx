import type { SearchResult } from '../api/types';
import { useAppLink } from '../links';
import { cleanBadge, cleanSnippet, cleanTitle, highlightParts } from '../api/results';

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

/** A result is one target: the whole row is the link, not the sixteen pixels of its title. The
 * source is a word before the title, quieter and set apart, never glued to it: "NHS Medicines A to Z
 * Kiwix build December 2025 How and when to take memantine - NHS" read as one sentence, and a pill
 * above the title on its own line made every row three lines before the snippet. */
export function ResultList({ results, label = 'Results' }: { results: SearchResult[]; label?: string }) {
  const follow = useAppLink();
  if (results.length === 0) return null;
  return (
    <ul className="list results" aria-label={label}>
      {results.map((r, i) => (
        <li key={`${r.url}#${i}`}>
          <a className="result-row" href={r.url} onClick={(e) => { if (follow(r.url)) e.preventDefault(); }}>
            <span className="result-line">
              <span className="result-source">{cleanBadge(r.badge)}</span>
              <span className="result-title">{cleanTitle(r.title)}</span>
            </span>
            {r.snippet && <Snippet text={r.snippet} />}
          </a>
        </li>
      ))}
    </ul>
  );
}
