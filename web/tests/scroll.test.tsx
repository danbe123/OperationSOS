import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from './render';
import { api } from '../src/api/client';
import { playbook, playbooks, view } from './fixtures/api';

describe('scroll to top on navigation', () => {
  it('resets the main container when a link opens a new screen', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'pages').mockResolvedValue([]);
    vi.spyOn(api, 'playbook').mockResolvedValue(playbook);
    vi.spyOn(api, 'situation').mockResolvedValue({ slug: null });
    vi.spyOn(api, 'situationView').mockResolvedValue(view);
    // The scenario tiles are the front door now, so the navigation this measures starts there.
    renderRoute('/');
    const main = document.querySelector('.content') as HTMLElement;
    await screen.findByRole('navigation', { name: 'Scenarios' });
    main.scrollTop = 400;
    await userEvent.setup().click(screen.getByRole('link', { name: /National grid collapse/ }));
    await screen.findByRole('heading', { level: 1, name: 'National grid collapse' });
    expect(main.scrollTop).toBe(0);
  });
});
