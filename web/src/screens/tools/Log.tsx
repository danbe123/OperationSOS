import { Screen, Body } from '../../shell/Screen';
import { EventLog } from '../plan/EventLog';

export function Log() {
  return (
    <Screen title="Event log">
      <Body><EventLog compact /></Body>
    </Screen>
  );
}
