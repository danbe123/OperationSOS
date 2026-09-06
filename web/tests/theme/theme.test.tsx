import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme, readStoredTheme, THEME_KEY } from '../../src/theme/ThemeProvider';
import { ThemeButton } from '../../src/theme/ThemeButton';

function Probe() {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme('blackout')}>go blackout</button>
    </div>
  );
}

describe('ThemeProvider', () => {
  it('defaults to vault and stamps data-theme on <html>', () => {
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('vault');
    expect(document.documentElement.dataset.theme).toBe('vault');
  });

  it('prefers the stored theme over the fallback', () => {
    localStorage.setItem(THEME_KEY, 'field');
    render(<ThemeProvider fallback="blackout"><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('field');
  });

  it('uses the fallback (the box default) when nothing is stored, and follows it when it arrives later', () => {
    const { rerender } = render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('vault');
    rerender(<ThemeProvider fallback="blackout"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('blackout');
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
  });

  it('ignores an invalid stored value', () => {
    localStorage.setItem(THEME_KEY, 'neon');
    expect(readStoredTheme(localStorage)).toBeNull();
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('vault');
  });

  it('takes the mode theme from the engine over a stored preference, until somebody chooses', async () => {
    localStorage.setItem(THEME_KEY, 'field');
    const { rerender } = render(<ThemeProvider mode="blackout"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('blackout');
    await act(async () => { screen.getByText('go blackout').click(); });
    rerender(<ThemeProvider mode="vault"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('blackout');   // the tap wins from here on
  });

  it('dims the screen while the mode says so', () => {
    const { rerender } = render(<ThemeProvider dim><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.dim).toBe('on');
    rerender(<ThemeProvider dim={false}><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.dim).toBeUndefined();
  });

  it('setTheme persists to localStorage and re-stamps <html>', async () => {
    render(<ThemeProvider><Probe /></ThemeProvider>);
    await act(async () => { screen.getByText('go blackout').click(); });
    expect(localStorage.getItem(THEME_KEY)).toBe('blackout');
    expect(document.documentElement.dataset.theme).toBe('blackout');
  });
});

describe('ThemeButton', () => {
  it('cycles vault -> field -> blackout -> vault and names the current theme', async () => {
    const user = userEvent.setup();
    render(<ThemeProvider><ThemeButton /></ThemeProvider>);
    const button = screen.getByRole('button', { name: /vault now/i });
    await user.click(button);
    expect(screen.getByRole('button', { name: /field now/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /field now/i }));
    expect(screen.getByRole('button', { name: /blackout now/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /blackout now/i }));
    expect(screen.getByRole('button', { name: /vault now/i })).toBeInTheDocument();
    expect(localStorage.getItem(THEME_KEY)).toBe('vault');
  });
});
