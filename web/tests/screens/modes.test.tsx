import { describe, it, expect, vi } from 'vitest';
import { act, screen, within } from '@testing-library/react';
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
  it('adds the no-phones link and keeps the way a phone joins the box', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    renderRoute('/');
    const box = await screen.findByTestId('status-strip');
    expect(within(box).getByRole('link', { name: /Phones down: what to do/ })).toHaveAttribute('href', '/p/no-phones');
    // Joining the box's own WiFi has nothing to do with the mobile network, so the way in stays,
    // and the address a second phone types is inside it.
    await act(async () => { within(box).getByRole('button', { name: /Connect a phone/ }).click(); });
    expect(screen.getByRole('dialog', { name: 'Connect a phone' })).toHaveTextContent('http://10.42.0.1');
  });

  it('keeps Connect-a-phone while the networks are up', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const box = await screen.findByTestId('status-strip');
    expect(within(box).getByRole('button', { name: /Connect a phone/ })).toBeInTheDocument();
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

  it('puts an Open the map button at the top of Now, carrying the flood overlay', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      scenario: { slug: 'storms-flooding', title: 'Storms and flooding', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
      modes: { ...view.modes, map_first: true },
    }));
    renderRoute('/');
    expect(await screen.findByRole('link', { name: /Open the map/ })).toHaveAttribute('href', '/map?overlay=flood-zones');
  });

  it('leaves the map button off Now when the modes do not ask for it', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    await screen.findByRole('region', { name: 'Start here' });
    expect(screen.queryByRole('link', { name: /Open the map/ })).toBeNull();
  });
});
