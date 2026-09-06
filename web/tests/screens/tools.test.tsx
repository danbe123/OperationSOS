import { describe, it, expect, vi } from 'vitest';
import { screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { library, notes } from '../fixtures/api';
import { resetTimers } from '../../src/tools/timerStore';

describe('Tools', () => {
  it('lists the seven tools', async () => {
    renderRoute('/tools');
    const nav = await screen.findByRole('navigation', { name: 'Tools' });
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/fieldcraft', '/tools/timers', '/tools/sun', '/tools/calc', '/tools/log', '/medical/dose', '/plan#stock']);
  });
});

describe('Timers', () => {
  it('starts, counts down and clears a boil timer', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      renderRoute('/tools/timers');
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      await user.click(await screen.findByRole('button', { name: 'Boil water' }));
      const running = screen.getByRole('list', { name: 'Running timers' });
      expect(within(running).getByText('1:00')).toBeInTheDocument();
      await act(async () => { await vi.advanceTimersByTimeAsync(61_000); });
      expect(within(running).getByText('No timer running.')).toBeInTheDocument();
    } finally {
      resetTimers();
      vi.useRealTimers();
    }
  });
  it('counts CPR compressions from the start button', async () => {
    renderRoute('/tools/timers');
    const user = userEvent.setup();
    await user.click(await screen.findByRole('button', { name: 'Start the beat' }));
    expect(screen.getByLabelText('Compressions so far')).toHaveTextContent('0');
    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
    expect(screen.getByRole('table', { name: 'Fallout marks' })).toHaveTextContent('1/10 of the 1-hour rate');
  });
});

describe('Sun and moon', () => {
  it('uses the last pin and shows sun times and the moon phase for a chosen date', async () => {
    vi.spyOn(api, 'notes').mockResolvedValue(notes.filter((n) => n.kind === 'pin'));
    renderRoute('/tools/sun');
    expect(await screen.findByText(/Pin: Well/)).toBeInTheDocument();
    const user = userEvent.setup();
    const date = screen.getByLabelText('Date');
    await user.clear(date);
    await user.type(date, '2026-06-21');
    const sun = screen.getByRole('region', { name: 'Sun' });
    expect(within(sun).getByText(/16 h \d\d min/)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Moon' })).toHaveTextContent(/moon|quarter|crescent|gibbous/i);
    await user.click(screen.getByRole('button', { name: 'Next day' }));
    expect(date).toHaveValue('2026-06-22');
  });
});

describe('Calculators', () => {
  it('computes from the defaults and refuses zero', async () => {
    renderRoute('/tools/calc');
    expect(await screen.findByRole('region', { name: 'Generator runtime' })).toHaveTextContent('About 17 h of running.');
    expect(screen.getByRole('region', { name: 'Battery hours' })).toHaveTextContent('About 14 h through an inverter');
    expect(screen.getByRole('region', { name: 'Solar yield' })).toHaveTextContent(/Roughly \d+ to \d+ Wh a day/);
    expect(screen.getByRole('region', { name: 'Rationing' })).toHaveTextContent('4.0 days.');
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText('People'));
    expect(screen.getByRole('region', { name: 'Rationing' })).toHaveTextContent('Enter numbers above zero.');
  });
});

describe("Children's doses", () => {
  it('reads the NHS bands, refuses under-age, and cites the installed NHS book', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/medical/dose');
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText('Years'), '0');
    await user.clear(screen.getByLabelText('Months'));
    await user.type(screen.getByLabelText('Months'), '8');
    const result = screen.getByRole('region', { name: 'Dose' });
    expect(result).toHaveTextContent('5ml');
    expect(result).toHaveTextContent('At most 4 doses in 24 hours.');
    expect(within(result).getByRole('link', { name: /Paracetamol for children/ })).toHaveAttribute('href', expect.stringMatching(/^\/read\/nhs_(uk|medicines)\/www\.nhs\.uk\/medicines\/paracetamol-for-children\/$/));
    await user.click(screen.getByRole('button', { name: 'Ibuprofen' }));
    await user.clear(screen.getByLabelText('Months'));
    await user.type(screen.getByLabelText('Months'), '2');
    expect(result).toHaveTextContent(/not given under 3 months/);
  });
});

describe('Field craft', () => {
  it('lists the fieldcraft pages in order', async () => {
    const { pages } = await import('../fixtures/api');
    vi.spyOn(api, 'pages').mockResolvedValue([
      ...pages.filter((p) => p.category !== 'fieldcraft'),
      { slug: 'fieldcraft-fire', title: 'Fire in a wet country', icon: 'fire', order: 15, html: '', category: 'fieldcraft', summary: 'Fire' },
      { slug: 'fieldcraft-basics', title: 'Field craft in Britain', icon: 'shield', order: 13, html: '', category: 'fieldcraft', summary: 'Rules' },
    ]);
    renderRoute('/fieldcraft');
    const nav = await screen.findByRole('navigation', { name: 'Field craft pages' });
    expect(within(nav).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/p/fieldcraft-basics', '/p/fieldcraft-fire']);
  });
});
