import { Screen, Body } from '../../shell/Screen';
import { Household } from './Household';
import './plan.css';

/** Who lives here: the register, and the form behind a button. The same rows the Medical screen
 * reads for needs and medications, edited in the one place they are kept. */
export function People() {
  return (
    <Screen title="People">
      <Body>
        <section className="panel" aria-label="People">
          <Household />
        </section>
      </Body>
    </Screen>
  );
}
