import { PrintButton } from '../../components/PrintButton';
import { Screen, Body } from '../../shell/Screen';
import { Stock } from './Stock';
import './plan.css';

/** What is in the cupboard, and how long it would last: three meters against a fortnight, the rows
 * beneath them shortest run first, and the form behind a button. Print puts the meters and the rows
 * on paper — a stocktake to carry to the cupboard — and leaves the Change buttons and the add form
 * behind on the screen. */
export function StockScreen() {
  return (
    <Screen title="Stock" actions={<PrintButton />} backTo="/plan">
      <Body>
        <section className="panel" aria-label="Stock">
          <Stock />
        </section>
      </Body>
    </Screen>
  );
}
