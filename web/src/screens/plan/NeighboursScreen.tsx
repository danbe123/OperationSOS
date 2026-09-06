import { Screen, Body } from '../../shell/Screen';
import { Neighbours, StreetListLink } from './Neighbours';
import './plan.css';

/** The street: what the box has worked out it can do, who is on it, and the sheet to put through
 * doors. The printable list is the screen's own action, at the top where a hand reaches for it. */
export function NeighboursScreen() {
  return (
    <Screen title="Neighbours" actions={<StreetListLink />}>
      <Body>
        <section className="panel" aria-label="Neighbours">
          <Neighbours />
        </section>
      </Body>
    </Screen>
  );
}
