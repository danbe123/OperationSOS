import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { cards } from '../fixtures/api';
import { splitCard } from '../../src/screens/Card';

describe('splitCard', () => {
  it('takes a card apart by its headings and gives every warning its own line', () => {
    const parts = splitCard('<h2>When to use</h2><p>Collapsed.</p><h2>Steps</h2><ol><li>One</li><li>Two</li></ol>'
      + '<h2>Warnings</h2><p><strong>Warning:</strong> A.\n<strong>Warning:</strong> B.</p><h2>Stop or escalate</h2><p>Call.</p><h2>Source</h2><p>SCMG.</p>');
    expect(parts.when).toBe('<p>Collapsed.</p>');
    expect(parts.steps).toEqual(['One', 'Two']);
    expect(parts.warnings).toBe('<p class="card-warning"><strong>Warning</strong> A.</p><p class="card-warning"><strong>Warning</strong> B.</p>');
    expect(parts.escalate).toBe('<p>Call.</p>');
    expect(parts.source).toBe('<p>SCMG.</p>');
  });
  it('keeps a card with no headings whole', () => {
    expect(splitCard('<p>Just prose.</p>')).toEqual({ when: '', steps: [], warnings: '', escalate: '', source: '', rest: '<p>Just prose.</p>' });
  });
});

describe('Card', () => {
  it('is one sheet: when to use, the steps with the first three set large, then the warnings and the escalation', async () => {
    vi.spyOn(api, 'card').mockResolvedValue(cards[0]);
    renderRoute('/medical/card/cpr-adult');
    await screen.findByRole('heading', { level: 1, name: 'CPR (adult)' });
    // Nothing to turn: no pager, no step counter.
    expect(screen.queryByRole('button', { name: /Next/ })).toBeNull();
    expect(screen.queryByText(/Step 1 of/)).toBeNull();
    expect(screen.getByText(/does not respond when you shout/)).toBeInTheDocument();
    const steps = within(screen.getByRole('list', { name: 'Steps' })).getAllByRole('listitem');
    expect(steps).toHaveLength(8);
    expect(steps[0]).toHaveTextContent('call 999');
    expect(steps.slice(0, 3).every((li) => li.classList.contains('card-step-lead'))).toBe(true);
    expect(steps.slice(3).some((li) => li.classList.contains('card-step-lead'))).toBe(false);
    expect(steps[1]).toHaveTextContent('defibrillator');
    // Each warning stands on its own line under the steps.
    expect(screen.getByText(/Broken ribs are common/).closest('p')).toHaveClass('card-warning');
    expect(screen.getByRole('region', { name: 'Stop or escalate' })).toBeInTheDocument();
  });
  it('shows an error when the card is missing', async () => {
    vi.spyOn(api, 'card').mockRejectedValue(new Error('not found'));
    renderRoute('/medical/card/nope');
    expect(await screen.findByText('Could not load this card: not found')).toBeInTheDocument();
  });
});
