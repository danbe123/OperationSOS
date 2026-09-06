import { Tile } from '../components/Tile';
import { Screen, Body } from '../shell/Screen';

export const TOOL_TILES = [
  { to: '/fieldcraft', icon: 'fire', title: 'Field craft', subtitle: 'Shelter, fire, water, wild food, moving' },
  { to: '/tools/timers', icon: 'alert', title: 'Timers', subtitle: 'Boil, CPR beat, fallout, doses' },
  { to: '/tools/sun', icon: 'sun', title: 'Sun and moon', subtitle: 'Sunrise, sunset, daylight, phase' },
  { to: '/tools/calc', icon: 'bolt', title: 'Calculators', subtitle: 'Generator, battery, solar, rations' },
  { to: '/situation#log', icon: 'book', title: 'Event log', subtitle: 'What happened, when' },
  { to: '/medical/dose', icon: 'flask', title: "Children's doses", subtitle: 'Paracetamol and ibuprofen by age' },
  { to: '/plan#stock', icon: 'wheat', title: 'Stock', subtitle: 'Water, food, fuel: days left' },
] as const;

export function Tools() {
  return (
    <Screen title="Tools">
      <Body>
        <p className="muted measure">Small offline tools. Nothing here needs the internet.</p>
        <nav className="tiles tiles-wide" aria-label="Tools">
          {TOOL_TILES.map((t) => <Tile key={t.to} to={t.to} icon={t.icon} title={t.title} subtitle={t.subtitle} />)}
        </nav>
      </Body>
    </Screen>
  );
}
