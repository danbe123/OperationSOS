import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Home } from '../../src/api/types';
import { gridRef } from '../../src/map/grid';
import { FakeMap } from './fakeMap';
import { mapConfig, nearby, notes } from '../fixtures/api';

const created = vi.hoisted(() => ({ maps: [] as unknown[] }));
vi.mock('maplibre-gl', async () => {
  const { FakeMap } = await import('./fakeMap');
  class Map extends FakeMap {
    constructor(opts: { style: string; center: [number, number]; zoom: number }) {
      super();
      this.center = { lng: opts.center[0], lat: opts.center[1] };
      this.zoom = opts.zoom;
      this.setStyle(opts.style);
      created.maps.push(this);
    }
  }
  const { FakePopup } = await import('./fakeMap');
  const stub = { Map, Popup: FakePopup, NavigationControl: class {}, ScaleControl: class {}, addProtocol: vi.fn() };
  return { default: stub, ...stub };
});
vi.mock('pmtiles', () => ({ Protocol: class { tile = () => undefined; }, EtagMismatch: class extends Error {} }));

function lastMap(): FakeMap {
  return created.maps[created.maps.length - 1] as FakeMap;
}

const home: Home = { lat: 50.93, lon: -1.43, label: 'Our house', flood_zone: null };

function mockApis(opts: { home?: Home | null } = {}) {
  vi.spyOn(api, 'mapConfig').mockResolvedValue(mapConfig);
  vi.spyOn(api, 'notes').mockResolvedValue(notes.filter((n) => n.kind === 'pin'));
  vi.spyOn(api, 'home').mockResolvedValue(opts.home ?? null);
  vi.spyOn(api, 'nearby').mockResolvedValue(nearby);
}

const lead = () => document.querySelector<HTMLElement>('.map-panel-lead')!;
const body = () => document.querySelector<HTMLElement>('.map-panel-body')!;

afterEach(() => {
  created.maps.length = 0;
  document.documentElement.style.removeProperty('--panel');
});

