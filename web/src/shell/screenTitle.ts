import { createContext, useContext } from 'react';

/** The shell names its own `<main>` after whatever screen is inside it, so a screen reader landing
 * on the main landmark hears "Now" or "CPR (adult)" rather than "main". The screen is the only thing
 * that knows its title, and the landmark is the shell's, so the title travels up through here. */
export const ScreenTitleContext = createContext<(title: string) => void>(() => {});

export function useReportScreenTitle(): (title: string) => void {
  return useContext(ScreenTitleContext);
}
