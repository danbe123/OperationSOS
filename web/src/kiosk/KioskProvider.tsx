import { createContext, useContext, useEffect, useMemo, type ReactNode } from 'react';

export const KIOSK_KEY = 'sos.kiosk';

/** `?kiosk=1` on the launch URL turns kiosk mode on for the browser session. */
export function detectKiosk(search: string, storage: Storage): boolean {
  try {
    if (new URLSearchParams(search).get('kiosk') === '1') {
      storage.setItem(KIOSK_KEY, '1');
      return true;
    }
    return storage.getItem(KIOSK_KEY) === '1';
  } catch {
    return false;
  }
}

const KioskContext = createContext(false);

export function KioskProvider({ children, force }: { children: ReactNode; force?: boolean }) {
  const kiosk = useMemo(() => force ?? detectKiosk(window.location.search, sessionStorage), [force]);
  useEffect(() => {
    document.documentElement.classList.toggle('kiosk', kiosk);
  }, [kiosk]);
  return <KioskContext.Provider value={kiosk}>{children}</KioskContext.Provider>;
}

export function useKiosk(): boolean {
  return useContext(KioskContext);
}
