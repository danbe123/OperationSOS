import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { page, rebuildSheets } from '../fixtures/api';

describe('Page', () => {
  it('renders a comms page with its table', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    renderRoute('/p/pmr446');
    expect(await screen.findByRole('heading', { name: 'PMR446 radio' })).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('446.00625 MHz')).toBeInTheDocument();
  });
  // The printed primer is a bundle of sheets, one to a side of A4; every other page is one document.
  it('prints the rebuild primer as sheets, and every other page as one document', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(rebuildSheets);
    const { container } = renderRoute('/p/rebuild-essentials-printed');
    expect(await screen.findByRole('button', { name: 'Print all sheets' })).toBeInTheDocument();
    expect(container.querySelector('.page-print-sheets')).not.toBeNull();
    expect(screen.getByText('Each sheet prints on its own side of A4.')).toBeInTheDocument();
  });

  it('keeps the plain print button on an ordinary page', async () => {
    vi.spyOn(api, 'page').mockResolvedValue(page);
    const { container } = renderRoute('/p/pmr446');
    expect(await screen.findByRole('button', { name: 'Print' })).toBeInTheDocument();
    expect(container.querySelector('.page-print-sheets')).toBeNull();
    expect(screen.queryByText('Each sheet prints on its own side of A4.')).toBeNull();
  });

  it('shows an error when the page is missing', async () => {
    vi.spyOn(api, 'page').mockRejectedValue(new Error('not found'));
    renderRoute('/p/nope');
    expect(await screen.findByText('Could not load this page: not found')).toBeInTheDocument();
  });
});
