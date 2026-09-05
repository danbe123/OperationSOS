import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

export type Theme = 'vault' | 'field' | 'blackout';
export const THEMES: readonly Theme[] = ['vault', 'field', 'blackout'] as const;
export const THEME_KEY = 'sos.theme';

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

/** `mode` and `dim` come from the engine's modes (blackout in a night-time power cut, say). A mode
 * outranks the stored preference while it lasts, but a deliberate tap on the theme button outranks it. */
export function ThemeProvider({ fallback, mode = null, dim = false, children }: { fallback?: Theme; mode?: Theme | null; dim?: boolean; children: ReactNode }) {
  const [stored, setStored] = useState<Theme | null>(() => readStoredTheme(localStorage));
  const [chosen, setChosen] = useState<Theme | null>(null);
  const theme: Theme = chosen ?? mode ?? stored ?? fallback ?? 'vault';

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
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
