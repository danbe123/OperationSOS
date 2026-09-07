import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { api } from '../api/client';
import type { Kit, KitHave, KitSummary, KitTierId } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { Icon } from '../icons';
import { notify } from '../components/Notice';
import { PrintButton } from '../components/PrintButton';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import './kit.css';

const TIER_LABEL: Record<KitTierId, string> = { basic: 'Basic', serious: 'Serious', full: 'Full' };
/** The range the box will hold: one person at least, and twenty is more than any household. */
const MIN_PEOPLE = 1;
const MAX_PEOPLE = 20;

/** The two ways to read the same ticks: the kits as they are worked through, and the flat list of
 * what is already in the house. The tab is the URL's hash, so `/kit#have` is a link somebody can
 * send or bookmark rather than a state that only exists once the screen is tapped. */
type TabId = 'kits' | 'have';
const TABS: { id: TabId; title: string }[] = [{ id: 'kits', title: 'Kits' }, { id: 'have', title: 'What you have' }];

/** "Basic 1/2 · Serious 0/1 · Full 0/1": the one line a tile has for progress. */
export function tierLine(tiers: KitSummary['tiers']): string {
  return (['basic', 'serious', 'full'] as KitTierId[]).map((t) => `${TIER_LABEL[t]} ${tiers[t].done}/${tiers[t].total}`).join(' · ');
}

/** "For 2 people", the one number every quantity on these screens is scaled by. */
function peopleLine(people: number): string {
  return `For ${people} ${people === 1 ? 'person' : 'people'}`;
}

/** Every kit as one packing list. `beforeprint` is too late to fetch anything, so the button fetches
 * the kits first and prints once they are on the page. `busy` is what the button reads while those
 * fetches are in flight: tapping again would gather every kit a second time. */
