import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { FakeMap } from '../map/fakeMap';
import { mapConfig, notes, places } from '../fixtures/api';

const created = vi.hoisted(() => ({ maps: [] as unknown[] }));
vi.mock('maplibre-gl', async () => {
  const { FakeMap } = await import('../map/fakeMap');
  class Map extends FakeMap {
    constructor(opts: { style: string; center: [number, number]; zoom: number }) {
      super();
      this.center = { lng: opts.center[0], lat: opts.center[1] };
      this.zoom = opts.zoom;
      this.setStyle(opts.style);
      created.maps.push(this);
    }
  }
  const { FakePopup } = await import('../map/fakeMap');
  const stub = { Map, Popup: FakePopup, NavigationControl: class {}, ScaleControl: class {}, addProtocol: vi.fn() };
  return { default: stub, ...stub };
});
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

function lastMap(): FakeMap {
  return created.maps[created.maps.length - 1] as FakeMap;
}
function mockApis() {
  vi.spyOn(api, 'mapConfig').mockResolvedValue(mapConfig);
  vi.spyOn(api, 'notes').mockResolvedValue(notes.filter((n) => n.kind === 'pin'));
  vi.spyOn(api, 'places').mockResolvedValue(places);
}
afterEach(() => { vi.useRealTimers(); created.maps.length = 0; });

