import { useEffect, useState } from 'react';

/* The encoder is 24 kB and is wanted by three panels nobody opens in the first minute, so it is
 * fetched when the first code is drawn rather than parsed on the front door. One promise for the
 * whole box: two codes side by side (the Connect panel's pair) share the one fetch. */
/* The types package declares the module's exports as namespace members, so the default export it
 * actually ships is described here rather than asserted at the call site. */
type Encoder = { default: { toDataURL: (text: string, opts: Record<string, unknown>) => Promise<string> } };
let encoder: Promise<Encoder> | null = null;
const loadEncoder = (): Promise<Encoder> => (encoder ??= import('qrcode') as unknown as Promise<Encoder>);

/** The one colour the code itself may be. A reader is built for dark marks on a light ground and
 * nothing else; the theme decides how much light there is around them, never what they are. */
const QUIET = '#ffffff';
const MARK = '#000000';

/** Is this token value a dark surface? The tokens are written as hex, and a browser hands back
 * whatever was declared, so rgb() is read too. Anything else counts as light, which is the safe
 * guess: a light theme gets the generous white border every scanner prefers. */
export function isDarkSurface(value: string): boolean {
  const text = value.trim();
  let r: number;
  let g: number;
  let b: number;
  const long = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(text);
  const short = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(text);
  const rgb = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i.exec(text);
  if (long) {
    [r, g, b] = [parseInt(long[1], 16), parseInt(long[2], 16), parseInt(long[3], 16)];
  } else if (short) {
    [r, g, b] = [parseInt(short[1] + short[1], 16), parseInt(short[2] + short[2], 16), parseInt(short[3] + short[3], 16)];
  } else if (rgb) {
    [r, g, b] = [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])];
  } else {
    return false;
  }
  return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 < 0.4;
}

/** A code to point another phone's camera at.
 *
 * Blackout exists to protect somebody's dark adaptation, and a 220 px sheet of white paper on the
 * screen undoes an hour of it in one blink. So on a dark theme the white stops at the edge of the
 * code and the panel's own colour carries on around it, and the four-module white border a reader
 * likes is offered rather than imposed: "Make it brighter to scan" hands it over when a camera
 * refuses the dim one. On a light theme the panel is already the quiet zone, so it gets the full
 * border and no button, because there is nothing left to brighten. */
export function QrCode({ text, size, label }: { text: string; size: number; label: string }) {
  const [bright, setBright] = useState(false);
  // A count of the palette changes so far, so the code is drawn again when the household changes
  // theme or the box dims itself. Watching the element the theme is written on keeps the code
  // working wherever it is rendered, including the panels that have no theme provider above them.
  const [palette, setPalette] = useState(0);
  const [src, setSrc] = useState<string | null>(null);
  // The panel colour as the theme has it now: the frame around the code is painted with it, so the
  // white on a dark theme stops at the edge of the code itself.
  const [surface, setSurface] = useState<{ dark: boolean; panel: string }>({ dark: false, panel: QUIET });

  useEffect(() => {
    let alive = true;
    // The theme writes data-theme on <html> from an effect of its own, and a child's effects run
    // before its parent's, so reading the tokens here and now would read the palette the box has
    // just left. A microtask lands after the whole flush, when the new palette is on the element.
    void Promise.resolve().then(async () => {
      if (!alive) return;
      const panel = getComputedStyle(document.documentElement).getPropertyValue('--panel').trim() || QUIET;
      const dark = isDarkSurface(panel);
      const onDark = dark && !bright;
      setSurface({ dark, panel });
      try {
        const { default: QRCode } = await loadEncoder();
        const url = await QRCode.toDataURL(text, { width: size, margin: onDark ? 1 : 4, color: { dark: MARK, light: QUIET } });
        if (alive) setSrc(url);
      } catch {
        if (alive) setSrc(null);
      }
    });
    return () => { alive = false; };
  }, [text, size, palette, bright]);

  useEffect(() => {
    const observer = new MutationObserver(() => setPalette((n) => n + 1));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-dim'] });
    return () => observer.disconnect();
  }, []);

  // The frame is the panel around the code, so the white is the code and nothing else. Inline,
  // because it has to beat the flat `background: #fff` the shell puts on every quiet zone.
  const framed = surface.dark && !bright;
  const frame = { background: framed ? surface.panel : QUIET, padding: framed ? 6 : 0, borderRadius: 'var(--radius)', display: 'inline-flex', lineHeight: 0, maxWidth: '100%' };
  return (
    <figure className="qr" style={{ width: size, maxWidth: '100%' }}>
      <span className="qr-frame" style={frame}>
        {src
          ? <img src={src} width={size} height={size} alt={`QR code: ${label}`} style={{ width: '100%', height: 'auto', background: QUIET }} />
          : <div className="qr-blank" style={{ width: size, maxWidth: '100%', aspectRatio: '1 / 1', background: framed ? surface.panel : QUIET }} />}
      </span>
      <figcaption>{label}</figcaption>
      {surface.dark && (
        <button type="button" className="btn btn-small" aria-pressed={bright} onClick={() => setBright(!bright)}>
          {bright ? 'Dim it again' : 'Make it brighter to scan'}
        </button>
      )}
    </figure>
  );
}
