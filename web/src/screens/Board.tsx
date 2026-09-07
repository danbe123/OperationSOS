import { useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Icon } from '../icons';
import { BoardView } from '../situation/BoardView';

/** `/board`: the board, and on this screen you can work it. The whole screen used to be one button
 * back to Now, so nothing on the board could be touched — a household looking at "Gas ✓ working"
 * had no way to say it had gone off without going back and finding the front door's buttons. Back
 * is now a button of its own in the board's header, and Escape does the same. */
export function Board() {
  const navigate = useNavigate();
  const home = useCallback(() => navigate('/'), [navigate]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') home(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [home]);
  return (
    <div className="screen screen-fill board-screen">
      <BoardView
        interactive
        action={(
          <button type="button" className="btn board-back" onClick={home}>
            <Icon name="back" size={22} /><span>Back to Now</span>
          </button>
        )}
      />
      <p className="board-hint">Tap a service to mark it off or on; tap a job to tick it.</p>
    </div>
  );
}
