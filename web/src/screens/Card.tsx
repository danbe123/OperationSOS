import { useLayoutEffect, useRef, useState } from 'react';
import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { Screen } from '../shell/Screen';
import { useScrollCue } from '../shell/Shell';
import { Emergency999 } from '../situation/Emergency999';
import { Html } from '../components/Html';

/** Above this many characters a step is a sentence rather than an instruction, and the display size
 * turns it into four lines that push the next step off a 480 px screen. Short steps keep the size
 * they are read at across a room; long ones drop to the lead size and stay on the screen. */
export const LONG_STEP = 40;

/** A quick card is read at arm's length by someone kneeling over a body. The call comes first, then
 * the first compression: nothing else is on the screen, the steps scroll inside their own frame,
 * and the screen says how many there are and that there are more below. */
export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  const steps = useRef<HTMLDivElement>(null);
  const [count, setCount] = useState(0);
  const more = useScrollCue(steps);

  useLayoutEffect(() => {
    const items = steps.current?.querySelectorAll<HTMLLIElement>('.card-html ol > li') ?? [];
    setCount(items.length);
    items.forEach((li) => li.classList.toggle('card-step-long', (li.textContent ?? '').trim().length > LONG_STEP));
  }, [data]);

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
        {count > 0 && (
          <p className="card-count" role="status">
            <span>{count} {count === 1 ? 'step' : 'steps'}</span>
            {more && (
              <button type="button" className="btn btn-small card-more" onClick={down}>
                <Icon name="down" size={18} /><span>More below</span>
              </button>
            )}
          </p>
        )}
        <div className={more ? 'card-scroll card-scroll-more' : 'card-scroll'} ref={steps}>
          {data && <Html className="card-html" html={data.html} />}
        </div>
      </div>
    </Screen>
  );
}
