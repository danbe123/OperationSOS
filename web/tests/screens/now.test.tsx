import { describe, it, expect, vi } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { playbooks, powerOffView, stockResponse, view } from '../fixtures/api';

describe('Now', () => {
  it('is the front door: the title, the household summary and the box, with no app bar of its own', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'stock').mockResolvedValue(stockResponse);
    vi.spyOn(api, 'household').mockResolvedValue([]);
    vi.spyOn(api, 'neighbours').mockResolvedValue([]);
    renderRoute('/');
    // The heading is the answer, not the name of the screen: the rail already says this is Now.
    expect(await screen.findByRole('heading', { level: 1, name: 'Everything is working' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Everything is working · SOS'));
    // no Back on the front door
    expect(screen.queryByRole('button', { name: /Back/ })).toBeNull();
    const household = await screen.findByRole('region', { name: 'Household and stock' });
    // Who the box counts for is said once, on this panel and nowhere else on the screen.
    expect(household).toHaveTextContent('Nobody is registered yet, so the box counts stock for one person.');
    expect(within(household).getByRole('list', { name: 'Days of stock left' })).toHaveTextContent('Water 1.5 days');
    // The front door says how a phone joins the box and nothing else about the machine: the address,
    // the drive's free space and the chip's temperature are on System.
    const box = await screen.findByTestId('status-strip');
    expect(box).toHaveTextContent('Phones join it over its own WiFi, SOS.');
    expect(box).not.toHaveTextContent('http://sos.box');
    expect(box).not.toHaveTextContent('CPU');
  });

  it('/now is the same screen as /', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/now');
    expect(await screen.findByRole('heading', { level: 1, name: 'Everything is working' })).toBeInTheDocument();
  });

  it('says how long the household would last and what would help, with no score and no points', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'stock').mockResolvedValue(stockResponse);
    vi.spyOn(api, 'household').mockResolvedValue([]);
    renderRoute('/');
    const panel = await screen.findByRole('region', { name: 'Situation' });
    // The heading above already says the state; the panel says what it is about.
    expect(panel).toHaveTextContent('How ready you are');
    // Every number on this panel comes from the engine's readiness: no second count of the same water.
    await waitFor(() => expect(panel).toHaveTextContent('One thing would help most.'));
    expect(panel).not.toHaveTextContent('You have water for');
    expect(panel).not.toHaveTextContent('out of 100');
    expect(panel).not.toHaveTextContent('points');
    expect(panel).toHaveTextContent('New box?');
    // the first-run calls to action are buttons on their own row, not 20 px underlines
    expect(within(panel).getByRole('link', { name: /Add who lives here/ })).toHaveClass('btn');
    expect(within(panel).getByRole('link', { name: /Add water, food and fuel/ })).toHaveClass('btn');
    expect(within(panel).getByRole('link', { name: 'Water: 1.5 days for 3 people' })).toHaveAttribute('href', '/plan#stock');
    expect(within(panel).getByRole('link', { name: /Practise a drill/ })).toHaveAttribute('href', '/situation#drill');
    expect(screen.queryByRole('region', { name: 'Right now' })).toBeNull();
  });

  it('leads with what to do once something is off', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const now = await screen.findByRole('region', { name: 'Right now' });
    expect(await screen.findByRole('heading', { level: 1, name: 'Power off, mobile patchy' })).toBeInTheDocument();
    expect(within(now).getAllByRole('listitem')).toHaveLength(3);
    expect(within(now).getByRole('link', { name: /All of them/ })).toHaveAttribute('href', '/tasks');
    expect(screen.queryByRole('region', { name: 'Situation' })).toBeNull();
    expect(await screen.findByRole('region', { name: 'Coming up' })).toHaveTextContent('Fridge food unsafe');
    expect(screen.getByRole('region', { name: 'The box thinks' })).toHaveTextContent('Mobile network — probably off');
    expect(screen.getByRole('region', { name: 'Read' })).toHaveTextContent('Right now');
  });

  it('says so, and keeps the rest of the box, when the engine cannot be read', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockRejectedValue(new Error('boom'));
    renderRoute('/');
    expect(await screen.findByText(/The box cannot read the situation/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Try again/ })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument();
  });
});
