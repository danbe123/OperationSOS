import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme, readStoredTheme, THEME_KEY, THEMES } from '../../src/theme/ThemeProvider';
import { ThemeButton } from '../../src/theme/ThemeButton';

function Probe() {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme('mono')}>go mono</button>
    </div>
  );
}

describe('ThemeProvider', () => {
  it('offers exactly two themes: the light one and the black-and-white one', () => {
    expect(THEMES).toEqual(['field', 'mono']);
  });

  it('defaults to field and stamps data-theme on <html>', () => {
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('field');
    expect(document.documentElement.dataset.theme).toBe('field');
  });

  it('prefers the stored theme over the fallback', () => {
    localStorage.setItem(THEME_KEY, 'mono');
    render(<ThemeProvider fallback="field"><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('mono');
  });

  it('uses the fallback (the box default) when nothing is stored, and follows it when it arrives later', () => {
    const { rerender } = render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('field');
    rerender(<ThemeProvider fallback="mono"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('mono');
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
  });

  it('ignores an invalid stored value', () => {
    localStorage.setItem(THEME_KEY, 'blackout');
    expect(readStoredTheme(localStorage)).toBeNull();
    render(<ThemeProvider><Probe /></ThemeProvider>);
    expect(screen.getByTestId('theme')).toHaveTextContent('field');
  });

  it('takes the mode theme from the engine over a stored preference, until somebody chooses', async () => {
    localStorage.setItem(THEME_KEY, 'field');
    const { rerender } = render(<ThemeProvider mode="mono"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('mono');
    await act(async () => { screen.getByText('go mono').click(); });
    rerender(<ThemeProvider mode="field"><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.theme).toBe('mono');   // the tap wins from here on
  });

  it('dims the screen while the mode says so', () => {
    const { rerender } = render(<ThemeProvider dim><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.dim).toBe('on');
    rerender(<ThemeProvider dim={false}><Probe /></ThemeProvider>);
    expect(document.documentElement.dataset.dim).toBeUndefined();
  });

  it('setTheme persists to localStorage and re-stamps <html>', async () => {
    render(<ThemeProvider><Probe /></ThemeProvider>);
    await act(async () => { screen.getByText('go mono').click(); });
    expect(localStorage.getItem(THEME_KEY)).toBe('mono');
    expect(document.documentElement.dataset.theme).toBe('mono');
  });
});

describe('ThemeButton', () => {
  it('cycles field -> mono -> field and names the current theme', async () => {
    const user = userEvent.setup();
    render(<ThemeProvider><ThemeButton /></ThemeProvider>);
    const button = screen.getByRole('button', { name: /Field now; next is Mono/i });
    await user.click(button);
    expect(screen.getByRole('button', { name: /Mono now; next is Field/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Mono now/i }));
    expect(screen.getByRole('button', { name: /Field now/i })).toBeInTheDocument();
    expect(localStorage.getItem(THEME_KEY)).toBe('field');
  });
});
