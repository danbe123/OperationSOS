import { Icon } from '../icons';
import { THEMES, useTheme, type Theme } from './ThemeProvider';

const LABELS: Record<Theme, string> = { vault: 'Vault', field: 'Field', blackout: 'Blackout' };

/** The theme button is on every screen: in the rail's footer where there is a rail, and in the
 * screen head where there is not. It used to wear the current theme's name — "Vault", "Blackout" —
 * in the rail's own row style, which made it a sixth place to go rather than something to press.
 * It says what it does: a verb, and the current theme after it. */
export function ThemeButton({ className }: { className?: string } = {}) {
  const { theme, setTheme } = useTheme();
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  return (
    <button
      type="button"
      className={className ? `btn btn-small theme-btn ${className}` : 'btn btn-small theme-btn'}
      onClick={() => setTheme(next)}
      aria-label={`Change the theme. ${LABELS[theme]} now; next is ${LABELS[next]}`}
    >
      <Icon name="sun" size={18} />
      <span>Change theme<small>{LABELS[theme]} now</small></span>
    </button>
  );
}
