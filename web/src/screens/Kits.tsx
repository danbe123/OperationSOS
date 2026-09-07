import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { Kit, KitSummary, KitTierId } from '../api/types';
import { errorMessage, useQuery } from '../api/useQuery';
import { notify } from '../components/Notice';
import { PrintButton } from '../components/PrintButton';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import './kit.css';

const TIER_LABEL: Record<KitTierId, string> = { basic: 'Basic', serious: 'Serious', full: 'Full' };
/** The range the box will hold: one person at least, and twenty is more than any household. */
const MIN_PEOPLE = 1;
const MAX_PEOPLE = 20;

/** "Basic 1/2 · Serious 0/1 · Full 0/1": the one line a tile has for progress. */
export function tierLine(tiers: KitSummary['tiers']): string {
  return (['basic', 'serious', 'full'] as KitTierId[]).map((t) => `${TIER_LABEL[t]} ${tiers[t].done}/${tiers[t].total}`).join(' · ');
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
                  <li key={i.id}>{i.checked ? '\u2611' : '\u2610'} {i.name}{i.qty ? ` — ${i.qty.text}` : ''}</li>
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
      <strong>For {people} {people === 1 ? 'person' : 'people'}</strong>
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

/** Kit: what to have in the house, in three tiers, ticked by everyone on the box. */
export function Kits() {
  const q = useQuery(() => api.kits(), [], { refetchOnFocus: true });
  const kits = q.data?.kits ?? [];
  const people = q.data?.people ?? 1;
  const { sheets, busy, printAll } = usePrintEveryKit(kits);
  // Nothing to print until the list of kits is on the screen: the button used to sit there through
  // the whole load and do nothing at all when a household tapped it.
  return (
    <Screen
      title="Kit" back={false} search={false}
      actions={<PrintButton label="Print every kit" disabled={!q.data || busy} onPrint={() => void printAll()} />}
    >
      <Body>
        <p className="muted">
          What to have before anything happens, in three tiers: three days, two weeks, and no help coming.
          Ticks are shared by everyone on the box.
        </p>
        {q.data && <PeopleStepper people={people} onSaved={q.refetch} />}
        {q.loading && <p className="muted">Loading the kits…</p>}
        {q.error && <p className="warning">Kits unavailable: {q.error}</p>}
        {kits.length > 0 && <KitTiles kits={kits} label="Kits" />}
        <PackingList sheets={sheets} />
      </Body>
    </Screen>
  );
}
