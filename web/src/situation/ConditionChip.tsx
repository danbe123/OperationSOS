import { Link } from 'react-router';
import { Icon } from '../icons';
import type { Condition } from '../api/types';
import { chipDuration, CONDITION_INFO, shortDuration, STATE_LABEL, STATE_SYMBOL, STATE_TONE } from './conditions';

/** One service, as a chip: green working, amber patchy, red off, always with its symbol, its word
 * and how long it has been that way. The duration is the number that decides whether the freezer is
 * still safe, so the compact chip in the band drops its icon before it drops the duration.
 * Tapping it opens the situation sheet at that condition. */
export function ConditionChip({ condition, compact = false }: { condition: Condition; compact?: boolean }) {
  const info = CONDITION_INFO[condition.id];
  const tone = STATE_TONE[condition.state];
  const full = chipDuration(condition.state, condition.for_s);
  const duration = compact ? shortDuration(condition.state, condition.for_s) : full;
  const label = `${info.title}: ${STATE_LABEL[condition.state]}${full ? ` ${full}` : ''}`;
  return (
    <Link className={`cond-chip cond-${tone}${compact ? ' cond-chip-compact' : ''}`} to={`/situation#${condition.id}`} aria-label={label}>
      <Icon name={info.icon} size={compact ? 18 : 22} className="cond-icon" />
      <span className="cond-name">{info.short}</span>
      <span className="cond-state"><span aria-hidden="true">{STATE_SYMBOL[condition.state]}</span> {STATE_LABEL[condition.state]}</span>
      {duration && <span className="cond-for">{duration}</span>}
    </Link>
  );
}
