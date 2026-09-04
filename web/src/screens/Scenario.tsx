import { useEffect, useMemo, useState } from 'react';
import { flushSync } from 'react-dom';
import { Link, useParams, useSearchParams } from 'react-router';
import { api } from '../api/client';
import type { Playbook, Section as SectionData } from '../api/types';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Checklist } from '../components/Checklist';
import { Html } from '../components/Html';
import { Section } from '../components/Section';
import { Icon } from '../icons';
import { useKiosk } from '../kiosk/KioskProvider';

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
        if (!mod) return <p key={i} className="pad warning">Module "{part.module}" is missing from this playbook.</p>;
        return (
          <Section key={i} title={mod.title} open={open}>
            <Html html={mod.html} />
            <p className="pad no-print"><Link to={`/m/${mod.slug}`}>Open "{mod.title}" on its own</Link></p>
          </Section>
        );
      })}
    </>
  );
}

export function Scenario() {
  const { slug = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const kiosk = useKiosk();
  const { data, error, loading, setData } = useQuery(() => api.playbook(slug), [slug], { intervalMs: 15_000, refetchOnFocus: true });
  const [printing, setPrinting] = useState(false);

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

  if (error) return <div className="screen"><AppBar title="Playbook" /><p className="pad warning">Could not load this playbook: {error}</p></div>;
  if (loading || !data) return <div className="screen"><AppBar title="Playbook" /><p className="pad muted">Loading…</p></div>;

  const current = data.sections.find((s) => s.id === tab) ?? data.sections[0];
  const unreferenced = data.modules.filter((m) => !referenced.has(m.slug));
  const sections = printing ? data.sections : [current];

  const print = () => {
    flushSync(() => setPrinting(true));
    window.print();
  };

  return (
    <div className="screen playbook">
      <AppBar
        title={data.title}
        actions={
          <>
            {data.overlays.length > 0 && (
              <Link className="btn btn-chrome" to={`/map?${data.overlays.map((o) => `overlay=${encodeURIComponent(o)}`).join('&')}`}><Icon name="map" /><span>Map</span></Link>
            )}
            {!kiosk && <button type="button" className="btn btn-chrome" onClick={print}><Icon name="print" /><span>Print</span></button>}
          </>
        }
      />
      <p className="pad muted">{data.summary}</p>
      <div className="tabs" role="tablist" aria-label="Sections">
        {data.sections.map((s) => (
          <button key={s.id} type="button" role="tab" id={`tab-${s.id}`} aria-selected={s.id === current.id} aria-controls={`panel-${s.id}`} className={s.id === current.id ? 'btn active' : 'btn'} onClick={() => selectTab(s.id)}>
            {s.title}
          </button>
        ))}
      </div>
      {sections.map((s) => (
        <section key={s.id} id={`panel-${s.id}`} role="tabpanel" aria-labelledby={`tab-${s.id}`}>
          {printing && <h2 className="pad">{s.title}</h2>}
          <SectionBody section={s} playbook={data} open={printing} />
        </section>
      ))}
      {unreferenced.length > 0 && (
        <>
          <h2 className="pad">Modules</h2>
          {unreferenced.map((m) => (
            <Section key={m.slug} title={m.title} open={printing}>
              <Html html={m.html} />
              <p className="pad no-print"><Link to={`/m/${m.slug}`}>Open "{m.title}" on its own</Link></p>
            </Section>
          ))}
        </>
      )}
      <h2 className="pad">Checklist</h2>
      <Checklist slug={data.slug} items={data.checklist} onItems={(items) => setData({ ...data, checklist: items })} />
      <h2 className="pad">Sources</h2>
      <ul className="list">
        {data.sources.map((s, i) => (
          <li key={i}>
            {s.doc ? <Link to={`/doc/${s.doc}`}>{s.title}</Link> : s.kiwix ? <Link to={`/read/${s.kiwix}`}>{s.title}</Link> : <span>{s.title}</span>}
            {s.as_at && <span className="muted"> (as at {s.as_at})</span>}
          </li>
        ))}
      </ul>
      <p className="pad muted">{data.reviewed ? `Reviewed ${data.reviewed}` : 'Not yet reviewed by the owner'}</p>
    </div>
  );
}
