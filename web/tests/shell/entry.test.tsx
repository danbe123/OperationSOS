import { describe, it, expect, vi, afterEach } from 'vitest';
import { screen, within } from '@testing-library/react';

/** The real app entry (src/main.tsx), not the pieces: the last-resort boundary must be mounted above the app,
 * and the window error handlers installed, or the tests of each piece prove nothing about the page. */
vi.mock('../../src/App', () => ({
  App: () => { throw new Error('the whole app broke'); },
}));

afterEach(() => {
  vi.restoreAllMocks();
  document.body.innerHTML = '';
});

describe('main.tsx', () => {
  it('mounts the error boundary above the app and installs the global error handlers', async () => {
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {});
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, pathname: '/', reload }, configurable: true });
    const root = document.createElement('div');
    root.id = 'root';
    document.body.appendChild(root);

    await import('../../src/main');

    // An app that throws while rendering ends on the fallback with the numbers, not on a white page.
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/something went wrong/i);
    expect(within(alert).getByRole('list', { name: 'Emergency numbers' })).toHaveTextContent('999');
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(logged).toHaveBeenCalledWith(expect.stringContaining('[sos] the app crashed'), expect.anything());

    // The handlers installed by main.tsx log an uncaught error with context.
    window.dispatchEvent(new ErrorEvent('error', { message: 'later', error: new Error('a later uncaught error') }));
    expect(logged).toHaveBeenCalledWith(expect.stringContaining('[sos] uncaught error'), expect.objectContaining({ message: 'a later uncaught error' }));
  });
});
