import { AppBar } from '../../components/AppBar';
import { EventLog } from '../plan/EventLog';

export function Log() {
  return (
    <div className="screen">
      <AppBar title="Event log" />
      <EventLog compact />
    </div>
  );
}
