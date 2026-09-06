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
  const relevant = kits.filter((k) => k.relevant);
  const rest = kits.filter((k) => !k.relevant);
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
          Quantities are for {people} {people === 1 ? 'person' : 'people'} on the household register. Ticks are shared by everyone on the box.
        </p>
        {q.loading && <p className="muted">Loading the kits…</p>}
        {q.error && <p className="warning">Kits unavailable: {q.error}</p>}
        {relevant.length > 0 && (
          <section aria-label="Kits for this household">
            <KitTiles kits={relevant} label="Kits" />
          </section>
        )}
        {rest.length > 0 && (
          <section aria-label="Kits not needed">
            <h2>Not needed for this household</h2>
            <p className="muted">These appear when someone on the register needs them. They open all the same.</p>
            <KitTiles kits={rest} label="Not needed for this household" />
          </section>
        )}
        <PackingList sheets={sheets} />
      </Body>
    </Screen>
  );
}
