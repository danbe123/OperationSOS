import { Icon } from '../icons';
import { THEMES, useTheme, type Theme } from './ThemeProvider';

const LABELS: Record<Theme, string> = { vault: 'Vault', field: 'Field', blackout: 'Blackout' };

export function ThemeButton({ className }: { className?: string } = {}) {
  const { theme, setTheme } = useTheme();
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  return (
    <button
      type="button"
      className={className ? `btn btn-quiet btn-small ${className}` : 'btn btn-quiet btn-small'}
      onClick={() => setTheme(next)}
      aria-label={`Theme: ${LABELS[theme]}. Switch to ${LABELS[next]}`}
    >
      <Icon name="sun" size={18} /><span>Theme: {LABELS[theme]}</span>
    </button>
  );
}
