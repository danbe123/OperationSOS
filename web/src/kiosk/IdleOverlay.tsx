import { useCallback, useEffect, useRef, useState, type SyntheticEvent } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { api } from '../api/client';
import { useStatus } from '../api/status';
import { BoardView } from '../situation/BoardView';
import { wantsBoard } from '../situation/board';
import { useSituation } from '../situation/SituationProvider';
import { useKiosk } from './KioskProvider';
import { watchActivity } from './activity';

export const IDLE_LEVEL = 10;
export const ACTIVE_LEVEL = 100;

/** Never send the kiosk Home from a quick card or a playbook's Right now tab. */
export function isProtectedRoute(pathname: string, search: string): boolean {
  if (pathname.startsWith('/medical/card/')) return true;
  if (pathname.startsWith('/s/')) {
    const tab = new URLSearchParams(search).get('tab');
    return tab === null || tab === 'right-now';
  }
  return false;
}

export function IdleOverlay() {
  const kiosk = useKiosk();
  const { status } = useStatus();
  const { view } = useSituation();
  const navigate = useNavigate();
  const location = useLocation();
  const idleMs = (status?.idle_minutes ?? 5) * 60_000;
  const homeMs = (status?.home_minutes ?? 30) * 60_000;
  const [dimmed, setDimmed] = useState(false);
  const [fallback, setFallback] = useState(false);
  const dimmedRef = useRef(false);
  dimmedRef.current = dimmed;
  // While something is off (or the engine asks for the board) the idle screen becomes the board:
  // a household mid-outage needs the kiosk to say something, not to go dark.
  const board = wantsBoard(view);
  const boardRef = useRef(board);
  boardRef.current = board;
  const locRef = useRef(location);
  locRef.current = location;
  const idleTimer = useRef<number | undefined>(undefined);
  const homeTimer = useRef<number | undefined>(undefined);

  const dim = useCallback(async () => {
    setDimmed(true);
    if (boardRef.current) {
      // the board is meant to be read from across the room: leave the backlight where it is
      await api.kioskIdle('idle').catch(() => undefined);
      return;
    }
    try {
      await api.kioskBacklight(IDLE_LEVEL);
      setFallback(false);
    } catch {
      setFallback(true); // 501: no backlight device; draw a darker overlay instead
    }
    await api.kioskIdle('idle').catch(() => undefined);
  }, []);

  const goHome = useCallback(() => {
    const l = locRef.current;
    if (!isProtectedRoute(l.pathname, l.search)) navigate('/');
  }, [navigate]);

  const arm = useCallback(() => {
    window.clearTimeout(idleTimer.current);
    window.clearTimeout(homeTimer.current);
    idleTimer.current = window.setTimeout(() => void dim(), idleMs);
    homeTimer.current = window.setTimeout(goHome, homeMs);
  }, [dim, goHome, idleMs, homeMs]);

  useEffect(() => {
    if (!kiosk) return;
    arm();
    const onActivity = () => {
      if (!dimmedRef.current) arm();
    };
    const detach = watchActivity(document, onActivity);
    return () => {
      detach();
      window.clearTimeout(idleTimer.current);
      window.clearTimeout(homeTimer.current);
    };
  }, [kiosk, arm]);

  // Wake on click (the last event of a tap) so the whole pointerdown/up/click sequence lands on the overlay and nothing reaches the page.
  const wake = (e: SyntheticEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDimmed(false);
    void api.kioskBacklight(ACTIVE_LEVEL).catch(() => undefined);
    void api.kioskIdle('active').catch(() => undefined);
    arm();
  };

  if (!kiosk || !dimmed) return null;
  if (board) {
    return (
      <div
        className="idle-board"
        role="button"
        tabIndex={0}
        aria-label="Board: touch to wake"
        onPointerDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onClick={wake}
        onKeyDown={wake}
      >
        <BoardView />
      </div>
    );
  }
  return (
    <div
      className={fallback ? 'idle-overlay idle-overlay-dark' : 'idle-overlay'}
      role="button"
      tabIndex={0}
      aria-label="Touch to wake"
      onPointerDown={(e) => { e.preventDefault(); e.stopPropagation(); }}
      onClick={wake}
      onKeyDown={wake}
    >
      <span>Touch to wake</span>
    </div>
  );
}
