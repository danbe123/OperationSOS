import { THEMES, useTheme, type Theme } from './ThemeProvider';

const LABELS: Record<Theme, string> = { vault: 'Vault', field: 'Field', blackout: 'Blackout' };

export function ThemeButton() {
  const { theme, setTheme } = useTheme();
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  return (
    <button type="button" className="btn btn-chrome" onClick={() => setTheme(next)} title={`Switch to ${LABELS[next]}`}>
      Theme: {LABELS[theme]}
    </button>
  );
}
