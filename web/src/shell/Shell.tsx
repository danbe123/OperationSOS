import { useLayoutEffect, useRef, type RefObject } from 'react';
import { Link, Outlet, useLocation, useNavigationType } from 'react-router';
import { Notices } from '../components/Notice';
import { Icon } from '../icons';
import { IdleOverlay } from '../kiosk/IdleOverlay';
import { Keyboard } from '../kiosk/Keyboard';
import { DrillBanner } from '../situation/DrillBanner';
import { ForecastReminders } from '../situation/ForecastReminders';
import { ThemeButton } from '../theme/ThemeButton';
import { DESTINATIONS } from './destinations';
import { SituationBand } from './SituationBand';
import { useWide } from './useWide';

/** Start each new screen at the top: the app scrolls inside .content, so the browser never resets it
 * for us. Back and forward keep their position; a hash link scrolls to its anchor instead. */
export function useScrollToTop(main: RefObject<HTMLElement | null>) {
  const { pathname, hash } = useLocation();
  const type = useNavigationType();
  useLayoutEffect(() => {
    if (type === 'POP') return;
    if (hash) {
      const target = document.getElementById(hash.slice(1));
      if (target) { target.scrollIntoView(); return; }
    }
    if (main.current) main.current.scrollTop = 0;
    window.scrollTo(0, 0);
  }, [pathname, hash, type, main]);
}

/** One navigation element, drawn as a 96 px rail on the kiosk and a bottom bar on phones. The five
 * destinations are always in the same order; the app name and the box's own screens ride along on
 * the rail, where there is room for them. */
function MainNav({ pathname, wide }: { pathname: string; wide: boolean }) {
  return (
    <nav className="mainnav no-print" aria-label="Sections">
      <Link className="rail-brand" to="/" aria-label="Operation SOS: go to Now">SOS</Link>
      <div className="mainnav-list">
        {DESTINATIONS.map((d) => (
          <Link key={d.label} className="rail-dest" to={d.to} aria-current={d.match(pathname) ? 'page' : undefined}>
            <Icon name={d.icon} size={22} />
            <span>{d.label}</span>
          </Link>
        ))}
      </div>
      {wide && (
        <div className="rail-foot">
          <Link className="rail-dest" to="/ai" aria-current={pathname === '/ai' ? 'page' : undefined}><Icon name="ai" size={20} /><span>AI</span></Link>
          <Link className="rail-dest" to="/system" aria-current={pathname === '/system' ? 'page' : undefined}><Icon name="settings" size={20} /><span>System</span></Link>
          <ThemeButton className="rail-theme" />
        </div>
      )}
    </nav>
  );
}

export function Shell() {
  const main = useRef<HTMLElement>(null);
  const { pathname } = useLocation();
  const wide = useWide();
  useScrollToTop(main);
  return (
    <div className="app">
      <div className="app-drill"><DrillBanner /></div>
      <MainNav pathname={pathname} wide={wide} />
      <div className="app-main">
        <SituationBand />
        <main className="content" ref={main}>
          <Outlet />
        </main>
      </div>
      <Notices />
      <ForecastReminders />
      <Keyboard />
      <IdleOverlay />
    </div>
  );
}
