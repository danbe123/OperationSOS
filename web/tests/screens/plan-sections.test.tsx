import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import type { Person } from '../../src/api/types';

const people: Person[] = [
  { id: 1, name: 'Sam', age: 7, needs: 'asthma', medications: 'salbutamol inhaler', contacts: '', updated_at: '2026-09-05T10:00:00Z' },
  { id: 2, name: 'Ali', age: null, needs: '', medications: '', contacts: 'Gran 0161 000', updated_at: '2026-09-05T10:00:00Z' },
];

describe('Medical household panel', () => {
  it('lists people with needs or medications', async () => {
    vi.spyOn(api, 'household').mockResolvedValue(people);
    renderRoute('/medical');
    const panel = await screen.findByRole('region', { name: 'Household medical needs' });
    expect(panel).toHaveTextContent('Sam');
    expect(panel).toHaveTextContent('asthma');
    expect(panel).not.toHaveTextContent('Ali');
    // The old anchor is still the address printed on fridge doors; the hub sends it to /plan/people.
    expect(within(panel).getByRole('link', { name: /Edit the register/ })).toHaveAttribute('href', '/plan#household');
  });
});
