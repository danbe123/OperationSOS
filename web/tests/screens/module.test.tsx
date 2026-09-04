import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';

describe('Module', () => {
  it('renders a module on its own', async () => {
    vi.spyOn(api, 'module').mockResolvedValue({ slug: 'water', title: 'Water', html: '<p>Store 3 litres per person per day.</p>' });
    renderRoute('/m/water');
    expect(await screen.findByRole('heading', { name: 'Water' })).toBeInTheDocument();
    expect(screen.getByText('Store 3 litres per person per day.')).toBeInTheDocument();
  });
});
