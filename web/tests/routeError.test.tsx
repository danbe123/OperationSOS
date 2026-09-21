import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderRoute } from './render';
import { RouteError } from '../src/router';

function renderFailing(message: string) {
  renderRoute('/doc/ad-a', { routes: [
    { path: '/doc/ad-a', errorElement: <RouteError />, loader: () => { throw new Error(message); }, element: <p>never</p> },
  ] });
}

describe('the route error page', () => {
  afterEach(() => { sessionStorage.clear(); vi.restoreAllMocks(); });

  it('reloads itself once when a tab left open across an update cannot fetch a chunk', async () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, pathname: '/doc/ad-a', reload }, configurable: true });
    renderFailing('Failed to fetch dynamically imported module: /assets/Doc-abc123.js');
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(1));
    expect(screen.queryByText('Unable to open this page')).toBeNull();
  });

  it('shows the page instead of reloading again within a minute, and for any other error', async () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, pathname: '/doc/ad-a', reload }, configurable: true });
    sessionStorage.setItem('sos.autoReloadAt', String(Date.now()));   // it reloaded a moment ago: not again
    renderFailing('Failed to fetch dynamically imported module: /assets/Doc-abc123.js');
    expect(await screen.findByText('Unable to open this page')).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
    sessionStorage.clear();
    renderFailing('boom');
    expect((await screen.findAllByText('Unable to open this page')).length).toBeGreaterThan(0);
    expect(reload).not.toHaveBeenCalled();
  });
});
