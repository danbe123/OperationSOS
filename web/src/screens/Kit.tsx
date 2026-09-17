import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '../api/client';
import type { Kit as KitData, KitItem, KitTier, KitTierId } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Html } from '../components/Html';
import { Icon } from '../icons';
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

/** One thing to have: the tick, the name with its quantity beside it, the reason under, and the
 * guide it comes from as a small button at the foot. The whole of the name and the reason is the
 * tick's label, so a finger lands anywhere on the row. */
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
    <li className={item.checked ? 'kit-item kit-item-done' : 'kit-item'}>
      <label className="kit-item-tick" htmlFor={id}>
        <input type="checkbox" id={id} checked={item.checked} disabled={busy} onChange={() => void toggle()} />
        <span className="kit-item-body">
          <span className="kit-item-head">
            <span className="task-title">{item.name}</span>
            {item.qty && <span className="kit-qty">{item.qty.text}</span>}
          </span>
          {item.why_html && <Html className="kit-why" html={item.why_html} />}
          {item.note_html && <Html className="kit-why" html={item.note_html} />}
        </span>
      </label>
      {(item.href || item.checked) && (
        <div className="row kit-item-foot">
          {item.href && (
            <Link className="btn btn-small btn-quiet" to={item.href} aria-label={`${linkTitle(item)}: ${item.name}`}><Icon name="book" size={18} /><span>{linkTitle(item)}</span></Link>
          )}
          {item.checked && <TickedLine at={item.updated_at} />}
          {item.checked && armed && undoing && <UndoTick label={item.name} busy={busy} onUndo={() => void toggle()} />}
        </div>
      )}
    </li>
  );
}

/** The three tiers as one switch: each says how far it is, and the one being worked on is open. Every
 * tier is on the page for the printer (a tier that is not open is hidden, not gone). */
function TierSwitch({ tiers, current, onPick }: { tiers: KitTier[]; current: KitTierId; onPick: (id: KitTierId) => void }) {
  return (
    <div className="kit-tier-switch no-print" role="tablist" aria-label="Tiers">
      {tiers.map((tier) => (
        <button
          key={tier.id} type="button" role="tab" id={`tier-tab-${tier.id}`} aria-selected={tier.id === current} aria-controls={`tier-${tier.id}`}
          className={tier.id === current ? 'kit-tier-tab active' : 'kit-tier-tab'} onClick={() => onPick(tier.id)}
        >
          <span className="kit-tier-tab-title">{tier.title}</span>
          <span className="kit-tier-tab-count">{tier.done === tier.total && tier.total > 0 ? 'Packed ✓' : `${tier.done} of ${tier.total}`}</span>
          <progress className="progress-line" value={tier.done} max={Math.max(1, tier.total)} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}

function TierPanel({ slug, tier, open, onKit }: { slug: string; tier: KitTier; open: boolean; onKit: (kit: KitData) => void }) {
  return (
    <section id={`tier-${tier.id}`} role="tabpanel" aria-labelledby={`tier-tab-${tier.id}`} className="kit-tier-panel" hidden={!open}>
      <p className="kit-tier-why"><strong>{tier.title}</strong> · {tier.days} days. {tier.why}</p>
      <ul className="list kit-items">
        {tier.items.map((item) => <ItemRow key={item.id} slug={slug} item={item} onKit={onKit} />)}
      </ul>
    </section>
  );
}

export function Kit() {
  const { slug = '' } = useParams();
  const q = useQuery(() => api.kit(slug), [slug], { refetchOnFocus: true });
  const [confirming, setConfirming] = useState(false);
  const [picked, setPicked] = useState<KitTierId | null>(null);
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
  // The tier being worked on opens: the first that is not packed, or the first if all are.
  const working = kit ? (kit.tiers.find((t) => t.done < t.total)?.id ?? kit.tiers[0]?.id ?? 'basic') : 'basic';
  const current = picked ?? working;
  const packed = kit ? kit.tiers.reduce((n, t) => n + t.done, 0) : 0;
  const total = kit ? kit.tiers.reduce((n, t) => n + t.total, 0) : 0;
  return (
    <Screen title={kit?.title ?? 'Kit'} search={false} backTo="/kit" actions={<PrintButton />}>
      <Body>
        {q.loading && <p className="muted">Loading…</p>}
        {q.error && <p className="warning">Could not load this kit: {q.error}</p>}
        {kit && (
          <>
            {/* The count is a setting, not a register, and the stepper that holds it is one tap away
                on the kit list: the number is said here and changed there. */}
            <p className="muted kit-page-line">
              <span>{packed} of {total} packed.</span>{' '}
              <span>Quantities are for <Link to="/kit">{kit.people} {kit.people === 1 ? 'person' : 'people'}</Link>. Ticks are shared by everyone on the box.</span>
            </p>
            <TierSwitch tiers={kit.tiers} current={current} onPick={setPicked} />
            {kit.tiers.map((tier) => <TierPanel key={tier.id} slug={slug} tier={tier} open={tier.id === current} onKit={q.setData} />)}
            {/* The list is what the screen is for: the reasoning sits under it, where somebody who
                wants it will look, rather than between the title and the first thing to pack. */}
            {kit.intro_html && (
              <section aria-labelledby="kit-why" className="kit-intro">
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
