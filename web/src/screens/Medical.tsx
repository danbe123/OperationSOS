import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { Card, LibraryItem } from '../api/types';
import { useQuery } from '../api/useQuery';
import { LibraryItemCard } from '../components/LibraryItemCard';
import { Tile } from '../components/Tile';
import { Icon } from '../icons';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import './card.css';

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

/** The groups the cards are picked from. The first minute comes first; a card not named here lands
 * in "More cards" rather than vanishing, so a new card is on the screen the day it is written. */
export const CARD_GROUPS: { id: string; title: string; slugs: string[] }[] = [
  { id: 'first-minute', title: 'The first minute', slugs: ['cpr-adult', 'cpr-child', 'severe-bleeding', 'choking', 'anaphylaxis', 'heart-attack', 'stroke', 'recovery-position', 'drowning', 'seizures', 'shock'] },
  { id: 'injuries', title: 'Injuries', slugs: ['broken-bones', 'sprains-strains', 'wound-cleaning', 'wound-closure', 'burns', 'head-injury', 'spinal-injury', 'eye-injury', 'nosebleed', 'bites-stings', 'electric-shock'] },
  { id: 'heat-cold', title: 'Heat, cold and water', slugs: ['hypothermia', 'frostbite', 'heat-stroke', 'dehydration'] },
  { id: 'poison', title: 'Poison, gas and radiation', slugs: ['carbon-monoxide', 'chemical-exposure', 'poisoning', 'radiation-sickness'] },
  { id: 'illness', title: 'Illness', slugs: ['sepsis', 'asthma-attack', 'low-blood-sugar', 'fever-child', 'dental-abscess'] },
  { id: 'birth', title: 'Pregnancy and birth', slugs: ['childbirth', 'pregnancy-emergencies'] },
];

/** The words on a card tile. The summary is clamped to two lines by the stylesheet; when it is cut,
 * the tile says so with a "Read more" under it, measured rather than guessed, so a short summary
 * never carries the label and a long one never ends mid-sentence with nothing said. */
function QuickCardText({ title, summary }: { title: string; summary?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [clamped, setClamped] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setClamped(el.scrollHeight > el.clientHeight + 1);
    check();
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(check);
    observer?.observe(el);
    return () => observer?.disconnect();
  }, [summary]);
  return (
    <span className="quick-card-text">
      <span className="quick-card-title">{title}</span>
      {summary && <span className="quick-card-sub" ref={ref}>{summary}</span>}
      {summary && <span className={clamped ? "quick-card-more" : "quick-card-more quick-card-more-off"} aria-hidden="true">… Read more</span>}
    </span>
  );
}

export function groupCards(cards: Card[], term = ''): { id: string; title: string; cards: Card[] }[] {
  const t = term.trim().toLowerCase();
  const hit = (c: Card) => !t || c.title.toLowerCase().includes(t) || (c.summary ?? '').toLowerCase().includes(t);
  const bySlug = new Map(cards.map((c) => [c.slug, c]));
  const placed = new Set<string>();
  const out = CARD_GROUPS.map((g) => {
    const members = g.slugs.map((s) => bySlug.get(s)).filter((c): c is Card => Boolean(c));
    members.forEach((c) => placed.add(c.slug));
    return { id: g.id, title: g.title, cards: members.filter(hit) };
  });
  const rest = cards.filter((c) => !placed.has(c.slug)).sort((a, b) => a.order - b.order).filter(hit);
  if (rest.length) out.push({ id: 'more', title: 'More cards', cards: rest });
  return out.filter((g) => g.cards.length > 0);
}

export function Medical() {
  const cardsQ = useQuery(() => api.cards(), []);
  const libQ = useQuery(() => api.library(), []);
  const [term, setTerm] = useState('');
  const groups = useMemo(() => groupCards(cardsQ.data ?? [], term), [cardsQ.data, term]);
  const medicalItems = useMemo(() => libQ.data?.categories.find((c) => c.id === 'medical')?.items ?? [], [libQ.data]);
  const nhs = nhsAtoZ(medicalItems);
  return (
    <Screen title="Medical" back={false}>
      <Body>
        <Emergency999 />

        {/* After 999, the quick cards are the loudest thing here. Thirty-odd cards in one column is a
            wall, so they come in groups, the first minute first, and each row says when it applies. */}
        <section aria-label="Quick cards">
          <h2>Quick cards</h2>
          <p className="muted">What to do in the first minutes, one sheet each, in big type.</p>
          {cardsQ.error && <p className="warning">Cards unavailable: {cardsQ.error}</p>}
          <label className="field card-filter">
            <span>Find a card</span>
            <input type="search" aria-label="Find a card" value={term} placeholder="bleeding, burn, choking" onChange={(e) => setTerm(e.target.value)} />
          </label>
          {term && groups.length === 0 && <p>Nothing matches. Try a shorter word, or the <Link to="/medical#nhs">NHS A to Z</Link>.</p>}
          <nav aria-label="Quick cards" className="card-groups">
            {groups.map((g) => (
              <section key={g.id} className="card-group" aria-label={g.title}>
                <h2>{g.title}</h2>
                <ul className="quick-cards">
                  {g.cards.map((c) => (
                    <li key={c.slug}>
                      <Link className={g.id === 'first-minute' ? 'quick-card quick-card-urgent' : 'quick-card'} to={`/medical/card/${c.slug}`}>
                        <Icon name={c.icon} size={28} />
                        <QuickCardText title={c.title} summary={c.summary} />
                        <Icon name="forward" size={22} className="quick-card-go" />
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </nav>
        </section>

        <section aria-label="NHS A to Z" id="nhs">
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
