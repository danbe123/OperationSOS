import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useLocation } from 'react-router';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { Shell as Layout } from '../../src/shell/Shell';
import { SearchBar, SEARCH_MAX_CHARS, SUGGEST_DEBOUNCE_MS } from '../../src/components/SearchBar';
import { suggestions } from '../fixtures/api';

function Where() {
  const loc = useLocation();
  return <span data-testid="where">{loc.pathname}{loc.search}</span>;
}
const routes = [{ element: <Layout />, children: [{ path: '*', element: <div><SearchBar /><Where /></div> }] }];

function setup() {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  const suggest = vi.spyOn(api, 'suggest').mockResolvedValue(suggestions);
  renderRoute('/', { routes });
  return { user, suggest };
}
afterEach(() => vi.useRealTimers());

describe('SearchBar', () => {
  it('debounces suggestions and lists them', async () => {
    const { user, suggest } = setup();
    await user.type(screen.getByRole('combobox', { name: 'Search' }), 'wat');
    expect(suggest).not.toHaveBeenCalled();
    await act(async () => { vi.advanceTimersByTime(SUGGEST_DEBOUNCE_MS); });
    expect(suggest).toHaveBeenCalledTimes(1);
    expect(suggest.mock.calls[0][0]).toBe('wat');
    expect(screen.getAllByRole('option')).toHaveLength(3);
  });

  it('picking a suggestion with a url follows it; without a url it searches', async () => {
    const { user } = setup();
    await user.type(screen.getByRole('combobox', { name: 'Search' }), 'wat');
    await act(async () => { vi.advanceTimersByTime(SUGGEST_DEBOUNCE_MS); });
    await user.click(screen.getByRole('option', { name: /Water disinfection/ }));
    expect(screen.getByTestId('where')).toHaveTextContent('/p/water-disinfection');
    await user.clear(screen.getByRole('combobox', { name: 'Search' }));
    await user.type(screen.getByRole('combobox', { name: 'Search' }), 'wat');
    await act(async () => { vi.advanceTimersByTime(SUGGEST_DEBOUNCE_MS); });
    await user.click(screen.getByRole('option', { name: /water purification/ }));
    expect(screen.getByTestId('where')).toHaveTextContent('/search?q=water%20purification');
  });

  it('Enter submits to /search?q=', async () => {
    const { user } = setup();
    await user.type(screen.getByRole('combobox', { name: 'Search' }), "st john's{Enter}");
    expect(screen.getByTestId('where')).toHaveTextContent("/search?q=st%20john's");
  });

  it('stops at the length the server accepts rather than sending a query it will refuse', async () => {
    const { user } = setup();
    const box = screen.getByRole('combobox', { name: 'Search' });
    expect(SEARCH_MAX_CHARS).toBe(512);
    expect(box).toHaveAttribute('maxlength', '512');
    await user.click(box);
    await user.paste('a'.repeat(SEARCH_MAX_CHARS + 88));
    expect(box).toHaveValue('a'.repeat(SEARCH_MAX_CHARS));
  });

  it('does not query for a single character', async () => {
    const { user, suggest } = setup();
    await user.type(screen.getByRole('combobox', { name: 'Search' }), 'w');
    await act(async () => { vi.advanceTimersByTime(SUGGEST_DEBOUNCE_MS * 2); });
    expect(suggest).not.toHaveBeenCalled();
  });
});
