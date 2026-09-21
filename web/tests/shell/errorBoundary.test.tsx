import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState, type ReactNode } from 'react';
import { renderRoute } from '../render';
import { routes, RouteError } from '../../src/router';
import { Shell } from '../../src/shell/Shell';
import { AppErrorBoundary } from '../../src/shell/AppErrorBoundary';
import { installGlobalErrorHandlers } from '../../src/shell/globalErrors';
import { reloadOnce, RELOAD_GUARD_MS } from '../../src/shell/reload';

/** The fault to throw, flipped by a test so that "Try again" has something to succeed at. */
const fault = { on: true };
function Bomb({ children = 'fine now' }: { children?: ReactNode }) {
  if (fault.on) throw new Error('boom from a component');
  return <p>{children}</p>;
}

function expectEmergencyNumbers(scope: HTMLElement | typeof document.body = document.body) {
  const numbers = within(scope as HTMLElement).getByRole('list', { name: 'Emergency numbers' });
  expect(numbers).toHaveTextContent('999');
  expect(numbers).toHaveTextContent('111');
  expect(numbers).toHaveTextContent('105');
}

beforeEach(() => {
  fault.on = true;
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });

describe('a screen that throws', () => {
  const screenRoutes = () => [{
    path: '/', element: <Shell />, errorElement: <RouteError />,
    children: [{ errorElement: <RouteError />, children: [{ path: 'x', element: <Bomb /> }, { index: true, element: <p>the front door</p> }] }],
  }];

  it('leaves the rail where it is, says what to do, and always shows the emergency numbers', async () => {
    renderRoute('/x', { routes: screenRoutes() });
    expect(await screen.findByText('Unable to open this page')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Sections' })).toBeInTheDocument();   // the shell is still there
    expectEmergencyNumbers();
    expect(screen.getByRole('link', { name: 'Go to Now' })).toHaveAttribute('href', '/');
  });

  it('Try again puts the screen back without reloading the page', async () => {
    const user = userEvent.setup();
    renderRoute('/x', { routes: screenRoutes() });
    await screen.findByText('Unable to open this page');
    fault.on = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('fine now')).toBeInTheDocument();
    expect(screen.queryByText('Unable to open this page')).toBeNull();
  });

  it('the app routes put screen errors below the shell, not over it', () => {
    const shell = routes[0];
    expect(shell.errorElement).toBeTruthy();
    expect(shell.children?.some((c) => c.path === undefined && c.index === undefined && c.errorElement && c.children)).toBe(true);
  });
});

describe('the shell itself throws', () => {
  it('shows the fallback with the emergency numbers and a way out', async () => {
    const user = userEvent.setup();
    function BrokenShell() {
      if (fault.on) throw new Error('the rail broke');
      return <p>shell is back</p>;
    }
    renderRoute('/', { routes: [{ path: '/', element: <BrokenShell />, errorElement: <RouteError /> }] });
    expect(await screen.findByText('Unable to open this page')).toBeInTheDocument();
    expectEmergencyNumbers();
    expect(screen.getByRole('link', { name: 'Go to Now' })).toBeInTheDocument();
    fault.on = false;
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('shell is back')).toBeInTheDocument();
  });
});

describe('the top-level boundary (providers, theme, everything above the router)', () => {
  it('catches a crash above the router, shows 999, 111 and 105 in plain text, and can try again', async () => {
    const user = userEvent.setup();
    render(<AppErrorBoundary><Bomb /></AppErrorBoundary>);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/something went wrong/i);
    expectEmergencyNumbers(alert);
    expect(within(alert).getByRole('link', { name: 'Go to Now' })).toHaveAttribute('href', '/');
    expect(console.error).toHaveBeenCalledWith(expect.stringContaining('[sos]'), expect.objectContaining({ message: 'boom from a component' }));
    fault.on = false;
    await user.click(within(alert).getByRole('button', { name: 'Try again' }));
    expect(screen.getByText('fine now')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('reloads the page by itself at most once a minute for the same fault', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, pathname: '/', reload }, configurable: true });
    const now = vi.spyOn(Date, 'now');
    now.mockReturnValue(1_000_000);
    render(<AppErrorBoundary><Bomb /></AppErrorBoundary>);
    expect(reload).toHaveBeenCalledTimes(1);
    now.mockReturnValue(1_000_000 + 30_000);
    render(<AppErrorBoundary><Bomb /></AppErrorBoundary>);
    expect(reload).toHaveBeenCalledTimes(1);   // still broken half a minute later: the fallback stays, no loop
    expect(screen.getAllByRole('alert').length).toBeGreaterThan(0);
  });
});

describe('reloadOnce', () => {
  it('reloads once a minute, not more, and never when it cannot remember that it did', () => {
    const reload = vi.fn();
    Object.defineProperty(window, 'location', { value: { ...window.location, reload }, configurable: true });
    expect(reloadOnce(5_000)).toBe(true);
    expect(reloadOnce(5_000 + RELOAD_GUARD_MS - 1)).toBe(false);
    expect(reloadOnce(5_000 + RELOAD_GUARD_MS)).toBe(true);
    expect(reload).toHaveBeenCalledTimes(2);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('denied'); });
    expect(reloadOnce(10_000_000)).toBe(false);   // no storage, no memory of the last reload: refuse rather than loop
    expect(reload).toHaveBeenCalledTimes(2);
  });
});

describe('errors that no boundary can catch', () => {
  let remove: () => void;
  afterEach(() => remove?.());

  it('an error in an event handler is logged with where it happened and the screen stays', async () => {
    remove = installGlobalErrorHandlers();
    const user = userEvent.setup();
    function Clicker() {
      const [n, setN] = useState(0);
      return (
        <div>
          <button type="button" onClick={() => { setN(n + 1); throw new Error('handler failed'); }}>Do it</button>
          <p>clicked {n}</p>
        </div>
      );
    }
    render(<Clicker />);
    await user.click(screen.getByRole('button', { name: 'Do it' }));
    expect(console.error).toHaveBeenCalledWith(expect.stringContaining('[sos] uncaught error'), expect.objectContaining({ message: 'handler failed' }));
    expect(screen.getByText('clicked 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Do it' })).toBeInTheDocument();
  });

  it('a rejected promise nobody handled is logged, left visible to the browser, and does not touch the screen', () => {
    remove = installGlobalErrorHandlers();
    render(<p>still here</p>);
    const event = new Event('unhandledrejection', { cancelable: true }) as Event & { reason: unknown };
    Object.defineProperty(event, 'reason', { value: new Error('nobody caught me') });
    act(() => { window.dispatchEvent(event); });
    expect(console.error).toHaveBeenCalledWith(expect.stringContaining('[sos] unhandled rejection'), expect.objectContaining({ message: 'nobody caught me' }));
    expect(event.defaultPrevented).toBe(false);   // still visible to the browser, and to Playwright's pageerror
    expect(screen.getByText('still here')).toBeInTheDocument();
  });

  it('a flood of the same error is logged a few times, not thousands', () => {
    remove = installGlobalErrorHandlers();
    for (let i = 0; i < 50; i++) window.dispatchEvent(new ErrorEvent('error', { message: 'again', error: new Error('again') }));
    const logged = (console.error as unknown as { mock: { calls: unknown[][] } }).mock.calls.filter((c) => String(c[0]).includes('uncaught error'));
    expect(logged.length).toBeLessThan(10);
  });
});