describe('Map panels: the answer comes first', () => {
  it('leads Nearby with the nearest of the kind you need and puts the small print under the list', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14');
    await user.click(await screen.findByRole('button', { name: /Nearby/ }));
    await act(async () => {});

    // the first kind the box found something for, its nearest place and how far away it is
    expect(lead()).toHaveTextContent('Boots, High Street');
    expect(lead()).toHaveTextContent('620 m to the east, about 8 min on foot');
    // the caveat is no longer standing in front of the answer
    expect(lead()).not.toHaveTextContent(/crow flies/);
    expect(lead().compareDocumentPosition(body()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(body().lastElementChild).toHaveTextContent(/as the crow flies/);
    // and the pinned action row no longer sits over the first result
    const actions = document.querySelector<HTMLElement>('.map-panel-actions')!;
    expect(actions).toHaveTextContent('Search from this centre');
    expect(actions).not.toHaveTextContent('Boots, High Street');

    // choosing another kind moves that kind's nearest into the head
    await user.selectOptions(screen.getByLabelText('Which kind of place do you need?'), 'emergency-department');
    expect(lead()).toHaveTextContent('Southampton General Hospital');
    await user.click(within(actions).getByRole('button', { name: 'Show it on the map' }));
    expect(lastMap().flyTo).toHaveBeenCalledWith({ center: [-1.4342, 50.9331], zoom: 15 });
  });

  it('says in the head when the chosen kind is not on the box, rather than leaving it blank', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?lat=50.93&lon=-1.43&z=14');
    await user.click(await screen.findByRole('button', { name: /Nearby/ }));
    await act(async () => {});
    await user.selectOptions(screen.getByLabelText('Which kind of place do you need?'), 'rest-centre');
    expect(lead()).toHaveTextContent('No searchable copy of the emergency-services overlay on this box.');
    expect(screen.queryByRole('button', { name: 'Show it on the map' })).toBeNull();
  });

  it('names both of Home\'s grid references and pins them above the body', async () => {
    mockApis({ home });
    const user = userEvent.setup();
    renderRoute('/map?lat=54.5&lon=-3.5&z=10');
    await user.click(await screen.findByRole('button', { name: /Home/ }));
    await act(async () => {});
    expect(lead()).toHaveTextContent(`Your home: ${gridRef(50.93, -1.43).text}`);
    expect(lead()).toHaveTextContent(`The map is on: ${gridRef(54.5, -3.5).text}`);
    // round 2's promise, kept: the line that follows the map is still there, and now it is pinned
    expect(lead()).toHaveTextContent('Move the map and this line follows it.');
    expect(lead().compareDocumentPosition(body()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('gives Share one grid reference, the link as a link, and a code sized to the panel', async () => {
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?lat=54.5&lon=-3.5&z=10');
    await act(async () => {});
    await user.click(screen.getByRole('button', { name: /Share/ }));
    await act(async () => {});
    expect(lead()).toHaveTextContent(`The map is on: ${gridRef(54.5, -3.5).text}`);
    const link = within(body()).getByRole('link');
    expect(link).toHaveAttribute('href', link.textContent);
    expect(link.textContent).toContain('/map?lat=54.50000&lon=-3.50000');
    // the place is written down once: no second notation of the same point beside the link
    expect(body().textContent).not.toMatch(/Centre:/);
    expect(body().querySelector('textarea')).toBeNull();
    // jsdom gives every box a zero height, so the code lands on its floor rather than on 220:
    // the size comes from the panel, not from a number in the markup
    const code = screen.getByRole('img', { name: /QR code/ });
    expect(Number(code.getAttribute('width'))).toBe(132);
  });
});

describe('Map panels close on Escape', () => {
  it('closes the open panel when Escape is pressed', async () => {
    vi.spyOn(api, 'mapConfig').mockResolvedValue(mapConfig);
    vi.spyOn(api, 'notes').mockResolvedValue([]);
    const user = userEvent.setup();
    renderRoute('/map');
    await user.click(await screen.findByRole('button', { name: /Pins/ }));
    expect(screen.getByRole('dialog', { name: 'Pins' })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('dialog', { name: 'Pins' })).toBeNull();
  });
});

describe('The QR quiet zone', () => {
  it('frames the code in the panel colour on a dark theme and offers the bright one on request', async () => {
    document.documentElement.style.setProperty('--panel', '#121b14');
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?lat=54.5&lon=-3.5&z=10');
    await act(async () => {});
    await user.click(screen.getByRole('button', { name: /Share/ }));
    await act(async () => {});
    const frame = document.querySelector<HTMLElement>('.qr-frame')!;
    expect(frame).toHaveStyle({ background: '#121b14' });
    // the shell paints every quiet zone flat white; the code's own inline colour has to beat it
    expect(screen.getByRole('img', { name: /QR code/ })).toHaveStyle({ background: '#ffffff' });

    const brighten = screen.getByRole('button', { name: 'Make it brighter to scan' });
    expect(brighten).toHaveAttribute('aria-pressed', 'false');
    await user.click(brighten);
    await act(async () => {});
    expect(document.querySelector<HTMLElement>('.qr-frame')!).toHaveStyle({ background: '#ffffff' });
    expect(screen.getByRole('button', { name: 'Dim it again' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('leaves a light theme alone: the panel is already the quiet zone', async () => {
    document.documentElement.style.setProperty('--panel', '#ffffff');
    mockApis();
    const user = userEvent.setup();
    renderRoute('/map?lat=54.5&lon=-3.5&z=10');
    await act(async () => {});
    await user.click(screen.getByRole('button', { name: /Share/ }));
    await act(async () => {});
    expect(document.querySelector<HTMLElement>('.qr-frame')!).toHaveStyle({ background: '#ffffff' });
    expect(screen.queryByRole('button', { name: /brighter/ })).toBeNull();
  });
});
