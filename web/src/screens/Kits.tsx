import { api } from '../api/client';
import type { KitSummary, KitTierId } from '../api/types';
import { useQuery } from '../api/useQuery';
import { PrintButton } from '../components/PrintButton';
import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';
import './kit.css';

const TIER_LABEL: Record<KitTierId, string> = { basic: 'Basic', serious: 'Serious', full: 'Full' };

/** "Basic 1/2 · Serious 0/1 · Full 0/1": the one line a tile has for progress. */
export function tierLine(tiers: KitSummary['tiers']): string {
  return (['basic', 'serious', 'full'] as KitTierId[]).map((t) => `${TIER_LABEL[t]} ${tiers[t].done}/${tiers[t].total}`).join(' · ');
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
  return (
    <Screen title="Kit" back={false} search={false} actions={<PrintButton />}>
      <Body>
        <p className="muted">
          What to have before anything happens, in three tiers: three days, two weeks, and no help coming.
          Quantities are for {people} {people === 1 ? 'person' : 'people'} on the household register. Ticks are shared by everyone on the box.
        </p>
        {q.loading && <p className="muted">Loading the kits…</p>}
        {q.error && <p className="warning">Kits unavailable: {q.error}</p>}
        {relevant.length > 0 && (
          <section aria-label="Kits for this household">
            <h2>Kits</h2>
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
      </Body>
    </Screen>
  );
}
