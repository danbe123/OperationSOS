import { Link } from 'react-router';
import { Icon } from '../icons';
import type { Condition } from '../api/types';
import { chipDuration, CONDITION_INFO, STATE_LABEL, STATE_SYMBOL, STATE_TONE } from './conditions';

/** One service, as a chip: green working, amber patchy, red off, always with its symbol and its word.
 * Tapping it opens the situation sheet at that condition. */
export function ConditionChip({ condition, compact = false }: { condition: Condition; compact?: boolean }) {
  const info = CONDITION_INFO[condition.id];
  const tone = STATE_TONE[condition.state];
  const duration = chipDuration(condition.state, condition.for_s);
  const label = `${info.title}: ${STATE_LABEL[condition.state]}${duration ? ` ${duration}` : ''}`;
  return (
    <Link className={`cond-chip cond-${tone}${compact ? ' cond-chip-compact' : ''}`} to={`/situation#${condition.id}`} aria-label={label}>
      <Icon name={info.icon} size={compact ? 18 : 22} />
      <span className="cond-name">{info.short}</span>
      <span className="cond-state"><span aria-hidden="true">{STATE_SYMBOL[condition.state]}</span> {STATE_LABEL[condition.state]}</span>
      {duration && !compact && <span className="cond-for">{duration}</span>}
    </Link>
  );
}
