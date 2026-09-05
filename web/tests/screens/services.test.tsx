import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { page, playbooks, status } from '../fixtures/api';
import { ALL_ON } from '../../src/services';

describe('What is working', () => {
  it('shows five green toggles, turns one red on tap, and offers the outage reading', async () => {
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, services: ALL_ON });
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    const set = vi.spyOn(api, 'setService').mockResolvedValue({ ...ALL_ON, phones: false });
    renderRoute('/');
    const group = await screen.findByRole('group', { name: 'Services' });
    const buttons = within(group).getAllByRole('button');
    expect(buttons.map((b) => b.getAttribute('aria-label'))).toEqual(['Power: on', 'Water: on', 'Gas: on', 'Internet: on', 'Phones: on']);
    expect(buttons[0]).toHaveClass('on');
    expect(screen.queryByRole('region', { name: 'What is off' })).toBeNull();
    await userEvent.setup().click(within(group).getByRole('button', { name: 'Phones: on' }));
    expect(set).toHaveBeenCalledWith('phones', false);
    const phones = await within(group).findByRole('button', { name: 'Phones: off' });
    expect(phones).toHaveClass('off');
    const panel = screen.getByRole('region', { name: 'What is off' });
    expect(panel).toHaveTextContent('Phones are down');
    expect(within(panel).getByRole('link', { name: 'Getting help without phones' })).toHaveAttribute('href', '/p/no-phones');
  });

  it('marks the emergency numbers on a page and shows the notice when the phones are down', async () => {
    vi.spyOn(api, 'status').mockResolvedValue({ ...status, services: { ...ALL_ON, phones: false, water: false } });
    vi.spyOn(api, 'page').mockResolvedValue({ ...page, html: '<p>Call 999 now, or 111 for advice.</p>' });
    renderRoute('/p/pmr446');
    const notice = await screen.findByRole('status');
    expect(notice).toHaveTextContent('Off right now: water, phones.');
    expect(await screen.findAllByText('phones down')).toHaveLength(2);
    expect(document.querySelector('.no-phone')?.textContent).toBe('999 phones down');
  });
});
