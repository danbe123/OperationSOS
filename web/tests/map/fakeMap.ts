import { vi } from 'vitest';

export type FakeLayer = { id: string; type: string; source?: string; 'source-layer'?: string; layout?: Record<string, unknown>; paint?: Record<string, unknown> };
export type FakeStyle = { version: 8; sources: Record<string, unknown>; layers: FakeLayer[]; glyphs?: string; name?: string };

/** Minimal maplibre Map double: keeps a style, exposes the add/remove/get API and a tiny event emitter. */
export class FakeMap {
  style: FakeStyle = { version: 8, sources: {}, layers: [] };
  vectorLayers: Record<string, string[]> = {};
  center = { lng: -3.5, lat: 54.5 };
  zoom = 5.5;
  private handlers = new Map<string, Set<(e: unknown) => void>>();
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
  getCanvas() { return { toDataURL: () => 'data:image/png;base64,QQ==', width: 853, height: 400 } as unknown as HTMLCanvasElement; }
  on(ev: string, fn: (e: unknown) => void) { if (!this.handlers.has(ev)) this.handlers.set(ev, new Set()); this.handlers.get(ev)!.add(fn); return this; }
  off(ev: string, fn: (e: unknown) => void) { this.handlers.get(ev)?.delete(fn); return this; }
  emit(ev: string, e: unknown) { this.handlers.get(ev)?.forEach((fn) => fn(e)); }
  visibility(id: string): string { return (this.getLayer(id)?.layout?.visibility as string | undefined) ?? 'visible'; }
}
