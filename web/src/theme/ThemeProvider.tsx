import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import './themes.css';

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

export function ThemeProvider({ fallback, children }: { fallback?: Theme; children: ReactNode }) {
  const [stored, setStored] = useState<Theme | null>(() => readStoredTheme(localStorage));
  const theme: Theme = stored ?? fallback ?? 'vault';

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    try {
      localStorage.setItem(THEME_KEY, t);
    } catch {
      // storage may be unavailable (private mode); the in-memory value still applies
    }
    setStored(t);
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
