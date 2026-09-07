import { describe, it, expect, vi } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { kitsResponse, playbooks, powerOffView, view } from '../fixtures/api';

describe('Now', () => {
  it('is the front door: the title, Start here and the box, with no app bar of its own', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/');
    // The heading is the answer, not the name of the screen: the rail already says this is Now.
    // Nothing is wrong with the services, and the box asks nobody to describe themselves first.
    expect(await screen.findByRole('heading', { level: 1, name: 'Everything is working' })).toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe('Everything is working · SOS'));
    // no Back on the front door
    expect(screen.queryByRole('button', { name: /Back/ })).toBeNull();
    // Nothing about a register, a cupboard or a score: the box counts the ticks it already has.
    expect(screen.queryByRole('region', { name: 'Household and stock' })).toBeNull();
    expect(screen.queryByRole('region', { name: 'How ready you are' })).toBeNull();
    // The front door says how a phone joins the box and nothing else about the machine: the address,
    // the drive's free space and the chip's temperature are on System.
    const box = await screen.findByTestId('status-strip');
    expect(box).toHaveTextContent('Phones join it over its own Wi-Fi, SOS.');
    expect(box).not.toHaveTextContent('http://sos.box');
    expect(box).not.toHaveTextContent('CPU');
  });

  it('/now is the same screen as /', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/now');
    expect(await screen.findByRole('heading', { level: 1, name: 'Everything is working' })).toBeInTheDocument();
  });

  it('says where to start in peacetime: the kit ticks so far, a drill and the guides', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'kits').mockResolvedValue(kitsResponse);
    renderRoute('/');
    const panel = await screen.findByRole('region', { name: 'Start here' });
    expect(panel).toHaveTextContent('Start here');
    // One line, from the basic tier of every kit added up: 1 of 2 on Water, 0 of 1 on Baby and child.
    const kits = await within(panel).findByRole('link', { name: 'Kits: 1 of 3 basic items ticked' });
    expect(kits).toHaveAttribute('href', '/kit');
    expect(within(panel).getByRole('link', { name: /Practise a drill/ })).toHaveAttribute('href', '/situation#drill');
    expect(within(panel).getByRole('link', { name: /Read the guides/ })).toHaveAttribute('href', '/guides');
    expect(within(panel).getByRole('link', { name: /Notes and pins/ })).toHaveAttribute('href', '/notes');
    // No score, no points, and nothing to fill in before the box is any use.
    expect(panel).not.toHaveTextContent('out of 100');
    expect(panel).not.toHaveTextContent('points');
    expect(panel).not.toHaveTextContent('register');
    expect(screen.queryByRole('region', { name: 'Right now' })).toBeNull();
  });

  it('still says where to start when the kits cannot be counted', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    vi.spyOn(api, 'kits').mockRejectedValue(new Error('boom'));
    renderRoute('/');
    const panel = await screen.findByRole('region', { name: 'Start here' });
    expect(await within(panel).findByText(/Kits unavailable: boom/)).toBeInTheDocument();
    expect(within(panel).getByRole('link', { name: /Practise a drill/ })).toBeInTheDocument();
  });

  it('leads with what to do once something is off', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'situationView').mockResolvedValue(powerOffView);
    renderRoute('/');
    const now = await screen.findByRole('region', { name: 'Right now' });
    expect(await screen.findByRole('heading', { level: 1, name: 'Power off, mobile patchy' })).toBeInTheDocument();
    expect(within(now).getAllByRole('listitem')).toHaveLength(3);
    expect(within(now).getByRole('link', { name: /All of them/ })).toHaveAttribute('href', '/tasks');
    expect(screen.queryByRole('region', { name: 'Start here' })).toBeNull();
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