function usePrintEveryKit(kits: KitSummary[]): { sheets: Kit[]; busy: boolean; printAll: () => Promise<void> } {
  const [sheets, setSheets] = useState<Kit[]>([]);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!sheets.length) return;
    window.print();
    setSheets([]);
  }, [sheets]);
  const printAll = async () => {
    setBusy(true);
    try {
      setSheets(await Promise.all(kits.map((k) => api.kit(k.slug))));
    } catch (e) {
      notify(`Could not gather the kits to print: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };
  return { sheets, busy, printAll };
}

function PackingList({ sheets }: { sheets: Kit[] }) {
  return (
    <div className="print-only kit-sheets">
      {sheets.map((kit) => (
        <section key={kit.slug}>
          <h2>{kit.title}</h2>
          {kit.tiers.map((tier) => (
            <div key={tier.id}>
              <h3>{tier.title} · {tier.days} days</h3>
              <ul className="list">
                {tier.items.map((i) => (
                  <li key={i.id}>{i.checked ? '☑' : '☐'} {i.name}{i.qty ? ` — ${i.qty.text}` : ''}</li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

/** The one thing the box ever asks a household: how many people the quantities are for. One tap
 * either way, saved as it is tapped, and the kits are read again so every quantity on the next
 * screen is the box's own arithmetic rather than the screen's guess at it. */
function PeopleStepper({ people, onSaved }: { people: number; onSaved: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const step = async (to: number) => {
    if (to < MIN_PEOPLE || to > MAX_PEOPLE) return;
    setBusy(true);
    try {
      await api.setPeople(to);
      await onSaved();
    } catch (e) {
      notify(`Could not save how many people: ${errorMessage(e)}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="row kit-people" role="group" aria-label="How many people">
      <button type="button" className="btn" disabled={busy || people <= MIN_PEOPLE} onClick={() => void step(people - 1)}>Fewer</button>
      <strong>{peopleLine(people)}</strong>
      <button type="button" className="btn" disabled={busy || people >= MAX_PEOPLE} onClick={() => void step(people + 1)}>More</button>
    </div>
  );
}

function KitTiles({ kits, label }: { kits: KitSummary[]; label: string }) {
  return (
    <nav className="tiles tiles-wide" aria-label={label}>
      {kits.map((k) => <Tile key={k.slug} to={`/kit/${k.slug}`} icon={k.icon} title={k.title} subtitle={k.summary} note={tierLine(k.tiers)} />)}
    </nav>
  );
}

/** One kit's ticked things, as a table: what it is and how much of it this household needs. The
 * heading is the way into the kit itself, so a row that looks wrong is one tap from being changed. */
function HaveKit({ kit }: { kit: KitHave }) {
  return (
    <section className="kit-have-kit">
      <h3><Link to={`/kit/${kit.slug}`}><Icon name={kit.icon} size={22} />{kit.title}</Link></h3>
      <table className="kit-have-table">
        <thead>
          <tr><th scope="col">Item</th><th scope="col">Quantity</th></tr>
        </thead>
        <tbody>
          {kit.items.map((i) => (
            <tr key={i.id}>
              <th scope="row">{i.name}<span className="kit-have-tier">{i.tier}</span></th>
              <td>{i.qty ? i.qty.text : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** What you have: every tick on the box in one place, kit by kit. It is its own read rather than a
 * count taken from `GET /kits`, which knows how many are ticked but not which. */
function HaveTab() {
  const q = useQuery(() => api.kitsHave(), [], { refetchOnFocus: true });
  const kits = q.data?.kits ?? [];
  const items = kits.reduce((n, k) => n + k.items.length, 0);
  return (
    <section id="panel-have" role="tabpanel" aria-labelledby="tab-have">
      <h2>What you have marked</h2>
      {q.data && <p className="muted">{peopleLine(q.data.people)}. Quantities are what this household needs, not what is in the cupboard.</p>}
      {q.loading && <p className="muted">Loading what you have…</p>}
      {q.error && <p className="warning">What you have is unavailable: {q.error}</p>}
      {q.data && kits.length === 0 && (
        <p className="muted">Nothing ticked yet. Open a kit and tick what you have. <Link to="/kit">Back to the kits</Link></p>
      )}
      {kits.map((k) => <HaveKit key={k.slug} kit={k} />)}
      {items > 0 && (
        <p className="muted kit-have-total">
          {items} {items === 1 ? 'item' : 'items'} across {kits.length} {kits.length === 1 ? 'kit' : 'kits'}
        </p>
      )}
    </section>
  );
}

/** Kit: what to have in the house, in three tiers, ticked by everyone on the box. */
export function Kits() {
  const location = useLocation();
  const navigate = useNavigate();
  const tab: TabId = location.hash === '#have' ? 'have' : 'kits';
  const q = useQuery(() => api.kits(), [], { refetchOnFocus: true });
  const kits = q.data?.kits ?? [];
  const people = q.data?.people ?? 1;
  const { sheets, busy, printAll } = usePrintEveryKit(kits);
  // Nothing to print until the list of kits is on the screen: the button used to sit there through
  // the whole load and do nothing at all when a household tapped it.
  return (
    <Screen
      title="Kit" back={false} search={false}
      actions={tab === 'have'
        ? <PrintButton label="Print" />
        : <PrintButton label="Print every kit" disabled={!q.data || busy} onPrint={() => void printAll()} />}
    >
      <Body>
        <div className="tabs no-print" role="tablist" aria-label="Kit">
          {TABS.map((t) => (
            <button
              key={t.id} type="button" role="tab" id={`tab-${t.id}`} aria-selected={t.id === tab} aria-controls={`panel-${t.id}`}
              className={t.id === tab ? 'btn active' : 'btn'} onClick={() => navigate(t.id === 'have' ? '/kit#have' : '/kit', { replace: true })}
            >
              {t.title}
            </button>
          ))}
        </div>
        {tab === 'have' ? <HaveTab /> : (
          <section id="panel-kits" role="tabpanel" aria-labelledby="tab-kits">
            <p className="muted">
              What to have before anything happens, in three tiers: three days, two weeks, and no help coming.
              Ticks are shared by everyone on the box.
            </p>
            {q.data && <PeopleStepper people={people} onSaved={q.refetch} />}
            {q.loading && <p className="muted">Loading the kits…</p>}
            {q.error && <p className="warning">Kits unavailable: {q.error}</p>}
            {kits.length > 0 && <KitTiles kits={kits} label="Kits" />}
          </section>
        )}
        <PackingList sheets={sheets} />
      </Body>
    </Screen>
  );
}
