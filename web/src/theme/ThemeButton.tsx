import { Icon } from '../icons';
import { THEME_LABELS as LABELS, THEMES, useTheme } from './ThemeProvider';

/** The theme button is on every screen: in the rail's footer where there is a rail, and among the
 * screen's own actions where there is not. One word — "Theme" — in a 20 px icon's company, so the
 * label fits the 48 px rail row instead of overflowing it by 19 px and being clipped into "Change /
 * theme" on all 177 kiosk screenshots. Which theme is on now, and which is next, stay in the
 * accessible name: the screen is already wearing the one it is asking about. */
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
      <Icon name="sun" size={20} />
      <span>Theme</span>
    </button>
  );
}
