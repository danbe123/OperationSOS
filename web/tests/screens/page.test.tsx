import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { page } from '../fixtures/api';

describe('Page', () => {
  it('renders a comms page with its table', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { name: 'PMR446 radio' })).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('446.00625 MHz')).toBeInTheDocument();
  });
  it('shows an error when the page is missing', async () => {
    vi.spyOn(api, 'page').mockRejectedValue(new Error('not found'));
    renderRoute('/p/nope');
    expect(await screen.findByText('Could not load this page: not found')).toBeInTheDocument();
  });
});
