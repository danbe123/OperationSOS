import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { Layout } from '../../src/router';
import { Html } from '../../src/components/Html';
import { api } from '../../src/api/client';
import { homeTiles } from '../../src/screens/Home';
import { condition, makeView, pages, playbooks, view } from '../fixtures/api';

const phonesDown = makeView({
  conditions: { mobile: condition('mobile', 'off'), landline: condition('landline', 'off') } as never,
  modes: { ...view.modes, calls: 'hidden' },
});

describe('modes: calls hidden', () => {
  it('swaps the chrome Connect-a-phone for the no-phones link, and keeps the WiFi way in', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    renderRoute('/');
    const strip = await screen.findByTestId('status-strip');
    expect(within(strip).queryByRole('button', { name: /Connect a phone/ })).toBeNull();
    expect(within(strip).getByRole('link', { name: /Phones down: what to do/ })).toHaveAttribute('href', '/p/no-phones');
    expect(strip).toHaveTextContent('http://10.42.0.1');
  });

  it('keeps Connect-a-phone while the networks are up', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const strip = await screen.findByTestId('status-strip');
    expect(within(strip).getByRole('button', { name: /Connect a phone/ })).toBeInTheDocument();
  });

  it('drops the numbers line on the phone and radio screen for the no-phones route', async () => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'situationView').mockResolvedValue(phonesDown);
    renderRoute('/radio');
    expect(await screen.findByText(/No number will connect/)).toBeInTheDocument();
    expect(screen.queryByText(/Emergency 999/)).toBeNull();
    expect(screen.getByRole('link', { name: 'getting help without phones' })).toHaveAttribute('href', '/p/no-phones');
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
  it('leads with the map and opens the flood zones for a flood', () => {
    expect(homeTiles(false).map((t) => t.to)[0]).toBe('/medical');
    expect(homeTiles(true).map((t) => t.to)[0]).toBe('/map');
    const flood = homeTiles(true, 'storms-flooding');
    expect(flood[0].to).toBe('/map?overlay=flood-zones');
    expect(flood[0].subtitle).toContain('flood zones');
    expect(homeTiles(false, 'grid-collapse')[1].to).toBe('/map');
  });

  it('carries the flood overlay onto Home', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(makeView({
      scenario: { slug: 'storms-flooding', title: 'Storms and flooding', started_at: '2026-09-06T12:00:00.000Z', elapsed_s: 7200, phase: 'right-now' },
      modes: { ...view.modes, map_first: true },
    }));
    renderRoute('/');
    const tools = await screen.findByRole('navigation', { name: 'Main sections' });
    expect(within(tools).getAllByRole('link')[0]).toHaveAttribute('href', '/map?overlay=flood-zones');
  });
});
