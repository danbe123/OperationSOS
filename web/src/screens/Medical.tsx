import { useMemo } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { LibraryItem } from '../api/types';
import { useQuery } from '../api/useQuery';
import { LibraryItemCard } from '../components/LibraryItemCard';
import { Tile } from '../components/Tile';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';

/**
 * The NHS A to Z lives inside the self-built `nhs_uk` ZIM (a zimit crawl, paths like `www.nhs.uk/conditions/`).
 * The host segment comes from the item's reader home so the crawl root never has to be hard-coded.
 */
export function nhsAtoZ(items: LibraryItem[]): { conditions: string | null; medicines: string | null; note: string | null } {
  const nhs = items.find((i) => i.id === 'nhs_uk');
  const medicinesZim = items.find((i) => i.id === 'nhs_medicines' && i.available && i.url);
  if (nhs && nhs.available && nhs.url) {
    const rest = nhs.url.replace(/^\/read\/nhs_uk\//, '');
    const host = rest.split('/')[0];
    const hasHost = host && rest.includes('/') && host.includes('.');
    return {
      conditions: hasHost ? `/read/nhs_uk/${host}/conditions/` : nhs.url,
      medicines: hasHost ? `/read/nhs_uk/${host}/medicines/` : nhs.url,
      note: null,
    };
  }
  if (nhs && !nhs.available) return { conditions: null, medicines: null, note: nhs.drive_label };
  if (medicinesZim) return { conditions: null, medicines: medicinesZim.url, note: 'NHS conditions not installed' };
  return { conditions: null, medicines: null, note: 'NHS not installed' };
}

export function Medical() {
  const cardsQ = useQuery(() => api.cards(), []);
  const libQ = useQuery(() => api.library(), []);
  const cards = useMemo(() => (cardsQ.data ?? []).slice().sort((a, b) => a.order - b.order), [cardsQ.data]);
  const medicalItems = useMemo(() => libQ.data?.categories.find((c) => c.id === 'medical')?.items ?? [], [libQ.data]);
  const nhs = nhsAtoZ(medicalItems);
  const householdQ = useQuery(() => api.household(), [], { refetchOnFocus: true });
  const people = (householdQ.data ?? []).filter((p) => p.needs || p.medications);
  return (
    <Screen title="Medical" back={false}>
      <Body>
        <Emergency999 />

        {/* After 999, the quick cards are the loudest thing here: they are the two-tap, life-critical
            items, so they are full-width rows and not the smallest tiles on the screen. */}
        <section aria-label="Quick cards">
          <h2>Quick cards</h2>
          <p className="muted">The few things you do in the first minute, in big type.</p>
          {cardsQ.error && <p className="warning">Cards unavailable: {cardsQ.error}</p>}
          <nav aria-label="Quick cards">
            <ul className="quick-cards">
              {cards.map((c) => (
                <li key={c.slug}>
                  <Link className="quick-card" to={`/medical/card/${c.slug}`}>
                    <Icon name={c.icon} size={28} />
                    <span>{c.title}</span>
                    <Icon name="forward" size={22} className="quick-card-go" />
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </section>

        {people.length > 0 && (
          <section className="panel" aria-label="Household medical needs">
            <div className="panel-head"><h2>In this household</h2><Link className="btn btn-small" to="/plan#household">Edit the register</Link></div>
            <ul className="list household-needs">
              {people.map((p) => (
                <li key={p.id}>
                  <strong>{p.name}</strong>{p.age !== null && <span className="muted"> ({p.age})</span>}
                  {p.needs && <span>: {p.needs}</span>}
                  {p.medications && <span className="muted"> · {p.medications}</span>}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section aria-label="NHS A to Z">
          <h2>NHS A to Z</h2>
          <nav className="tiles tiles-wide" aria-label="NHS A to Z">
            <Tile to={nhs.conditions ?? '#'} icon="medical" title="Conditions A to Z" subtitle="Symptoms, conditions, treatments" disabled={!nhs.conditions} note={nhs.conditions ? undefined : (nhs.note ?? undefined)} />
            <Tile to={nhs.medicines ?? '#'} icon="flask" title="Medicines A to Z" subtitle="Doses, side effects, UK names" disabled={!nhs.medicines} note={nhs.medicines ? undefined : (nhs.note ?? undefined)} />
            <Tile to="/medical/dose" icon="drop" title="Children's doses" subtitle="Paracetamol and ibuprofen by age" />
          </nav>
        </section>

        <section aria-label="Medical library">
          <h2>Medical library</h2>
          {libQ.error && <p className="warning">Library unavailable: {libQ.error}</p>}
          <ul className="list items" aria-label="Medical library">
            {medicalItems.map((item) => <LibraryItemCard key={item.id} item={item} />)}
          </ul>
        </section>
      </Body>
    </Screen>
  );
}
