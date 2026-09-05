import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from './render';
import { api } from '../src/api/client';
import { playbooks } from './fixtures/api';

describe('scroll to top on navigation', () => {
  it('resets the main container when a link opens a new screen', async () => {
    vi.spyOn(api, 'playbooks').mockResolvedValue(playbooks);
    vi.spyOn(api, 'pages').mockResolvedValue([]);
    renderRoute('/');
    const main = document.querySelector('.layout-main') as HTMLElement;
    await screen.findByRole('navigation', { name: 'Main sections' });
    main.scrollTop = 400;
    await userEvent.setup().click(screen.getByRole('link', { name: /Tools/ }));
    await screen.findByRole('navigation', { name: 'Tools' });
    expect(main.scrollTop).toBe(0);
  });
});
