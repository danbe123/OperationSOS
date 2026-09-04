import { AppBar } from '../components/AppBar';
import { StatusStrip } from '../components/StatusStrip';

export function Home() {
  return (
    <div className="screen">
      <AppBar title="Operation SOS" back={false} />
      <StatusStrip />
    </div>
  );
}
