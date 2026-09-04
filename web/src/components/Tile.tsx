import { Link } from 'react-router';
import { Icon } from '../icons';

export function Tile({ to, icon, title, subtitle, big, disabled, note }: {
  to: string; icon: string; title: string; subtitle?: string; big?: boolean; disabled?: boolean; note?: string;
}) {
  const className = ['tile', big ? 'tile-big' : '', disabled ? 'disabled' : ''].filter(Boolean).join(' ');
  const body = (
    <>
      <Icon name={icon} size={big ? 36 : 28} />
      <span className="tile-title">{title}</span>
      {subtitle && <span className="tile-sub">{subtitle}</span>}
      {note && <span className="tile-sub tile-note">{note}</span>}
    </>
  );
  if (disabled) return <div className={className} aria-disabled="true">{body}</div>;
  return <Link className={className} to={to}>{body}</Link>;
}
