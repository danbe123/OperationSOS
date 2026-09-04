import { QrCode } from '../components/QrCode';

/** WiFi join payload for an open network. Backslash, semicolon, comma, quote and colon are escaped per the WIFI: scheme. */
export function wifiQrPayload(ssid: string): string {
  const escaped = ssid.replace(/([\\;,":])/g, '\\$1');
  return `WIFI:T:nopass;S:${escaped};;`;
}

export function ConnectPanel({ ssid, ip, onClose }: { ssid: string; ip: string; onClose: () => void }) {
  const url = `http://${ip}/`;
  return (
    <div className="connect-panel" role="dialog" aria-modal="true" aria-label="Connect a phone">
      <h1 className="chrome">Connect a phone</h1>
      <div className="connect-cols">
        <section>
          <p className="connect-big">1. Join WiFi <strong>{ssid}</strong></p>
          <QrCode text={wifiQrPayload(ssid)} size={220} label="Scan to join the WiFi" />
        </section>
        <section>
          <p className="connect-big">2. Open <strong>{url}</strong></p>
          <p className="connect-big">or <strong>http://sos.box</strong></p>
          <QrCode text={url} size={220} label="Scan to open SOS" />
        </section>
      </div>
      <p className="connect-help">If the page will not load, turn mobile data off.</p>
      <button type="button" className="btn btn-big" onClick={onClose} autoFocus>Close</button>
    </div>
  );
}
