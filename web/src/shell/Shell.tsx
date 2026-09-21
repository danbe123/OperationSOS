import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react';
import { Link, Outlet, useLocation, useNavigationType } from 'react-router';
import { Notices } from '../components/Notice';
import { Reconnecting } from '../components/Reconnecting';
import { Icon } from '../icons';
import { IdleOverlay } from '../kiosk/IdleOverlay';
import { KeyboardMount } from '../kiosk/KeyboardMount';
import { DrillBanner } from '../situation/DrillBanner';
import { ForecastReminders } from '../situation/ForecastReminders';
import { ThemeButton } from '../theme/ThemeButton';
import { DESTINATIONS } from './destinations';
import { ScreenTitleContext } from './screenTitle';
import { SituationBand } from './SituationBand';
import { ColdStartContext, rememberPlace } from './lastPlace';
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

/** Whether the content column has more below the fold, so the shell can say so. The kiosk has no
 * scrollbar and no bounce: a 423 px window on a 2,964 px screen looked exactly like a screen that
 * ended, and the first job the household still had to do was under the edge. */
export function useScrollCue(main: RefObject<HTMLElement | null>): boolean {
  const [more, setMore] = useState(false);
  useLayoutEffect(() => {
    const el = main.current;
    if (!el) return;
    const check = () => setMore(el.scrollTop + el.clientHeight < el.scrollHeight - 1);
    check();
    el.addEventListener('scroll', check, { passive: true });
    window.addEventListener('resize', check);
    const observer = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(check);
    observer?.observe(el);
    if (el.firstElementChild) observer?.observe(el.firstElementChild);
    return () => {
      el.removeEventListener('scroll', check);
      window.removeEventListener('resize', check);
      observer?.disconnect();
    };
  }, [main]);
  return more;
}

/** One navigation element, drawn as a 96 px rail on the kiosk and a bottom bar on phones. The five
 * destinations are always in the same order; the app name and the box's own screens ride along on
 * the rail, where there is room for them. It is drawn first and read last: the shell puts it after
 * the content in the DOM (the grid puts it back on the left) so a keyboard reaches the first job
 * before it reaches eight links to somewhere else. */
function MainNav({ pathname, wide }: { pathname: string; wide: boolean }) {
  return (
    <nav className="mainnav no-print" aria-label="Sections">
      {/* No wordmark: it went where Now already goes, and the owner had it removed ("remove SOS off
          the left nav"). The five destinations start at the top of the rail. */}
      <div className="mainnav-list">
        {DESTINATIONS.map((d) => (
          <Link key={d.label} className="rail-dest" to={d.to} aria-current={d.match(pathname) ? 'page' : undefined}>
            <Icon name={d.icon} size={20} />
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
  const [title, setTitle] = useState('Operation SOS');
  const report = useCallback((t: string) => setTitle(t), []);
  useScrollToTop(main);
  const more = useScrollCue(main);
  // Cold start: this page load has not been moved off its first location yet. Set while rendering, so a
  // Now that mounts because somebody navigated to it already sees that they did.
  const location = useLocation();
  const firstKey = useRef(location.key);
  const cold = useRef(true);
  if (location.key !== firstKey.current) cold.current = false;
  // Where somebody is working, for "Continue where you were" after the browser or the box restarts; the
  // timer keeps "how long ago" honest for somebody who reads one screen for an hour.
  const here = `${location.pathname}${location.search}`;
  useEffect(() => {
    rememberPlace(here);
    const timer = window.setInterval(() => rememberPlace(here), 5 * 60_000);
    return () => window.clearInterval(timer);
  }, [here]);
  // The board is the whole screen: it says what the band and the rail say, in type twice the size,
  // and a tap anywhere on it comes back. Furniture would only cost it lines.
  if (pathname === '/board') {
    return (
      <div className="app app-board">
        <main className="content" id="main" tabIndex={-1} aria-label="The board" ref={main}><Outlet /></main>
        <Notices />
        <Reconnecting />
        <IdleOverlay />
      </div>
    );
  }
  return (
    <ColdStartContext.Provider value={cold}>
    <ScreenTitleContext.Provider value={report}>
      <div className="app">
        {/* The first focusable thing in the box, on every screen: seventeen tab stops stood between
            a keyboard and the first job, and there was nothing to step over them with. */}
        <a className="skip-link no-print" href="#main">Skip to what to do</a>
        <div className="app-drill"><DrillBanner /></div>
        {/* The band is drawn above the content and read after it: three links about what is broken
            should not stand between a keyboard and the job the screen is for. `order` puts it back
            on top for everybody who is looking rather than tabbing. */}
        <div className="app-main" data-more={more ? 'yes' : 'no'}>
          <main className="content" id="main" tabIndex={-1} aria-label={title} ref={main}>
            <Outlet />
          </main>
          <SituationBand />
        </div>
        <MainNav pathname={pathname} wide={wide} />
        <Notices />
        <Reconnecting />
        <ForecastReminders />
        <KeyboardMount />
        <IdleOverlay />
      </div>
    </ScreenTitleContext.Provider>
    </ColdStartContext.Provider>
  );
}
