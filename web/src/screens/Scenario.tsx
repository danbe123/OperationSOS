import { useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import { Link, useParams, useSearchParams } from 'react-router';
import { api } from '../api/client';
import type { Playbook, Section as SectionData, Situation } from '../api/types';
import { useQuery } from '../api/useQuery';
import { Checklist } from '../components/Checklist';
import { Html } from '../components/Html';
import { PrintButton } from '../components/PrintButton';
import { Section } from '../components/Section';
import { SituationClock } from '../components/SituationClock';
import { Icon } from '../icons';
import { Screen } from '../shell/Screen';
import { withTask } from '../situation/apply';
import { Emergency999 } from '../situation/Emergency999';
import { ReadAloudBlock } from '../situation/ReadAloud';
import { useSituation } from '../situation/SituationProvider';
import { TaskRow } from '../situation/TaskRow';
import { elapsedSince, phaseFor } from '../tools/situation';
import './scenario.css';

const MODULE_MARK = /(?:<p>\s*)?(?:<div[^>]*data-module="([\w-]+)"[^>]*>\s*<\/div>|\{\{module:([\w-]+)\}\})(?:\s*<\/p>)?/g;

/** Split section HTML at module markers so each included module renders as an accordion in place. */
export function splitModules(html: string): (string | { module: string })[] {
  const out: (string | { module: string })[] = [];
  let last = 0;
  for (const m of html.matchAll(MODULE_MARK)) {
    const index = m.index ?? 0;
    if (index > last) out.push(html.slice(last, index));
    out.push({ module: m[1] ?? m[2] });
    last = index + m[0].length;
  }
  if (last < html.length) out.push(html.slice(last));
  return out;
}

function SectionBody({ section, playbook, open }: { section: SectionData; playbook: Playbook; open: boolean }) {
  return (
    <>
      {splitModules(section.html).map((part, i) => {
        if (typeof part === 'string') return <Html key={i} html={part} />;
        const mod = playbook.modules.find((m) => m.slug === part.module);
        if (!mod) return <p key={i} className="warning">The “{part.module}” module is missing from this guide.</p>;
        return (
          <Section key={i} title={mod.title} open={open}>
            <Html html={mod.html} />
            <p className="no-print"><Link to={`/m/${mod.slug}`}>Open “{mod.title}” on its own</Link></p>
          </Section>
        );
      })}
    </>
  );
}

/** The scenario's jobs: the box's own task list when this scenario is the one that is running, and
 * the guide's shared checklist otherwise. Both tick the same rows on the box. */
function ScenarioTasks({ playbook, onItems }: { playbook: Playbook; onItems: (items: Playbook['checklist']) => void }) {
  const { view, apply } = useSituation();
  const live = (view?.tasks ?? []).filter((t) => t.source === `checklist:${playbook.slug}`);
  const total = live.length > 0 ? live.length : playbook.checklist.length;
  const done = live.length > 0 ? live.filter((t) => t.done).length : playbook.checklist.filter((i) => i.checked).length;
  return (
    <aside className="panel scenario-tasks" id="response-checklist" aria-labelledby="checklist-heading">
      <div className="panel-head">
        <h2 id="checklist-heading">Things to do for this guide</h2>
        {/* The shared checklist says "n of m done, last change …" for itself; only the engine's own
            list needs the count spelled out here. */}
        {live.length > 0 && <span className="badge">{done} of {total} done</span>}
      </div>
      <progress className="progress-line" aria-label="Checklist completion" value={done} max={Math.max(1, total)} />
      <p className="muted">Shared with everyone on this box.</p>
      {live.length > 0 ? (
        <ul className="list task-list">
          {live.map((t) => <TaskRow key={t.id} task={t} onChanged={(saved) => view && apply(withTask(view, saved))} />)}
        </ul>
      ) : (
        <Checklist slug={playbook.slug} items={playbook.checklist} onItems={onItems} />
      )}
    </aside>
  );
}

export function Scenario() {
  const { slug = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const { data, error, loading, setData } = useQuery(() => api.playbook(slug), [slug], { intervalMs: 15_000, refetchOnFocus: true });
  const [printing, setPrinting] = useState(false);
  const situationQ = useQuery<Situation>(() => api.situation(), [slug], { intervalMs: 30_000, refetchOnFocus: true });
  const situation = situationQ.data ?? null;
  const nowPhase = situation && situation.slug === slug ? phaseFor(elapsedSince(situation.started_at)).id : null;
  useEffect(() => {
    if (!data) return;
    try { localStorage.setItem('sos.lastPlaybook', data.slug); } catch { /* Storage is optional. */ }
  }, [data]);

  const tab = params.get('tab') ?? 'right-now';
  const selectTab = (id: string) => {
    const p = new URLSearchParams(params);
    if (id === 'right-now') p.delete('tab');
    else p.set('tab', id);
    setParams(p, { replace: true });
  };

  useEffect(() => {
    const before = () => flushSync(() => setPrinting(true));
    const after = () => setPrinting(false);
    window.addEventListener('beforeprint', before);
    window.addEventListener('afterprint', after);
    return () => {
      window.removeEventListener('beforeprint', before);
      window.removeEventListener('afterprint', after);
    };
  }, []);

  const referenced = useMemo(() => {
    const set = new Set<string>();
    data?.sections.forEach((s) => splitModules(s.html).forEach((p) => { if (typeof p !== 'string') set.add(p.module); }));
    return set;
  }, [data]);

  if (error) return <Screen title="Guide" search={false}><div className="screen-body"><p className="warning">Could not load this guide: {error}</p></div></Screen>;
  if (loading || !data) return <Screen title="Guide" search={false}><div className="screen-body"><p className="muted">Loading…</p></div></Screen>;

  const current = data.sections.find((s) => s.id === tab) ?? data.sections[0];
  const unreferenced = data.modules.filter((m) => !referenced.has(m.slug));
  const sections = printing ? data.sections : [current];

  const print = () => {
    flushSync(() => setPrinting(true));
    window.print();
  };

  return (
    <Screen
      title={data.title}
      search={false}
      className="playbook"
      actions={
        <>
          {!printing && <SituationClock slug={data.slug} situation={situation} onChange={situationQ.setData} />}
          {data.overlays.length > 0 && (
            <Link className="btn btn-small" to={`/map?${data.overlays.map((o) => `overlay=${encodeURIComponent(o)}`).join('&')}`}><Icon name="map" size={18} /><span>Map</span></Link>
          )}
          <PrintButton onPrint={print} />
        </>
      }
    >
      <div className="screen-body">
        <Emergency999 onlyWhenHidden />
        <p className="muted measure">{data.summary}</p>
        <div className="tabs" role="tablist" aria-label="Sections">
          {data.sections.map((s) => (
            <button key={s.id} type="button" role="tab" id={`tab-${s.id}`} aria-selected={s.id === current.id} aria-controls={`panel-${s.id}`} aria-current={s.id === nowPhase ? 'time' : undefined} className={s.id === current.id ? 'btn active' : 'btn'} onClick={() => selectTab(s.id)}>
              {s.title}{s.id === nowPhase && <span className="badge badge-warn tab-now">now</span>}
            </button>
          ))}
        </div>
        <div className="scenario-workspace">
          <div className="scenario-guidance">
            {sections.map((s) => (
              <section className="scenario-panel" key={s.id} id={`panel-${s.id}`} role="tabpanel" aria-labelledby={`tab-${s.id}`}>
                <h2>{s.id === 'right-now' ? 'Do this first' : s.title}</h2>
                <ReadAloudBlock id={`section:${data.slug}#${s.id}`} label="Read this section aloud">
                  <SectionBody section={s} playbook={data} open={printing} />
                </ReadAloudBlock>
              </section>
            ))}
            {unreferenced.length > 0 && (
              <section aria-label="More modules">
                <h2>More modules</h2>
                {unreferenced.map((m) => (
                  <Section key={m.slug} title={m.title} open={printing}>
                    <Html html={m.html} />
                    <p className="no-print"><Link to={`/m/${m.slug}`}>Open “{m.title}” on its own</Link></p>
                  </Section>
                ))}
              </section>
            )}
          </div>
          <ScenarioTasks playbook={data} onItems={(items) => setData({ ...data, checklist: items })} />
          {/* Where there is one column the jobs come before the paperwork; where there are two the
              sources sit under the guidance they belong to. */}
          <footer className="scenario-sources">
            <h2>Sources</h2>
            <ul className="list">
              {data.sources.map((s, i) => (
                <li key={i}>
                  {s.doc ? <Link to={`/doc/${s.doc}`}>{s.title}</Link> : s.kiwix ? <Link to={`/read/${s.kiwix}`}>{s.title}</Link> : <span>{s.title}</span>}
                  {s.as_at && <span className="muted"> (as at {s.as_at})</span>}
                </li>
              ))}
            </ul>
            <p className="muted">{data.reviewed ? `Reviewed ${data.reviewed}` : 'Not yet reviewed by the owner'}</p>
          </footer>
        </div>
      </div>
    </Screen>
  );
}
