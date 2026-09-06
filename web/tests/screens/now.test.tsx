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
    expect(await screen.findByRole('heading', { level: 1, name: 'Now' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Now · SOS'));
    // no Back on the front door
    expect(screen.queryByRole('button', { name: /Back/ })).toBeNull();
    const household = await screen.findByRole('region', { name: 'Household and stock' });
    expect(household).toHaveTextContent('Nobody registered yet');
    expect(within(household).getByRole('list', { name: 'Days of stock left' })).toHaveTextContent('Water 1.5 days');
    expect(await screen.findByTestId('status-strip')).toHaveTextContent('http://sos.box');
  });

  it('/now is the same screen as /', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/now');
    expect(await screen.findByRole('heading', { level: 1, name: 'Now' })).toBeInTheDocument();
  });

  it('shows the readiness and its gaps in peacetime, and the drill', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    renderRoute('/');
    const panel = await screen.findByRole('region', { name: 'Situation' });
    expect(panel).toHaveTextContent('Everything is working');
    expect(within(panel).getByLabelText('Readiness')).toHaveTextContent('62');
    expect(within(panel).getByRole('link', { name: 'Water: 1.5 days for 3 people' })).toHaveAttribute('href', '/plan#stock');
    expect(within(panel).getByRole('link', { name: /Practise a drill/ })).toHaveAttribute('href', '/situation#drill');
    expect(screen.queryByRole('region', { name: 'Do this now' })).toBeNull();
  });

  it('leads with what to do once something is off', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const now = await screen.findByRole('region', { name: 'Do this now' });
    expect(within(now).getAllByRole('listitem')).toHaveLength(3);
    expect(within(now).getByRole('link', { name: /All tasks/ })).toHaveAttribute('href', '/tasks');
    expect(screen.queryByRole('region', { name: 'Situation' })).toBeNull();
    expect(await screen.findByRole('region', { name: 'Coming up' })).toHaveTextContent('Fridge food unsafe');
    expect(screen.getByRole('region', { name: 'The box thinks' })).toHaveTextContent('Mobile network is probably off');
    expect(screen.getByRole('region', { name: 'Read this' })).toHaveTextContent('Right now');
  });

  it('says so, and keeps the rest of the box, when the engine cannot be read', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockRejectedValue(new Error('boom'));
    renderRoute('/');
    expect(await screen.findByText(/The situation is unavailable: boom/)).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument();
  });
});
