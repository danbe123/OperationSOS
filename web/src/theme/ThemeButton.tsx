import { Icon } from '../icons';
import { THEMES, useTheme, type Theme } from './ThemeProvider';

const LABELS: Record<Theme, string> = { vault: 'Vault', field: 'Field', blackout: 'Blackout' };

/** The theme button is on every screen: in the rail's footer where there is a rail, and in the
 * screen head where there is not. `short` is the rail's version, which has 96 px to say it in. */
export function ThemeButton({ className, short = false }: { className?: string; short?: boolean } = {}) {
  const { theme, setTheme } = useTheme();
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  return (
    <button
      type="button"
      className={className ? `btn btn-quiet btn-small ${className}` : 'btn btn-quiet btn-small'}
      onClick={() => setTheme(next)}
      aria-label={`Theme: ${LABELS[theme]}. Switch to ${LABELS[next]}`}
    >
      <Icon name="sun" size={18} /><span>{short ? LABELS[theme] : `Theme: ${LABELS[theme]}`}</span>
    </button>
  );
}
