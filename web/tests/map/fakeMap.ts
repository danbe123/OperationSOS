import { vi } from 'vitest';

export type FakeLayer = { id: string; type: string; source?: string; 'source-layer'?: string; layout?: Record<string, unknown>; paint?: Record<string, unknown> };
export type FakeStyle = { version: 8; sources: Record<string, unknown>; layers: FakeLayer[]; glyphs?: string; name?: string };

export type FakeFeature = { id?: string | number; source: string; sourceLayer?: string; layer: { id: string };
  properties: Record<string, unknown>; geometry?: { type: string; coordinates: unknown } };

/** Minimal maplibre Map double: keeps a style, exposes the add/remove/get API and a tiny event emitter. */
export class FakeMap {
  style: FakeStyle = { version: 8, sources: {}, layers: [] };
  vectorLayers: Record<string, string[]> = {};
  center = { lng: -3.5, lat: 54.5 };
  zoom = 5.5;
  /** What queryRenderedFeatures answers; tests set this to put a feature "under" the pointer. */
  renderedFeatures: FakeFeature[] = [];
  canvas = document.createElement('canvas');
  /** The element maplibre was pointed at: the docked tooltip is appended to it, and its width decides
   * which side the tooltip docks to. jsdom lays nothing out, so the width is stated rather than measured. */
  container: HTMLElement;
  private handlers = new Map<string, Set<(e: unknown) => void>>();
  constructor(opts?: { container?: HTMLElement }) {
    this.container = opts?.container ?? document.createElement('div');
    Object.defineProperty(this.container, 'clientWidth', { value: 1000, configurable: true });
    this.container.appendChild(this.canvas);
  }
  queryRenderedFeatures = vi.fn((_box?: unknown, opts?: { layers?: string[] }) => this.renderedFeatures.filter((f) => !opts?.layers || opts.layers.includes(f.layer.id)));
  /** jsdom has no layout: every projection lands at the canvas origin, which is enough to query "the centre". */
  project = vi.fn((lngLat: [number, number]) => ({ x: 0, y: 0, lngLat }));
  unproject = vi.fn(() => ({ lng: this.center.lng, lat: this.center.lat }));
  addControl = vi.fn();
  remove = vi.fn();
  resize = vi.fn();
  flyTo = vi.fn((o: { center?: [number, number]; zoom?: number }) => {
    if (o.center) this.center = { lng: o.center[0], lat: o.center[1] };
    if (o.zoom !== undefined) this.zoom = o.zoom;
    this.emit('moveend', {});
  });
  jumpTo = this.flyTo;
  setStyle = vi.fn((style: string | FakeStyle, opts?: { transformStyle?: (prev: FakeStyle | undefined, next: FakeStyle) => FakeStyle }) => {
    const next: FakeStyle = typeof style === 'string'
      ? { version: 8, name: style, sources: { base: { type: 'vector', url: style } }, layers: [{ id: 'land', type: 'fill', source: 'base' }, { id: 'roads', type: 'line', source: 'base' }, { id: 'labels', type: 'symbol', source: 'base' }] }
      : style;
    this.style = opts?.transformStyle ? opts.transformStyle(this.style, next) : next;
    queueMicrotask(() => this.emit('style.load', {}));
  });
  getStyle() { return this.style; }
  getSource(id: string) { return this.style.sources[id] ? { vectorLayerIds: this.vectorLayers[id] } : undefined; }
  addSource(id: string, s: unknown) { this.style.sources[id] = s; }
  removeSource(id: string) { delete this.style.sources[id]; }
  getLayer(id: string) { return this.style.layers.find((l) => l.id === id); }
  addLayer(l: FakeLayer, before?: string) {
    const i = before ? this.style.layers.findIndex((x) => x.id === before) : -1;
    if (i === -1) this.style.layers.push(l);
    else this.style.layers.splice(i, 0, l);
  }
  removeLayer(id: string) { this.style.layers = this.style.layers.filter((l) => l.id !== id); }
  setLayoutProperty(id: string, k: string, v: unknown) { const l = this.getLayer(id); if (l) l.layout = { ...(l.layout ?? {}), [k]: v }; }
  setPaintProperty(id: string, k: string, v: unknown) { const l = this.getLayer(id); if (l) l.paint = { ...(l.paint ?? {}), [k]: v }; }
  getCenter() { return this.center; }
  getZoom() { return this.zoom; }
  getCanvas() {
    const c = this.canvas as HTMLCanvasElement & { toDataURL: () => string };
    c.toDataURL = () => 'data:image/png;base64,QQ==';
    return c;
  }
  getContainer() { return this.container; }
  on(ev: string, fn: (e: unknown) => void) { if (!this.handlers.has(ev)) this.handlers.set(ev, new Set()); this.handlers.get(ev)!.add(fn); return this; }
  off(ev: string, fn: (e: unknown) => void) { this.handlers.get(ev)?.delete(fn); return this; }
  emit(ev: string, e: unknown) { this.handlers.get(ev)?.forEach((fn) => fn(e)); }
  visibility(id: string): string { return (this.getLayer(id)?.layout?.visibility as string | undefined) ?? 'visible'; }
}
