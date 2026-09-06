import { useMemo, useRef } from 'react';
import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Html } from '../components/Html';
import { Screen } from '../shell/Screen';
import { useScrollCue } from '../shell/Shell';
import { Emergency999 } from '../situation/Emergency999';
import './card.css';

/** A card taken apart by its own headings: the renderer gives every card the same five sections
 * (when to use, steps, warnings, stop or escalate, source), and the screen sets each one the way
 * it is read rather than as a run of prose. `rest` is anything a card puts outside those headings. */
export type CardParts = { when: string; steps: string[]; warnings: string; escalate: string; source: string; rest: string };

const WARNING = /<strong>\s*Warning:?\s*<\/strong>\s*/i;

function sectionFor(heading: string): keyof CardParts | null {
  const h = heading.trim().toLowerCase();
  if (h.startsWith('when')) return 'when';
  if (h === 'steps') return 'steps';
  if (h.startsWith('warning')) return 'warnings';
  if (h.startsWith('stop')) return 'escalate';
  if (h === 'source' || h === 'sources') return 'source';
  return null;
}

export function splitCard(html: string): CardParts {
  const parts: CardParts = { when: '', steps: [], warnings: '', escalate: '', source: '', rest: '' };
  const root = new DOMParser().parseFromString(`<div>${html ?? ''}</div>`, 'text/html').body.firstElementChild;
  if (!root) return parts;
  let key: keyof CardParts | null = null;
  const warnings: string[] = [];
  for (const node of Array.from(root.childNodes)) {
    const el = node.nodeType === Node.ELEMENT_NODE ? (node as Element) : null;
    if (el && /^H[1-6]$/.test(el.tagName)) {
      key = sectionFor(el.textContent ?? '');
      continue;
    }
    if (key === 'steps') {
      if (el?.tagName === 'OL') parts.steps.push(...Array.from(el.children, (li) => li.innerHTML.trim()));
      continue;
    }
    if (key === 'warnings') {
      // One paragraph per warning, however the source ran them together: a warning is read on its own.
      const text = el?.tagName === 'P' ? el.innerHTML : (el?.outerHTML ?? node.textContent ?? '');
      warnings.push(...text.split(WARNING).map((w) => w.trim()).filter(Boolean));
      continue;
    }
    const outer = el ? el.outerHTML : (node.textContent ?? '');
    if (key) parts[key] += outer;
    else parts.rest += outer;
  }
  parts.warnings = warnings.map((w) => `<p class="card-warning"><strong>Warning</strong> ${w}</p>`).join('');
  return parts;
}

/** How many steps the card has, counted from the card's own HTML rather than from the screen. */
export function countSteps(html: string): number {
  return splitCard(html).steps.length;
}

/** A quick card is read at arm's length in bad light, often by someone kneeling over a body.
 * It is one sheet: one line to confirm it is the right card, then the steps, the first three set
 * big enough to read from a standing start (the content rule keeps them under 70 characters), the
 * rest at reading size, then the warnings and what to do when nobody is coming. Nothing to turn,
 * nothing to tap: the sheet scrolls, and a fade at the bottom says there is more. */
export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  const frame = useRef<HTMLDivElement>(null);
  const more = useScrollCue(frame);
  const parts = useMemo(() => splitCard(data?.html ?? ''), [data]);
  const sheet = parts.steps.length > 0;
  return (
    <Screen title={data?.title ?? 'Quick card'} search={false} fill className="card">
      <div className="card-body">
        <Emergency999 />
        {loading && <p className="muted">Loading the card…</p>}
        {error && <p className="warning">Could not load this card: {error}</p>}
        <div className={more ? 'card-scroll card-scroll-more' : 'card-scroll'} ref={frame}>
          {data && !sheet && <Html className="html card-html" html={data.html} />}
          {data && sheet && (
            <article className="card-sheet">
              {parts.when && <Html className="card-when" html={parts.when} />}
              {parts.rest && <Html className="html card-html" html={parts.rest} />}
              <ol className="card-steps" aria-label="Steps">
                {parts.steps.map((step, i) => (
                  <li key={i} className={i < 3 ? 'card-step card-step-lead' : 'card-step'}>
                    <Html html={step} />
                  </li>
                ))}
              </ol>
              {parts.warnings && <Html className="card-warnings" html={parts.warnings} />}
              {parts.escalate && (
                <section className="card-escalate" aria-label="Stop or escalate">
                  <h2>Stop or escalate</h2>
                  <Html html={parts.escalate} />
                </section>
              )}
              {parts.source && <Html className="card-source" html={parts.source} />}
            </article>
          )}
        </div>
      </div>
    </Screen>
  );
}
