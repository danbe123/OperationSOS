import { describe, it, expect, vi } from 'vitest';
import { useState } from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { api, ApiError } from '../../src/api/client';
import type { ChecklistItem } from '../../src/api/types';
import { Checklist, relativeTime, checklistSummary } from '../../src/components/Checklist';
import { Notices } from '../../src/components/Notice';
import { playbook } from '../fixtures/api';

function Host({ initial }: { initial: ChecklistItem[] }) {
  const [items, setItems] = useState(initial);
  return <div><Checklist slug="grid-collapse" items={items} onItems={setItems} /><Notices /></div>;
}
const NOW = Date.parse('2026-09-03T10:12:00Z');

describe('relativeTime and checklistSummary', () => {
  it('formats minutes, hours and days', () => {
    expect(relativeTime('2026-09-03T10:11:40Z', NOW)).toBe('just now');
    expect(relativeTime('2026-09-03T10:00:00Z', NOW)).toBe('12 min ago');
    expect(relativeTime('2026-09-03T07:00:00Z', NOW)).toBe('3 h ago');
    expect(relativeTime('2026-08-30T10:00:00Z', NOW)).toBe('4 days ago');
    expect(relativeTime(null, NOW)).toBe('');
  });
  it('counts done items and reports the latest change', () => {
    expect(checklistSummary(playbook.checklist, NOW)).toBe('1 of 3 done, last change 12 min ago');
    expect(checklistSummary(playbook.checklist.map((i) => ({ ...i, checked: false, updated_at: null })), NOW)).toBe('0 of 3 done');
  });
});

describe('Checklist', () => {
  it('ticks optimistically, then applies the list the server returns', async () => {
    const user = userEvent.setup();
    const returned = playbook.checklist.map((i) => (i.id === 'fill-bath' ? { ...i, checked: true, updated_at: new Date().toISOString() } : i));
    const spy = vi.spyOn(api, 'setChecklist').mockResolvedValue(returned);
    render(<Host initial={playbook.checklist} />);
    await user.click(screen.getByLabelText(/Fill the bath/));
    expect(spy).toHaveBeenCalledWith('grid-collapse', 'fill-bath', true);
    expect(screen.getByLabelText(/Fill the bath/)).toBeChecked();
    expect(screen.getByTestId('checklist-summary')).toHaveTextContent(/^2 of 3 done, last change/);
    expect(screen.getByText(/ticked just now/)).toBeInTheDocument();
  });

  it('reverts and shows a notice when the save fails', async () => {
    const user = userEvent.setup();
    vi.spyOn(api, 'setChecklist').mockRejectedValue(new ApiError(500, 'db locked'));
    render(<Host initial={playbook.checklist} />);
    await user.click(screen.getByLabelText(/Fill the bath/));
    expect(await screen.findByText(/Could not save the tick: db locked/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Fill the bath/)).not.toBeChecked();
    expect(screen.getByTestId('checklist-summary')).toHaveTextContent(/^1 of 3 done/);
  });

  it('Reset list asks for confirmation, then DELETEs and applies the cleared list', async () => {
    const user = userEvent.setup();
    const cleared = playbook.checklist.map((i) => ({ ...i, checked: false, updated_at: null }));
    const spy = vi.spyOn(api, 'resetChecklist').mockResolvedValue(cleared);
    render(<Host initial={playbook.checklist} />);
    await user.click(screen.getByRole('button', { name: 'Reset list' }));
    expect(spy).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByRole('button', { name: 'Reset list' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Reset list' }));
    await user.click(screen.getByRole('button', { name: 'Yes, reset' }));
    expect(spy).toHaveBeenCalledWith('grid-collapse');
    await act(async () => {});
    expect(screen.getByLabelText(/torches/)).not.toBeChecked();
    expect(screen.getByTestId('checklist-summary')).toHaveTextContent('0 of 3 done');
  });
});
