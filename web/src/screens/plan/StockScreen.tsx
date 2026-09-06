import { Screen, Body } from '../../shell/Screen';
import { Stock } from './Stock';
import './plan.css';

/** What is in the cupboard, and how long it would last: three meters against a fortnight, the rows
 * beneath them shortest run first, and the form behind a button. */
export function StockScreen() {
  return (
    <Screen title="Stock" backTo="/plan">
      <Body>
        <section className="panel" aria-label="Stock">
          <Stock />
        </section>
      </Body>
    </Screen>
  );
}
