import { Screen, Body } from '../../shell/Screen';
import { Notes } from './Notes';
import './plan.css';

/** Everything written down, in one list: notes and the pins dropped on the map, newest first. */
export function NotesScreen() {
  return (
    <Screen title="Notes and pins">
      <Body>
        <section className="panel" aria-label="Notes and pins">
          <Notes pins />
        </section>
      </Body>
    </Screen>
  );
}