describe('Map screen', () => {
  it('creates the map from config, adds terrain and default overlays, and writes the view to the URL', async () => {
    mockApis();
    const { router } = renderRoute('/map');
    await screen.findByRole('button', { name: /Layers/ });
    await act(async () => {});
    const map = lastMap();
    expect(map.style.name).toBe('/maps/styles/osm-field.json');
    expect(map.getLayer('sos-hillshade')).toBeDefined();
    expect(map.getLayer('sos-contours')).toBeDefined();
    expect(map.visibility('sos-overlay-health-point')).toBe('none');
    expect(map.style.sources['sos-overlay-footpaths']).toBeDefined();
    expect(map.style.sources['sos-overlay-flood-zones']).toBeUndefined();
    expect(router.state.location.search).toBe('?lat=54.50000&lon=-3.50000&z=5.5&overlay=footpaths');
    expect(map.getLayer('sos-pins-point')).toBeDefined();
  });

  it('toggles overlays from the layer panel with coverage notes and availability', async () => {
    mockApis();
    const user = userEvent.setup();
    const { router } = renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Layers/ }));
    const panel = screen.getByRole('dialog', { name: 'Layers' });
    await user.click(within(panel).getByLabelText('Hospitals, pharmacies, GP surgeries'));
    expect(lastMap().visibility('sos-overlay-health-point')).toBe('visible');
    expect(router.state.location.search).toContain('overlay=footpaths&overlay=health');
    expect(within(panel).getByText('No data for Scotland, Northern Ireland, Republic of Ireland, Isle of Man, Channel Islands')).toBeInTheDocument();
    expect(within(panel).getByLabelText('Flood zones')).toBeDisabled();
    expect(within(panel).getByText('Not installed')).toBeInTheDocument();
    await user.click(within(panel).getByLabelText('Contours and hillshade'));
    expect(lastMap().visibility('sos-hillshade')).toBe('none');
  });

  it('switching base keeps overlays and terrain across setStyle', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?overlay=health');
    await user.click(await screen.findByRole('button', { name: /Layers/ }));
    const panel = screen.getByRole('dialog', { name: 'Layers' });
    const map = lastMap();
    expect(map.visibility('sos-overlay-health-point')).toBe('visible');
    await user.click(within(panel).getByLabelText('OS Open Zoomstack'));
    expect(map.setStyle).toHaveBeenLastCalledWith('/maps/styles/os-field.json', expect.objectContaining({ transformStyle: expect.any(Function) }));
    await act(async () => {});
    expect(map.style.name).toBe('/maps/styles/os-field.json');
    expect(map.getLayer('land')).toBeDefined();
    expect(map.visibility('sos-overlay-health-point')).toBe('visible');
    expect(map.getLayer('sos-hillshade')).toBeDefined();
    expect(localStorage.getItem('sos.mapBase')).toBe('os');
  });

  it('reads lat/lon/z/label from the query, shows the label and the centre grid reference', async () => {
    mockApis();
    renderRoute('/map?lat=50.9379&lon=-1.4708&z=14&label=OS+HQ');
    await screen.findByRole('button', { name: /Layers/ });
    await act(async () => {}); // let api.mapConfig() resolve and the map mount, as the first test also does
    const map = lastMap();
    expect(map.center).toEqual({ lng: -1.4708, lat: 50.9379 });
    expect(map.zoom).toBe(14);
    expect(screen.getByText('OS HQ')).toHaveClass('map-label');
    expect(screen.getByTestId('map-readout')).toHaveTextContent('Centre: SU 3728 1551');
  });

  it('Find place on a phone explains the HTTP limit and offers place, postcode, grid entry and the packs', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Find place/ }));
    expect(screen.getByText(/GPS is blocked over HTTP/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Phone map packs/ })).toHaveAttribute('href', '/maps/packs/index.html');
    await user.type(screen.getByLabelText('Place, postcode or grid reference'), 'SU 3728 1551');
    await user.click(screen.getByRole('button', { name: 'Go to grid reference SU 3728 1551' }));
    const call = lastMap().flyTo.mock.calls.at(-1)![0] as { center: [number, number]; zoom: number };
    expect(Math.abs(call.center[0] - -1.4708)).toBeLessThan(0.001);
    expect(Math.abs(call.center[1] - 50.9379)).toBeLessThan(0.001);
  });

  it('Find place on the kiosk offers the device position and flies to it', async () => {
    mockApis();
    Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });
    const getCurrentPosition = vi.fn((ok: (p: { coords: { latitude: number; longitude: number } }) => void) => ok({ coords: { latitude: 51.5, longitude: -0.12 } }));
    Object.defineProperty(navigator, 'geolocation', { value: { getCurrentPosition }, configurable: true });
    const user = userEvent.setup();
    renderRoute('/map', { kiosk: true });
    await user.click(await screen.findByRole('button', { name: /Find place/ }));
    await user.click(screen.getByRole('button', { name: /Locate me/ }));
    expect(getCurrentPosition).toHaveBeenCalled();
    expect(lastMap().flyTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: [-0.12, 51.5] }));
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true });
  });

  it('place search flies to a place', async () => {
    // Real timers, not fake ones: userEvent's click/type simulation hangs indefinitely under
    // vi.useFakeTimers() in this environment (reproduced with a bare <button>, unrelated to this
    // screen), so the 250ms debounce is awaited for real via waitFor instead of advanced.
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map');
    await act(async () => {});
    await user.click(screen.getByRole('button', { name: /Find place/ }));
    await user.type(screen.getByLabelText('Place, postcode or grid reference'), 'oxf');
    await waitFor(() => expect(api.places).toHaveBeenCalledWith('oxf', 10));
    await user.click(await screen.findByRole('button', { name: /Oxford/ }));
    expect(lastMap().flyTo).toHaveBeenLastCalledWith(expect.objectContaining({ center: [-1.2577, 51.752], zoom: 13 }));
  });

  it('pins: lists saved pins, drops one at the centre, deletes one', async () => {
    mockApis();
    const list = notes.filter((n) => n.kind === 'pin');
    vi.spyOn(api, 'notes').mockImplementation(async () => list);
    const create = vi.spyOn(api, 'createNote').mockImplementation(async (n) => {
      const note = { id: 9, kind: 'pin' as const, title: n.title ?? '', body: '', lat: n.lat ?? null, lon: n.lon ?? null, updated_at: '2026-09-03T12:00:00Z' };
      list.push(note);
      return note;
    });
    const del = vi.spyOn(api, 'deleteNote').mockResolvedValue({ ok: true });
    const user = userEvent.setup();
    renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Pins/ }));
    const panel = screen.getByRole('dialog', { name: 'Pins' });
    expect(within(panel).getByText('Well')).toBeInTheDocument();
    await user.click(within(panel).getByRole('button', { name: 'Drop a pin at the centre' }));
    await user.type(within(panel).getByLabelText('Pin name'), 'Camp');
    await user.click(within(panel).getByRole('button', { name: 'Save pin' }));
    expect(create).toHaveBeenCalledWith({ kind: 'pin', title: 'Camp', body: '', lat: 54.5, lon: -3.5 });
    expect(await within(panel).findByText('Camp')).toBeInTheDocument();
    await user.click(within(panel).getAllByRole('button', { name: /Delete/ })[0]);
    expect(del).toHaveBeenCalledWith(2);
  });

  it('measure: two taps show distance and bearing', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Measure/ }));
    const map = lastMap();
    await act(async () => { map.emit('click', { lngLat: { lng: -0.1278, lat: 51.5074 } }); });
    await act(async () => { map.emit('click', { lngLat: { lng: 2.3522, lat: 48.8566 } }); });
    expect(screen.getByTestId('map-readout')).toHaveTextContent('343.6 km');
    expect(screen.getByTestId('map-readout')).toHaveTextContent('148° SSE');
    expect(map.getLayer('sos-measure-line')).toBeDefined();
  });

  it('hovering an overlay feature shows a tooltip that survives a base switch; tapping empty map closes a pinned one', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?overlay=health');
    await user.click(await screen.findByRole('button', { name: /Layers/ }));
    const map = lastMap();
    map.renderedFeatures = [{ id: 1, source: 'sos-overlay-health', layer: { id: 'sos-overlay-health-point' }, properties: { name: 'Southampton General Hospital', amenity: 'hospital' } }];
    await act(async () => { map.emit('mousemove', { point: { x: 40, y: 40 }, lngLat: { lng: -1.4353, lat: 50.9333 }, originalEvent: {} }); });
    const tip = screen.getByRole('tooltip');
    expect(tip).toHaveTextContent('Southampton General Hospital');
    expect(tip).toHaveTextContent('Hospitals, pharmacies, GP surgeries');
    expect(tip).toHaveTextContent('Hospital');
    expect(map.getCanvas().style.cursor).toBe('pointer');
    await act(async () => { map.emit('click', { point: { x: 40, y: 40 }, lngLat: { lng: -1.4353, lat: 50.9333 }, originalEvent: { pointerType: 'touch' } }); });
    await user.click(within(screen.getByRole('dialog', { name: 'Layers' })).getByLabelText('OS Open Zoomstack'));
    await act(async () => {});
    expect(map.style.name).toBe('/maps/styles/os-field.json');
    expect(screen.getByRole('tooltip')).toHaveTextContent('Southampton General Hospital');
    map.renderedFeatures = [];
    await act(async () => { map.emit('click', { point: { x: 300, y: 300 }, lngLat: { lng: -1.4, lat: 50.9 }, originalEvent: {} }); });
    expect(screen.queryByRole('tooltip')).toBeNull();
    expect(screen.getByTestId('map-readout')).toHaveTextContent('Tapped:');
  });

  it('share shows the address as a link and a QR; print is hidden in kiosk', async () => {
    mockApis();
    const user = userEvent.setup();
    const a = renderRoute('/map?lat=50.9379&lon=-1.4708&z=14&label=OS+HQ');
    await act(async () => {}); // let /api/status resolve so the share URL uses the hotspot IP
    await user.click(screen.getByRole('button', { name: /Share/ }));
    const url = 'http://10.42.0.1/map?lat=50.93790&lon=-1.47080&z=14&overlay=footpaths&label=OS+HQ';
    expect(screen.getByRole('link', { name: url })).toHaveAttribute('href', url);
    expect(screen.getByRole('img', { name: /QR code/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Print/ })).toBeInTheDocument();
    a.unmount();
    renderRoute('/map', { kiosk: true });
    await screen.findByRole('button', { name: /Layers/ });
    expect(screen.queryByRole('button', { name: /Print/ })).toBeNull();
  });
});
