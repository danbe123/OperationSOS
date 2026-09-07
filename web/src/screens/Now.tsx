import { useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { useQuery } from '../api/useQuery';
import { tileLine } from '../api/words';
import { Icon } from '../icons';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import { Briefing } from '../situation/Briefing';
import { Emergency999 } from '../situation/Emergency999';
import { nowTitle } from '../situation/nowTitle';
import { scenarioMapHref } from '../situation/mapLink';
import { isEventful, useSituation } from '../situation/SituationProvider';
import { situationLine } from '../components/SituationClock';
import { ReadAloud } from '../situation/ReadAloud';
import './now.css';

/** Peacetime on Now: the front door asks the one question the box is for, and every answer is a
 * tile. It used to say "Start here" over a kit count, a drill button and a row of shortcuts, and
 * carry a panel about the machine itself underneath — the household's own question ("what do I do
 * about a power cut, a flood, a pandemic") was two taps away on Guides. The tiles are the question's
 * answers, so they are the front door; the kit ticks are on /kit, the drill on /situation, and how
 * a phone joins the box on /system. */
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
      {scenarios.length > 0 && (
        <nav className="tiles" aria-label="Scenarios">
          {scenarios.map((p) => (
            <Tile key={p.slug} to={`/s/${p.slug}`} icon={p.icon} title={p.title} subtitle={tileLine(p.title, p.summary)} />
          ))}
        </nav>
      )}
    </>
  );
}

/** A situation that is running, or the guide last opened on this device: the way straight back in.
 * The band already names a scenario the engine knows about, so this only fills the gaps it leaves. */
function CarryOn() {
  const { status } = useStatus();
  const { view } = useSituation();
  const playbooks = useQuery(() => api.playbooks(), []);
  const [lastSlug] = useState(() => {
    try { return localStorage.getItem('sos.lastPlaybook'); } catch { return null; }
  });
  const titleOf = (slug: string) => (playbooks.data ?? []).find((p) => p.slug === slug)?.title ?? slug;
  const running = !view?.scenario && status?.situation ? status.situation : null;
  const last = lastSlug && lastSlug !== running?.slug && lastSlug !== view?.scenario?.slug ? lastSlug : null;
  if (!running && !last) return null;
  return (
    <section className="panel panel-warn now-carry" aria-label="Carry on">
      {running && (
        <Link className="now-resume" to={`/s/${running.slug}`}>
          <Icon name="alert" size={20} />
          <span>
            <small>Active situation, {situationLine({ ...running, title: null, elapsed_s: 0, phase: 'right-now' })}</small>
            <strong>{titleOf(running.slug)}</strong>
          </span>
          <Icon name="forward" size={20} />
        </Link>
      )}
      {last && (
        <Link className="now-resume" to={`/s/${last}`}>
          <Icon name="book" size={20} />
          <span><small>Recently opened on this device</small><strong>Continue: {titleOf(last)}</strong></span>
          <Icon name="forward" size={20} />
        </Link>
      )}
    </section>
  );
}

/** Now is the front door. It answers "what do I do" from the engine, or asks the household what the
 * situation is and lets them pick it off the wall. */
export function Now() {
  const { view, error, loading, refresh } = useSituation();
  const eventful = isEventful(view);
  const mapHref = scenarioMapHref(view?.scenario?.slug);
  // What is read aloud is the briefing itself; the button that reads it belongs in the screen's own
  // actions, beside Search, not on a row of its own above the first job.
  const briefing = useRef<HTMLDivElement>(null);
  // The heading is the answer while something is happening, and the question the rest of the time.
  return (
    <Screen
      title={eventful ? nowTitle(view) : "What's the situation?"}
      back={false}
      actions={eventful ? <ReadAloud id="briefing" target={briefing} label="Read aloud" /> : undefined}
    >
      <Body>
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
        {view?.modes.map_first && (
          <p><Link className="btn btn-primary btn-big" to={mapHref}><Icon name="map" /><span>Open the map</span></Link></p>
        )}
        <CarryOn />
        {/* Nothing at all until the engine has answered: painting the question over a situation that
            is still being read is the front door telling a household the wrong thing first. With the
            engine down the tiles are the whole answer, so they come up anyway. */}
        {eventful ? <Briefing blockRef={briefing} /> : (view || !loading) && <Situations />}
      </Body>
    </Screen>
  );
}
