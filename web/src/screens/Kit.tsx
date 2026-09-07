import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '../api/client';
import type { Kit as KitData, KitItem, KitTier } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Html } from '../components/Html';
import { notify } from '../components/Notice';
import { PrintButton } from '../components/PrintButton';
import { Screen, Body } from '../shell/Screen';
import { TickedLine, UndoTick, useTickUndo } from '../situation/Tick';
import './kit.css';

function linkTitle(item: KitItem): string {
  const [scheme, rest] = (item.link ?? '').split(':', 2);
  if (!rest) return 'Open';
  const name = rest.replace(/[-_]/g, ' ').replace(/^.*\//, '');
  const kind = { module: 'module', page: 'page', card: 'card', playbook: 'guide', doc: 'document', kiwix: 'article', map: 'map' }[scheme] ?? '';
  return `${name.charAt(0).toUpperCase()}${name.slice(1)}${kind ? ` ${kind}` : ''}`;
}

function ItemRow({ slug, item, onKit }: { slug: string; item: KitItem; onKit: (kit: KitData) => void }) {
  const [busy, setBusy] = useState(false);
  const [undoing, setUndoing] = useState(false);
  const { armed, arm, disarm } = useTickUndo();
  const toggle = async () => {
    const next = !item.checked;
    setBusy(true);
    try {
      onKit(await api.setKitItem(slug, item.id, { checked: next }));
      if (next) { setUndoing(true); arm(); } else { setUndoing(false); disarm(); }
    } catch (e) {
      notify(`Could not save the tick: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };
  const id = `kit-${slug}-${item.id}`;
  return (
    <li className={item.checked ? 'task-row task-done' : 'task-row'}>
      <label className="task-tick" htmlFor={id}>
        <input type="checkbox" id={id} checked={item.checked} disabled={busy} onChange={() => void toggle()} />
        <span>
          <span className="task-title">{item.name}</span>
          {item.qty && <span className="kit-qty">{item.qty.text}</span>}
          {item.why_html && <Html className="kit-why" html={item.why_html} />}
          {item.note_html && <Html className="kit-why" html={item.note_html} />}
          {item.href && (
            <> <Link to={item.href} aria-label={`${linkTitle(item)}: ${item.name}`}>{linkTitle(item)}</Link></>
          )}
        </span>
      </label>
      {item.checked && (
        <div className="row task-meta">
          <TickedLine at={item.updated_at} />
          {armed && undoing && <UndoTick label={item.name} busy={busy} onUndo={() => void toggle()} />}
        </div>
      )}
    </li>
  );
}

function Tier({ slug, tier, open, onKit }: { slug: string; tier: KitTier; open: boolean; onKit: (kit: KitData) => void }) {
  return (
    <details className="panel kit-tier" open={open} aria-label={`${tier.title}: ${tier.done} of ${tier.total}`} role="group">
      <summary>
        <span>{tier.title}</span>
        <span className="muted">{tier.days} days · {tier.done} of {tier.total} · {tier.why}</span>
      </summary>
      <ul className="list task-list">
        {tier.items.map((item) => <ItemRow key={item.id} slug={slug} item={item} onKit={onKit} />)}
      </ul>
    </details>
  );
}

export function Kit() {
  const { slug = '' } = useParams();
  const q = useQuery(() => api.kit(slug), [slug], { refetchOnFocus: true });
  const [confirming, setConfirming] = useState(false);
  const [opened, setOpened] = useState<Record<string, boolean>>({});
  const kit = q.data;
  const reset = async () => {
    try {
      q.setData(await api.resetKit(slug));
    } catch (e) {
      notify(`Could not reset the ticks: ${errorMessage(e)}`);
    } finally {
      setConfirming(false);
    }
  };
  const basicDone = kit ? kit.tiers[0].done === kit.tiers[0].total && kit.tiers[0].total > 0 : false;
  const isOpen = (tier: KitTier) => opened[tier.id] ?? (tier.id === 'basic' || (tier.id === 'serious' && basicDone));
  return (
    <Screen title={kit?.title ?? 'Kit'} search={false} actions={<PrintButton />}>
      <Body>
        {q.loading && <p className="muted">Loading…</p>}
        {q.error && <p className="warning">Could not load this kit: {q.error}</p>}
        {kit && (
          <>
            {/* The count is a setting, not a register, and the stepper that holds it is one tap away
                on the kit list: the number is said here and changed there. */}
            <p className="muted">
              Quantities are for <Link to="/kit">{kit.people} {kit.people === 1 ? 'person' : 'people'}</Link>. Ticks are shared by everyone on the box.
            </p>
            {kit.tiers.map((tier) => (
              <div key={tier.id} onToggle={(e) => setOpened((o) => ({ ...o, [tier.id]: (e.target as HTMLDetailsElement).open }))}>
                <Tier slug={slug} tier={tier} open={isOpen(tier)} onKit={q.setData} />
              </div>
            ))}
            {/* The list is what the screen is for: the reasoning sits under it, where somebody who
                wants it will look, rather than between the title and the first thing to pack. */}
            {kit.intro_html && (
              <section aria-labelledby="kit-why">
                <h2 id="kit-why">Why these things</h2>
                <Html html={kit.intro_html} />
              </section>
            )}
            {kit.sources.length > 0 && (
              <p className="muted">Sources: {kit.sources.map((s) => s.title).join('; ')}.</p>
            )}
            {confirming ? (
              <div className="row no-print">
                <span>Clear every tick on this kit?</span>
                <button type="button" className="btn btn-danger" onClick={() => void reset()}>Yes, reset</button>
                <button type="button" className="btn" onClick={() => setConfirming(false)}>Cancel</button>
              </div>
            ) : (
              <button type="button" className="btn btn-small no-print" onClick={() => setConfirming(true)}>Reset ticks</button>
            )}
          </>
        )}
      </Body>
    </Screen>
  );
}
