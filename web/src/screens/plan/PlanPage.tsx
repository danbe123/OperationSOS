import { api } from '../../api/client';
import { useQuery } from '../../api/useQuery';
import { Html } from '../../components/Html';
import { PrintButton } from '../../components/PrintButton';
import { Screen, Body } from '../../shell/Screen';
import './plan.css';

/** The household plan itself: meeting points, the out-of-area contact, who fetches whom. It is a
 * page from the box, written to be printed and stuck to the inside of a cupboard door. */
export function PlanPage() {
  const planQ = useQuery(() => api.page('household-plan'), []);
  return (
    <Screen title="The plan" actions={<PrintButton />}>
      <Body>
        <section className="panel" aria-label="The plan">
          {planQ.error && <p className="warning">The plan is unavailable: {planQ.error}</p>}
          {planQ.data && <Html html={planQ.data.html} />}
        </section>
      </Body>
    </Screen>
  );
}
