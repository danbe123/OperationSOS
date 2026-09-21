import { useContext, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { ColdStartContext, forgetPlace, readPlace, type LastPlace } from '../shell/lastPlace';
import { api } from '../api/client';
import { errorMessage } from '../api/useQuery';
import { notify } from '../components/Notice';
import { CONDITION_IDS, type ConditionId } from '../api/types';
import { CONDITION_INFO, STATE_SYMBOL, STATE_TONE, stateWord } from '../situation/conditions';
import { flipCondition } from '../situation/flip';
import { useQuery } from '../api/useQuery';
import { tileLine } from '../api/words';
import { Icon } from '../icons';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import { isEventful, useSituation } from '../situation/SituationProvider';
import './now.css';

/** Peacetime on Now: the front door asks the one question the box is for, and every answer is a
 * tile. It used to say "Start here" over a kit count, a drill button and a row of shortcuts, and
 * carry a panel about the machine itself underneath — the household's own question ("what do I do
 * about a power cut, a flood, a pandemic") was two taps away on Guides. The tiles are the question's
 * answers, so they are the front door; the kit ticks are on /kit, the drill on /situation, and how
 * a phone joins the box on /system. */
/** In the screen's head, where the search field was ("on now page, remove the search move the on off
 * icons where the search was"): the services, power, water, gas, mobile and the rest, one button each.
 * Tapping one tells the box that service is off (or working again), which is what the situation
 * engine runs on: the tasks, the forecasts and the briefing all follow from these. The full row of
 * detail (since when, a note, patchy rather than off) stays on /situation. */
function ServiceRow() {
  const { view, refresh } = useSituation();
  const [busy, setBusy] = useState<ConditionId | null>(null);
  if (!view) return null;
  const flip = async (id: ConditionId) => {
    setBusy(id);
    try {
      await flipCondition(id, view.conditions[id]);
      await refresh();
    } catch (e) {
      notify(`Could not change ${CONDITION_INFO[id].title}: ${errorMessage(e)}`);
    } finally {
      setBusy(null);
    }
  };
  return (
    <nav className="service-row" aria-label="Services">
        {CONDITION_IDS.map((id) => {
          const c = view.conditions[id];
          const off = c.state !== 'working';
          const info = CONDITION_INFO[id];
          const word = stateWord(id, c.state);
          const back = id === 'roads' || id === 'shops' ? 'open' : 'working';
          return (
            <button
              key={id} type="button" className={`btn service-btn service-${STATE_TONE[c.state]}`}
              aria-pressed={off} aria-label={`${info.title}: ${word}`}
              title={off ? `${info.title} is ${word}. Tap when it is ${back} again.` : `${info.title} is ${word}. Tap if it has gone ${id === 'roads' || id === 'shops' ? 'closed' : 'off'}.`}
              disabled={busy === id} onClick={() => void flip(id)}
            >
              <Icon name={info.icon} size={24} />
              <span className="service-name">{info.short}</span>
              <span className="service-mark" aria-hidden="true">{STATE_SYMBOL[c.state]}</span>
            </button>
          );
        })}
    </nav>
  );
}

/** Tapping a service says that service is off, and nothing else: the front door does not change
 * shape under the finger that tapped it. What the box makes of it — the jobs, the forecast, the
 * guesses — is one line and one tap away, on the sheet that holds it. */
function WhatToDo() {
  const { view } = useSituation();
  if (!view || !isEventful(view)) return null;
  const broken = CONDITION_IDS.map((id) => view.conditions[id]).filter((c) => c && c.state !== 'working');
  return (
    <p className="now-what-to-do">
      {broken.length > 0 && `${broken.length} ${broken.length === 1 ? 'service' : 'services'} off. `}
      <Link to="/situation">What to do now</Link>
    </p>
  );
}

function Situations() {
  const playbooks = useQuery(() => api.playbooks(), []);
  const scenarios = useMemo(
    () => (playbooks.data ?? []).slice().sort((a, b) => a.order - b.order),
    [playbooks.data],
  );
  return (
    <>
      {playbooks.loading && !playbooks.data && <p className="muted">Reading…</p>}
      {playbooks.error && (
        <p className="panel panel-warn row" role="status">
          <span className="warning">The box cannot read the guides: {playbooks.error}</span>
          <button type="button" className="btn btn-small" onClick={() => void playbooks.refetch()}><Icon name="refresh" size={18} /><span>Try again</span></button>
        </p>
      )}
      {/* First aid opens the grid, and is there as soon as the guides have been asked for, whether or not they
          could be read: the quick medical cards are the one thing here that must not wait on anything. It is
          what keeps a quick card at two taps from Now, now that Medical lives in the Library. */}
      {(scenarios.length > 0 || !playbooks.loading) && (
        <nav className="tiles" aria-label="Scenarios">
          <Tile to="/library/medical" icon="medical" title="First aid" subtitle="Quick cards" />
          {scenarios.map((p) => (
            <Tile key={p.slug} to={`/s/${p.slug}`} icon={p.icon} title={p.title} subtitle={tileLine(p.title, p.summary)} />
          ))}
        </nav>
      )}
      <WhatToDo />
    </>
  );
}

/** After the kiosk browser or the box restarts, one calm way back to the screen somebody was on: only on a
 * cold start (never after moving about the app), only when it was under twelve hours ago, dismissible, and
 * never a redirect. Dismissing forgets the place. */
function ContinueChip() {
  const cold = useContext(ColdStartContext);
  const [offer, setOffer] = useState<LastPlace | null>(() => (cold.current ? readPlace() : null));
  if (!offer) return null;
  return (
    <nav className="chips now-continue" aria-label="Continue">
      <Link className="chip" to={offer.path}>
        <Icon name="back" size={18} />
        <span>Continue where you were{offer.title ? `: ${offer.title}` : ''}</span>
      </Link>
      <button type="button" className="chip" aria-label="Dismiss: continue where you were" onClick={() => { forgetPlace(); setOffer(null); }}>
        <Icon name="close" size={18} />
      </button>
    </nav>
  );
}

/** Now is the front door, and it is the same door whatever is happening: the question, the
 * situations, and the services. It used to turn into the briefing the moment anything was off, so
 * a household that tapped Power to say the power was off was taken to a screen of forecasts and
 * jobs it had not asked for, with the button it had just pressed nowhere in sight. */
export function Now() {
  const { view, error, loading, refresh } = useSituation();
  return (
    <Screen title="What's the situation?" back={false} search={false} actions={<ServiceRow />}>
      <Body>
        <ContinueChip />
        {/* With both networks down this is the most important new fact on the front door, and the
            box used to say nothing about it here at all. One component, one sentence. */}
        <Emergency999 onlyWhenHidden />
        {error && (
          <p className="panel panel-warn row" role="status">
            <span className="warning">The box cannot read the situation.</span>
            <span className="muted">The guides and the map still work.</span>
            <button type="button" className="btn btn-small" onClick={() => void refresh()}><Icon name="refresh" size={18} /><span>Try again</span></button>
          </p>
        )}
        {loading && !view && <p className="muted">Reading the situation…</p>}
        {/* Nothing at all until the engine has answered: painting the question over a situation that
            is still being read is the front door telling a household the wrong thing first. With the
            engine down the tiles are the whole answer, so they come up anyway. */}
        {(view || !loading) && <Situations />}
      </Body>
    </Screen>
  );
}
