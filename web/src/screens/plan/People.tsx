import { PrintButton } from '../../components/PrintButton';
import { Screen, Body } from '../../shell/Screen';
import { Household } from './Household';
import './plan.css';

/** Who lives here: the register, and the form behind a button. The same rows the Medical screen
 * reads for needs and medications, edited in the one place they are kept. The register is worth
 * having on paper when the phones are down, so the screen offers Print: the rows go through, the
 * Edit and Remove buttons and the form do not. */
export function People() {
  return (
    <Screen title="People" actions={<PrintButton />} backTo="/plan">
      <Body>
        <section className="panel" aria-label="People">
          <Household />
        </section>
      </Body>
    </Screen>
  );
}
