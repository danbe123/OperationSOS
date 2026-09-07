import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Home, MapConfig } from '../../src/api/types';
import { FakeMap } from '../map/fakeMap';
import { mapConfig, nearby, notes } from '../fixtures/api';

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

/** The flood zones as a GeoJSON overlay that is on by default, so the layers exist to be queried. */
const withFlood: MapConfig = {
  ...mapConfig,
  overlays: mapConfig.overlays.map((o) => (o.id === 'flood-zones' ? { ...o, kind: 'geojson' as const, url: '/maps/overlays/flood.geojson', available: true, default_on: true } : o)),
};

const home: Home = { lat: 50.93, lon: -1.43, label: 'Home', flood_zone: '3' };

function mockApis(opts: { home?: Home | null; config?: MapConfig } = {}) {
  vi.spyOn(api, 'mapConfig').mockResolvedValue(opts.config ?? withFlood);
  vi.spyOn(api, 'notes').mockResolvedValue(notes.filter((n) => n.kind === 'pin'));
  vi.spyOn(api, 'home').mockResolvedValue(opts.home ?? null);
  vi.spyOn(api, 'nearby').mockResolvedValue(nearby);
}
afterEach(() => { created.maps.length = 0; });

describe('Map: home', () => {
  it('sets the centre as home with the flood zone read from the overlay under it', async () => {
    mockApis();
    const setHome = vi.spyOn(api, 'setHome').mockResolvedValue({ lat: 54.5, lon: -3.5, label: 'Our house', flood_zone: '3' });
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14&overlay=flood-zones');
    await user.click(await screen.findByRole('button', { name: /Home/ }));
    await act(async () => {});
    lastMap().renderedFeatures = [{ source: 'sos-overlay-flood-zones', layer: { id: 'sos-overlay-flood-zones-fill' }, properties: { zone: 'Flood zone 3' } }];
    const panel = screen.getByRole('dialog', { name: 'Home' });
    expect(panel).toHaveTextContent('No home set');
    await user.clear(within(panel).getByLabelText('Home name'));
    await user.type(within(panel).getByLabelText('Home name'), 'Our house');
    await user.click(within(panel).getByRole('button', { name: 'Set as home' }));
    expect(setHome).toHaveBeenCalledWith({ lat: 50.93, lon: -1.43, label: 'Our house', flood_zone: '3' });
    expect(screen.getByRole('dialog', { name: 'Home' })).toHaveTextContent('Flood zone 3');
  });

  it('records no flood zone when the overlay is not on the map', async () => {
    mockApis({ config: mapConfig });
    const setHome = vi.spyOn(api, 'setHome').mockResolvedValue({ lat: 54.5, lon: -3.5, label: 'Home', flood_zone: null });
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14');
    await user.click(await screen.findByRole('button', { name: /Home/ }));
    await act(async () => {});
    await user.click(within(screen.getByRole('dialog', { name: 'Home' })).getByRole('button', { name: 'Set as home' }));
    expect(setHome).toHaveBeenCalledWith({ lat: 50.93, lon: -1.43, label: 'Home', flood_zone: null });
    expect(screen.getByRole('dialog', { name: 'Home' })).toHaveTextContent('Turn the flood zones layer on');
  });

  it('draws the home as its own marker', async () => {
    mockApis({ home });
    renderRoute('/map');
    await screen.findByRole('group', { name: 'Map layers' });
    await act(async () => {});
    const map = lastMap();
    expect(map.getLayer('sos-home-point')).toBeDefined();
    const source = map.style.sources['sos-home'] as { data: { features: { geometry: { coordinates: number[] } }[] } };
    expect(source.data.features[0].geometry.coordinates).toEqual([-1.43, 50.93]);
  });
});

describe('Map: nearby', () => {
  it('lists the facilities for the centre with distance, walk and bearing, and pans to one', async () => {
    mockApis({ home });
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14');
    await user.click(await screen.findByRole('button', { name: /Nearby/ }));
    await act(async () => {});
    expect(api.nearby).toHaveBeenCalledWith(50.93, -1.43);
    const list = await screen.findByRole('list', { name: 'Nearby facilities' });
    const items = [...list.querySelectorAll<HTMLElement>(':scope > li')];
    expect(items[0]).toHaveTextContent('Pharmacy');
    expect(items[0]).toHaveTextContent('Boots, High Street');
    expect(items[0]).toHaveTextContent('620 m to the east, about 8 min on foot');
    // the runners-up ride under the nearest, not as separate blocks
    expect(within(items[0]).getByRole('list', { name: /Other pharmacy nearby/i })).toHaveTextContent('Shirley Pharmacy');
    expect(items[1]).toHaveTextContent('Emergency department');
    const panel = screen.getByRole('dialog', { name: 'Nearby' });
    expect(panel).toHaveTextContent('Rest centre');
    expect(panel).toHaveTextContent('No searchable copy of the emergency-services overlay on this box.');
    expect(panel).toHaveTextContent(/as the crow flies/);
    expect(panel).not.toHaveTextContent(/Naismith/);
    await user.click(within(items[0]).getByRole('button', { name: /^Boots, High Street/ }));
    expect(lastMap().flyTo).toHaveBeenCalledWith({ center: [-1.4331, 50.9345], zoom: 15 });
  });

  it('draws a straight line from home with the bearing and the Naismith time', async () => {
    mockApis({ home });
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14');
    await user.click(await screen.findByRole('button', { name: /Nearby/ }));
    await act(async () => {});
    const list = await screen.findByRole('list', { name: 'Nearby facilities' });
    const items = [...list.querySelectorAll<HTMLElement>(':scope > li')];
    await user.click(within(items[1]).getByRole('button', { name: /Line to Southampton General Hospital/ }));
    const readout = screen.getByTestId('map-readout');
    expect(readout).toHaveTextContent('Southampton General Hospital');
    expect(readout).toHaveTextContent('from home');
    expect(readout).toHaveTextContent(/bearing \d{3}°/);
    expect(readout).toHaveTextContent(/on foot/);
    await act(async () => {});
    const map = lastMap();
    const source = map.style.sources['sos-route'] as { data: { features: { geometry: { coordinates: number[][] } }[] } };
    expect(source.data.features[0].geometry.coordinates).toEqual([[-1.43, 50.93], [-1.4342, 50.9331]]);
    await user.click(screen.getByRole('button', { name: 'Clear the line' }));
    expect(screen.getByTestId('map-readout')).not.toHaveTextContent('Southampton');
  });
});
