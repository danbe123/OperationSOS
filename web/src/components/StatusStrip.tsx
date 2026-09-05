import { useState } from 'react';
import { Link } from 'react-router';
import { useStatus } from '../api/status';
import { ConnectPanel } from '../kiosk/ConnectPanel';
import { Icon } from '../icons';
import { useCallsHidden } from '../situation/SituationProvider';

export function StatusStrip() {
  const { status, error } = useStatus();
  const callsHidden = useCallsHidden();
  const [open, setOpen] = useState(false);
  if (!status) {
    return <div className="status-strip chrome">{error ? `Box status unavailable: ${error}` : 'Checking the box…'}</div>;
  }
  const ext = status.disks.extended.mounted ? `External drive: ${status.disks.extended.free_gb} GB free` : 'External drive: not connected';
  const hot = status.cpu_temp_c !== null && status.cpu_temp_c >= status.thermal_ai_off_c;
  return (
    <div className="status-strip chrome" data-testid="status-strip">
      <span><Icon name="wifi" size={18} /> WiFi <strong>{status.hotspot.ssid}</strong></span>
      <span>http://{status.hotspot.ip}</span>
      <span>http://sos.box</span>
      <span><Icon name="drive" size={18} /> {ext}</span>
      <span className={hot ? 'status-hot' : undefined}>
        <Icon name="thermometer" size={18} /> {status.cpu_temp_c === null ? 'CPU: n/a' : `CPU ${Math.round(status.cpu_temp_c)}°C`}
      </span>
      {/* With both networks down nothing in the chrome should point at a phone; the WiFi name and the
          address beside it are still the way in from a handset, and the link says what to do instead. */}
      {callsHidden ? (
        <Link className="btn" to="/p/no-phones"><Icon name="alert" size={18} /> Phones down: what to do</Link>
      ) : (
        <button type="button" className="btn" onClick={() => setOpen(true)}><Icon name="phone" size={18} /> Connect a phone</button>
      )}
      {open && !callsHidden && <ConnectPanel ssid={status.hotspot.ssid} ip={status.hotspot.ip} onClose={() => setOpen(false)} />}
    </div>
  );
}
