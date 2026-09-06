import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { Screen } from '../shell/Screen';
import { useScrollCue } from '../shell/Shell';
import { Emergency999 } from '../situation/Emergency999';
import { useCallsHidden } from '../situation/SituationProvider';
import { Html } from '../components/Html';

/** How many steps the card has, counted from the card's own HTML rather than from the screen. */
export function countSteps(html: string): number {
  const list = /<ol[^>]*>([\s\S]*?)<\/ol>/i.exec(html ?? '');
  return list ? (list[1].match(/<li[\s>]/gi) ?? []).length : 0;
}

/** Above this many characters a step is a sentence rather than an instruction, and the display size
 * turns it into four lines that push the next step off a 480 px screen. Short steps keep the size
 * they are read at across a room; long ones drop to the lead size and stay on the screen. */
export const LONG_STEP = 45;

/** A quick card is read at arm's length by someone kneeling over a body. The call comes first, then
 * the first compression: nothing else is on the screen, the steps scroll inside their own frame,
 * and the screen says how many there are and that there are more below. */
export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  const steps = useRef<HTMLDivElement>(null);
  // 0 the display size, 1 the lead size, 2 the body size — the floor.
  const [tight, setTight] = useState(0);
  const more = useScrollCue(steps);
  // The card's own HTML changes under the screen when the situation does: a card asked for with both
  // networks down is a different card, with a different step 2.
  const callsHidden = useCallsHidden();
  const count = useMemo(() => countSteps(data?.html ?? ''), [data]);

  useLayoutEffect(() => {
    const frame = steps.current;
    if (!frame) return;
    const items = [...frame.querySelectorAll<HTMLLIElement>('.card-html ol > li')];
    items.forEach((li) => li.classList.toggle('card-step-long', (li.textContent ?? '').trim().length > LONG_STEP));
    // The first three steps are what the card is for: with both networks down step 2 becomes a
    // sentence about who to send, and at the display size that pushed the compression rate under the
    // bottom edge of a 390 px phone. The card gives up a size at a time until the third step is on
    // the first screen, and never goes below the body size.
    const third = items[Math.min(2, items.length - 1)];
    if (!third) return;
    if (third.offsetTop + third.offsetHeight > frame.clientHeight) setTight((t) => Math.min(2, t + 1));
  }, [data, callsHidden, more, tight]);
  // A different card starts at the size a card is meant to be read at.
  useEffect(() => setTight(0), [data]);

  const down = () => {
    const el = steps.current;
    if (el) el.scrollBy({ top: Math.round(el.clientHeight * 0.8), behavior: 'smooth' });
  };

  return (
    <Screen title={data?.title ?? 'Quick card'} search={false} fill className="card">
      <div className="card-body">
        {/* One 999 line, and on this screen it is one line: the same panel at full height cost a
            480 px card 90 of them, and the card's own steps say what to do about the phones. */}
        <Emergency999 compact />
        {loading && <p className="muted">Loading the card…</p>}
        {error && <p className="warning">Could not load this card: {error}</p>}
        {/* The count is not a live region: how many steps a card has is a fact about the card, and
            announcing it again every time the frame scrolls is noise over somebody's shoulder. */}
        {count > 0 && (
          <p className="card-count">
            <span>{count} {count === 1 ? 'step' : 'steps'}</span>
            {more && (
              <button type="button" className="btn btn-small card-more" onClick={down}>
                <Icon name="down" size={18} /><span>More below</span>
              </button>
            )}
          </p>
        )}
        <div className={['card-scroll', more ? 'card-scroll-more' : '', ['', 'card-steps-tight', 'card-steps-tighter'][tight]].filter(Boolean).join(' ')} ref={steps}>
          {data && <Html className="card-html" html={data.html} />}
        </div>
      </div>
    </Screen>
  );
}
