import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { cards } from '../fixtures/api';

describe('Card', () => {
  it('renders the card title in the extra-large class and numbered steps', async () => {
    vi.spyOn(api, 'card').mockResolvedValue(cards[0]);
    renderRoute('/medical/card/cpr-adult');
    const title = await screen.findByRole('heading', { level: 1, name: 'CPR (adult)' });
    expect(title).toHaveClass('card-title');
    const steps = screen.getAllByRole('listitem');
    expect(steps).toHaveLength(4);
    expect(steps[1]).toHaveTextContent('Call 999');
    expect(steps[0].closest('.card-html')).not.toBeNull();
    expect(screen.getByText(/Do not stop until help arrives/)).toHaveClass('warning');
  });
  it('shows an error when the card is missing', async () => {
    vi.spyOn(api, 'card').mockRejectedValue(new Error('not found'));
    renderRoute('/medical/card/nope');
    expect(await screen.findByText('Could not load this card: not found')).toBeInTheDocument();
  });
});
