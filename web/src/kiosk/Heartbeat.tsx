import { useEffect } from 'react';

/** How often the kiosk's own page tells the box it is alive. */
export const HEARTBEAT_MS = 30_000;

/** The kiosk browser's page says "alive" to the box every 30 s. If the page hangs, or its renderer dies and
 * leaves an "Aw, Snap" tab, the beats stop; `sos-kiosk-app` sees the age grow and restarts Chromium. Only the
 * kiosk's own page mounts this (a phone never does), it sends no data, and a failed beat is just a failed
 * beat. `keepalive` lets the last one leave with a page that is going away. */
export function KioskHeartbeat() {
  useEffect(() => {
    const beat = () => {
      fetch('/api/kiosk/alive', { method: 'POST', keepalive: true }).catch(() => { /* the box is away: the next beat tries again */ });
    };
    beat();
    const timer = window.setInterval(beat, HEARTBEAT_MS);
    return () => window.clearInterval(timer);
  }, []);
  return null;
}
