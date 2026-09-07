import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderRoute } from '../render';
import { Shell as Layout } from '../../src/shell/Shell';
import { Html } from '../../src/components/Html';
import { api } from '../../src/api/client';
import { scenarioMapHref } from '../../src/situation/mapLink';
import { condition, makeView, pages, playbooks, view } from '../fixtures/api';

const phonesDown = makeView({
  conditions: { mobile: condition('mobile', 'off'), landline: condition('landline', 'off') } as never,
  modes: { ...view.modes, calls: 'hidden' },
});

describe('modes: calls hidden', () => {
  it('says on the front door that 999 will not connect, and where to go instead', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    renderRoute('/');
    // With both networks down this is the most important new fact on the front door. How a phone
    // joins the box has nothing to do with the mobile network and lives on System.
    expect(await screen.findByText(/999 will not connect/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Getting help without phones' })).toHaveAttribute('href', '/p/no-phones');
  });

  it('drops the numbers line on the phone and radio screen for the no-phones route', async () => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    renderRoute('/radio');
    expect(await screen.findByText(/No number will connect/)).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Numbers to ring' })).toBeNull();
    expect(screen.getByText(/999 will not connect/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Getting help without phones' })).toHaveAttribute('href', '/p/no-phones');
  });

  it('turns tel: links in the content into the no-phones page', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    const html = '<p><a id="dial" href="tel:105">105</a></p>';
    const routes = [{ path: '/', element: <Layout />, children: [{ path: '*', element: <Html html={html} /> }] }];
    renderRoute('/p/uk-numbers', { routes });
    const link = await screen.findByRole('link', { name: /105 will not connect/ });
    expect(link).toHaveAttribute('href', '/p/no-phones');
  });

  it('leaves tel: links alone while the phones work', async () => {
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    const html = '<p><a id="dial" href="tel:105">105</a></p>';
    const routes = [{ path: '/', element: <Layout />, children: [{ path: '*', element: <Html html={html} /> }] }];
    renderRoute('/p/uk-numbers', { routes });
    expect(await screen.findByRole('link', { name: '105' })).toHaveAttribute('href', 'tel:105');
  });
});

describe('modes: map first', () => {
  it('sends a flood to the map with its flood zones already on', () => {
    expect(scenarioMapHref(null)).toBe('/map');
    expect(scenarioMapHref('grid-collapse')).toBe('/map');
    expect(scenarioMapHref('storms-flooding')).toBe('/map?overlay=flood-zones');
  });

  it('never rearranges the front door: the map is where it always is, on the rail', async () => {
    // A flood used to put an Open the map button above everything else on Now. The front door is
    // the same door in every situation now — the question, the tiles and the services — and the
    // map is one of the five destinations, on every screen.
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      scenario: { slug: 'storms-flooding', title: 'Storms and flooding', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
      modes: { ...view.modes, map_first: true },
    }));
    renderRoute('/');
    await screen.findByRole('navigation', { name: 'Scenarios' });
    expect(screen.queryByRole('link', { name: /Open the map/ })).toBeNull();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument();
  });
});
