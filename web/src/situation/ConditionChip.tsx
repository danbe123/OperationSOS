import { Link } from 'react-router';
import { Icon } from '../icons';
import type { Condition } from '../api/types';
import { chipDuration, CONDITION_INFO, elapsedFrom, shortDuration, STATE_SYMBOL, STATE_TONE, stateWord } from './conditions';

/** One service, as a chip: green working, amber patchy, red off, always with its symbol, its word
 * and how long it has been that way. The duration is the number that decides whether the freezer is
 * still safe, so the compact chip in the band drops its icon before it drops the duration.
 * Tapping it opens the situation sheet at that condition. */
export function ConditionChip({ condition, compact = false }: { condition: Condition; compact?: boolean }) {
  const info = CONDITION_INFO[condition.id];
  const tone = STATE_TONE[condition.state];
  // Counted from the instant the box stored, so the band, the board and the sheet never disagree
  // about how long the power has been off.
  const elapsed = elapsedFrom(condition);
  const full = chipDuration(condition.state, elapsed);
  const duration = compact ? shortDuration(condition.state, elapsed) : full;
  const word = stateWord(condition.id, condition.state);
  const label = `${info.title}: ${word}${full ? ` ${full}` : ''}`;
  return (
    <Link className={`cond-chip cond-${tone}${compact ? ' cond-chip-compact' : ''}`} to={`/situation#${condition.id}`} aria-label={label}>
      <Icon name={info.icon} size={compact ? 18 : 22} className="cond-icon" />
      <span className="cond-name">{info.short}</span>
      <span className="cond-state"><span aria-hidden="true">{STATE_SYMBOL[condition.state]}</span> {word}</span>
      {duration && <span className="cond-for">{duration}</span>}
    </Link>
  );
}
