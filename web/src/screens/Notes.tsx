import { PrintButton } from '../components/PrintButton';
import { Screen, Body } from '../shell/Screen';
import { Notes as NotesList } from './plan/Notes';

/** Everything written down, in one list: notes and the pins dropped on the map, newest first. Print
 * puts the lot on one sheet; the Edit and Delete buttons and the form stay behind on the screen. */
export function NotesScreen() {
  return (
    <Screen title="Notes and pins" actions={<PrintButton />} backTo="/">
      <Body>
        <section className="panel" aria-label="Notes and pins">
          <NotesList pins />
        </section>
      </Body>
    </Screen>
  );
}
