import { useNavigate } from 'react-router';
import { BoardView } from '../situation/BoardView';

/** `/board`: the whole screen is the board, and a tap anywhere on it goes back to Now. */
export function Board() {
  const navigate = useNavigate();
  const home = () => navigate('/');
  return (
    <div
      className="screen screen-fill board-screen"
      role="button"
      tabIndex={0}
      aria-label="Board: tap to go back to Now"
      onClick={home}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') home(); }}
    >
      <BoardView />
      <p className="board-hint">Tap anywhere to go back</p>
    </div>
  );
}
