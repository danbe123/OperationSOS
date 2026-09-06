import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError } from '../api/client';
import { useStatus } from '../api/status';
import type { AiState, Status, UpdateProgress } from '../api/types';
import { errorMessage } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Badge } from '../components/Badge';
import { notify } from '../components/Notice';
import { usePinGate } from '../components/PinModal';
import { Progress } from '../components/Progress';
import { useKiosk } from '../kiosk/KioskProvider';
import { THEMES, type Theme } from '../theme/ThemeProvider';

export function formatUptime(s: number): string {
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days} days ${hours} h`;
  if (hours > 0) return `${hours} h ${mins} min`;
  return `${mins} min`;
}

const AI_LABEL: Record<AiState, string> = { off: 'off', starting: 'starting', ready: 'ready', error: 'error', 'off-thermal': 'off (too hot)', busy: 'busy' };

function StatusCards({ s }: { s: Status }) {
  return (
    <div className="panels">
      <div className="panel"><h3>Box</h3><p>Version <strong>{s.version}</strong></p><p>Up {formatUptime(s.uptime_s)}</p><p>Working <strong>{s.load[0] < 1 ? 'lightly' : s.load[0] < 2.5 ? 'steadily' : 'hard'}</strong></p></div>
      <div className="panel"><h3>Heat and memory</h3><p>CPU <strong>{s.cpu_temp_c === null ? 'n/a' : `${Math.round(s.cpu_temp_c)}°C`}</strong></p><p>Memory <strong>{Math.round((s.mem.used_mb / Math.max(1, s.mem.total_mb)) * 100)}% used</strong> of {(s.mem.total_mb / 1024).toFixed(1)} GB</p></div>
      <div className="panel"><h3>Storage</h3><p>Core: <strong>{s.disks.core.free_gb} of {s.disks.core.total_gb} GB free</strong></p><p>External: <strong>{s.disks.extended.mounted ? `${s.disks.extended.free_gb} of ${s.disks.extended.total_gb} GB free` : 'Not connected'}</strong></p></div>
      <div className="panel"><h3>Hotspot</h3><p>WiFi <strong>{s.hotspot.ssid}</strong> {s.hotspot.enabled ? '' : '(off)'}</p><p>http://{s.hotspot.ip}</p><p>http://sos.box</p><p><strong>{s.hotspot.clients} {s.hotspot.clients === 1 ? 'device' : 'devices'}</strong> connected</p></div>
      <div className="panel"><h3>Security</h3><p>{s.pin_required ? 'PIN protection on' : 'PIN protection off'}</p><p className="muted">{s.dev ? 'Development profile' : 'Production profile'}</p></div>
    </div>
  );
}

/**
 * Everything below the loading gate. A separate component so the form fields below can seed their
 * defaults from `status` with a plain lazy `useState` initializer, evaluated once on this
 * component's first (and only, thanks to `status` being non-null for its whole lifetime) mount —
 * rather than an effect that runs *after* the first render, which would leave a window where the
 * field is briefly empty and a fast interaction (or a fast test) can be silently overwritten once
 * the effect fires.
 */
function SystemBody({ status, kiosk, run, dialog, update, refresh }: {
  status: Status;
  kiosk: boolean;
  run: <T>(fn: () => Promise<T>) => Promise<T | undefined>;
  dialog: ReturnType<typeof usePinGate>['dialog'];
  update: (s: Status) => void;
  refresh: () => Promise<void>;
}) {
  const [ssid, setSsid] = useState(status.hotspot.ssid);
  const [passphrase, setPassphrase] = useState('');
  const [thermal, setThermal] = useState(String(status.thermal_ai_off_c));
  const [idle, setIdle] = useState(String(status.idle_minutes));
  const [home, setHome] = useState(String(status.home_minutes));
  const [theme, setTheme] = useState<Theme>(status.default_theme);
  const [brightness, setBrightness] = useState(100);
  const [backlightNote, setBacklightNote] = useState<string | null>(null);
  const [newPin, setNewPin] = useState('');
  const [tiers, setTiers] = useState<('core' | 'extended')[]>(['core']);
  const [progress, setProgress] = useState<UpdateProgress | null>(null);
  const [aiState, setAiState] = useState<AiState | null>(null);
  const backlightTimer = useRef<number | undefined>(undefined);

  const pollingUpdate = progress !== null && !progress.done;
  useEffect(() => {
    if (!pollingUpdate) return;
    let cancelled = false;
    let timer: number;
    const poll = async () => {
      let done = false;
      try {
        const next = await api.updateProgress();
        done = next.done;
        if (!cancelled) setProgress(next);
      } catch (e) {
        if (!cancelled) notify(`Update progress unavailable: ${errorMessage(e)}`);
      }
      if (!cancelled && !done) timer = window.setTimeout(() => void poll(), 2000);
    };
    timer = window.setTimeout(() => void poll(), 2000);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [pollingUpdate]);

  const gated = async (fn: () => Promise<Status>) => {
    try {
      const s = await run(fn);
      if (s) update(s);
    } catch (e) {
      notify(errorMessage(e));
    }
  };

  const saveHotspot = (e: FormEvent) => {
    e.preventDefault();
    const body = passphrase ? { ssid: ssid.trim(), passphrase } : { ssid: ssid.trim() };
    void gated(() => api.hotspot(body));
  };
  const saveSettings = (e: FormEvent) => {
    e.preventDefault();
    void gated(() => api.settings({ thermal_ai_off_c: Number(thermal), idle_minutes: Number(idle), home_minutes: Number(home), default_theme: theme }));
  };
  const onBrightness = (level: number) => {
    setBrightness(level);
    window.clearTimeout(backlightTimer.current);
    backlightTimer.current = window.setTimeout(async () => {
      try {
        await api.systemBacklight(level);
        setBacklightNote(null);
      } catch (e) {
        setBacklightNote(e instanceof ApiError && e.status === 501 ? 'No backlight control on this display' : errorMessage(e));
      }
    }, 250);
  };
  const toggleAi = async (on: boolean) => {
    try {
      const r = await run(() => (on ? api.aiEnable() : api.aiDisable()));
      if (r) {
        setAiState(r.state);
        await refresh();
      }
    } catch (e) {
      notify(errorMessage(e));
    }
  };
  const changePin = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await run(() => api.changePin(newPin));
      if (r) {
        notify('PIN changed');
        setNewPin('');
        await refresh();
      }
    } catch (err) {
      notify(errorMessage(err));
    }
  };
  const startUpdate = async () => {
    try {
      const r = await run(() => api.update(tiers));
      if (r) setProgress({ running: true, lines: ['Starting…'], done: false, ok: null });
    } catch (e) {
      notify(errorMessage(e));
    }
  };
  const rescan = async () => {
    try {
      const r = await api.rescan();
      notify(`Rescanned: ${r.available} of ${r.items} items available`);
      await refresh();
    } catch (e) {
      notify(errorMessage(e));
    }
  };

  const ai = aiState ?? status.ai.state;

  return (
    <Screen title="System" className="system">
      <Body>
      {dialog}
      <StatusCards s={status} />

      <section className="panel stack">
        <h2>Hotspot</h2>
        <form className="stack" onSubmit={saveHotspot}>
          <label className="field"><span>Network name (SSID)</span><input type="text" aria-label="Network name (SSID)" value={ssid} onChange={(e) => setSsid(e.target.value)} maxLength={32} /></label>
          <label className="field"><span>Passphrase (blank for an open network)</span><input type="password" aria-label="Passphrase (blank for an open network)" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} minLength={passphrase ? 8 : undefined} maxLength={63} /></label>
          <button type="submit" className="btn btn-primary">Save hotspot</button>
        </form>
      </section>

      <section className="panel stack">
        <h2>Ethernet</h2>
        <p className="muted">Home router: plug into your router for updates and http://sos.local. Direct: plug a laptop straight in (10.43.0.1).</p>
        <div className="row">
          <button type="button" className={status.eth_mode === 'client' ? 'btn active' : 'btn'} aria-pressed={status.eth_mode === 'client'} onClick={() => void gated(() => api.ethMode('client'))}>Home router (DHCP)</button>
          <button type="button" className={status.eth_mode === 'direct' ? 'btn active' : 'btn'} aria-pressed={status.eth_mode === 'direct'} onClick={() => void gated(() => api.ethMode('direct'))}>Direct laptop link</button>
        </div>
      </section>

      <section className="panel stack">
        <h2>Power</h2>
        <p className="muted">Low power dims the screen and stops the AI.</p>
        <div className="row">
          <button type="button" className={status.power_mode === 'normal' ? 'btn active' : 'btn'} aria-pressed={status.power_mode === 'normal'} onClick={() => void gated(() => api.powerMode('normal'))}>Normal</button>
          <button type="button" className={status.power_mode === 'low' ? 'btn active' : 'btn'} aria-pressed={status.power_mode === 'low'} onClick={() => void gated(() => api.powerMode('low'))}>Low power</button>
        </div>
        <label className="field"><span>Screen brightness</span><input type="range" aria-label="Screen brightness" min={10} max={100} step={5} value={brightness} onChange={(e) => onBrightness(Number(e.target.value))} /></label>
        {backlightNote && <p className="warning">{backlightNote}</p>}
      </section>

      <section className="panel stack">
        <h2>AI assistant</h2>
        <p>State: <Badge tone={ai === 'ready' ? 'ok' : ai === 'off-thermal' || ai === 'error' ? 'danger' : 'default'}>{AI_LABEL[ai]}</Badge>{status.ai.model && <span className="muted"> · {status.ai.model}</span>}</p>
        {ai === 'off-thermal' && <p className="warning">The AI switched off because the box got too hot. Let it cool, then turn it on again.</p>}
        {status.ai.message && <p className="muted">{status.ai.message}</p>}
        <div className="row">
          {ai === 'off' || ai === 'off-thermal' || ai === 'error' ? (
            <button type="button" className="btn btn-primary" onClick={() => void toggleAi(true)} disabled={status.power_mode === 'low'}>Turn AI on</button>
          ) : (
            <button type="button" className="btn" onClick={() => void toggleAi(false)}>Turn AI off</button>
          )}
        </div>
        {status.power_mode === 'low' && <p className="muted">Leave low power mode to use the AI.</p>}
      </section>

      <section className="panel stack">
        <h2>Settings</h2>
        <form className="stack" onSubmit={saveSettings}>
          <label className="field"><span>Stop the AI above (°C)</span><input type="number" aria-label="Stop the AI above (°C)" min={60} max={95} value={thermal} onChange={(e) => setThermal(e.target.value)} inputMode="numeric" /></label>
          <label className="field"><span>Dim after (minutes)</span><input type="number" aria-label="Dim after (minutes)" min={1} max={120} value={idle} onChange={(e) => setIdle(e.target.value)} inputMode="numeric" /></label>
          <label className="field"><span>Return to Home after (minutes)</span><input type="number" aria-label="Return to Home after (minutes)" min={5} max={480} value={home} onChange={(e) => setHome(e.target.value)} inputMode="numeric" /></label>
          <label className="field"><span>Default theme</span>
            <select aria-label="Default theme" value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
              {THEMES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          <button type="submit" className="btn btn-primary">Save settings</button>
        </form>
      </section>

      <section className="panel stack">
        <h2>Admin PIN</h2>
        <form className="row" onSubmit={(e) => void changePin(e)}>
          <input type="password" inputMode="numeric" pattern="[0-9]*" aria-label="New PIN" placeholder="New PIN" value={newPin} onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ''))} maxLength={8} />
          <button type="submit" className="btn" disabled={newPin.length < 4}>Change PIN</button>
        </form>
        <p className="muted">Forgotten PIN: run <code>sos pin reset</code> on the box.</p>
      </section>

      <section className="panel stack">
        <h2>Update content</h2>
        <p className="muted">Needs the box on a router with internet (ethernet).</p>
        <div className="row">
          <label className="check-row"><input type="checkbox" checked={tiers.includes('core')} onChange={(e) => setTiers(e.target.checked ? [...new Set([...tiers, 'core' as const])] : tiers.filter((t) => t !== 'core'))} /> Core</label>
          <label className="check-row"><input type="checkbox" disabled={!status.disks.extended.mounted} checked={tiers.includes('extended')} onChange={(e) => setTiers(e.target.checked ? [...new Set([...tiers, 'extended' as const])] : tiers.filter((t) => t !== 'extended'))} /> External drive</label>
          <button type="button" className="btn btn-primary" onClick={() => void startUpdate()} disabled={tiers.length === 0 || (progress?.running ?? false)}>Start update</button>
          {kiosk && <button type="button" className="btn" onClick={() => void rescan()}>Rescan library</button>}
        </div>
        {progress && (
          <>
            {progress.running && <Progress label="Updating" />}
            {progress.done && <p className={progress.ok ? 'ok' : 'warning'}>{progress.ok ? 'Update finished' : 'Update failed'}</p>}
            <pre className="log" role="log">{progress.lines.map((l, i) => <div key={i}>{l}</div>)}</pre>
          </>
        )}
      </section>
      </Body>
    </Screen>
  );
}

export function System() {
  const kiosk = useKiosk();
  const { status, error, update, refresh } = useStatus();
  const { run, dialog } = usePinGate();

  if (!status) {
    return (
      <Screen title="System">
        <Body>{error ? <p className="warning">Box status unavailable: {error}</p> : <p className="muted">Reading the box status…</p>}</Body>
      </Screen>
    );
  }

  return <SystemBody status={status} kiosk={kiosk} run={run} dialog={dialog} update={update} refresh={refresh} />;
}
