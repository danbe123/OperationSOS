import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from 'react';

/** Two themes and no more: Field, paper and ink, and Mono, white on pure black with no hue in it.
 * Field is the box default, so an unstamped document (and the bare `:root` in tokens.css) is light. */
export type Theme = 'field' | 'mono';
export const THEMES: readonly Theme[] = ['field', 'mono'] as const;
export const THEME_KEY = 'sos.theme';
/** The names a person sees. The ids are what is stored, posted and stamped on <html>. */
export const THEME_LABELS: Record<Theme, string> = { field: 'Field', mono: 'Mono' };

export function isTheme(value: unknown): value is Theme {
  return typeof value === 'string' && (THEMES as readonly string[]).includes(value);
}

export function readStoredTheme(storage: Storage): Theme | null {
  try {
    const v = storage.getItem(THEME_KEY);
    return isTheme(v) ? v : null;
  } catch {
    return null;
  }
}

type ThemeContextValue = { theme: Theme; setTheme: (t: Theme) => void };
const ThemeContext = createContext<ThemeContextValue | null>(null);

/** `mode` and `dim` come from the engine's modes (mono in a night-time power cut, say). A mode
 * outranks the stored preference while it lasts, but a deliberate tap on the theme button outranks it. */
export function ThemeProvider({ fallback, mode = null, dim = false, children }: { fallback?: Theme; mode?: Theme | null; dim?: boolean; children: ReactNode }) {
  const [stored, setStored] = useState<Theme | null>(() => readStoredTheme(localStorage));
  const [chosen, setChosen] = useState<Theme | null>(null);
  const theme: Theme = chosen ?? mode ?? stored ?? fallback ?? 'field';

  // Stamped in layout effects, which run before any screen's ordinary effects: the book reader, the
  // PDF viewer and the article reader read the palette off the root when the theme changes, and a
  // child's effect runs before its parent's, so with a plain effect here they read the palette the
  // theme had just left ("if i change theme on a book the page doesnt change with the theme").
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useLayoutEffect(() => {
    if (dim) document.documentElement.dataset.dim = 'on';
    else delete document.documentElement.dataset.dim;
  }, [dim]);

  const setTheme = useCallback((t: Theme) => {
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      // storage may be unavailable (private mode); the in-memory value still applies
    }
    setStored(t);
    setChosen(t);
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
