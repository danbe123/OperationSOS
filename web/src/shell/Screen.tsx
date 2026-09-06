import { useEffect, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { Icon } from '../icons';
import { SearchBar } from '../components/SearchBar';
import { ThemeButton } from '../theme/ThemeButton';
import { useWide } from './useWide';

/** Every screen is a `Screen`: a title as the first line, its own actions, Back to where you came
 * from, and the search field that is on every screen. Navigation lives in the shell, so no screen
 * draws an app bar of its own. */
export function Screen({
  title, actions, children, className, back = true, search = true, fill = false,
}: {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  back?: boolean;
  search?: boolean;
  fill?: boolean;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const wide = useWide();
  useEffect(() => {
    document.title = title === 'Operation SOS' ? title : `${title} · SOS`;
  }, [title]);
  const goBack = () => {
    // 'default' is the key of the first entry in this history; there is nothing to go back to.
    if (location.key === 'default') navigate('/');
    else navigate(-1);
  };
  const classes = ['screen', fill ? 'screen-fill' : '', className ?? ''].filter(Boolean).join(' ');
  return (
    <div className={classes}>
      <header className="screen-head">
        {back && (
          <button type="button" className="btn btn-quiet btn-small screen-head-back no-print" onClick={goBack}>
            <Icon name="back" size={20} /><span>Back</span>
          </button>
        )}
        <h1>{title}</h1>
        {actions && <div className="screen-head-actions no-print">{actions}</div>}
        {!wide && <ThemeButton className="screen-head-theme no-print" />}
        {search && wide && <div className="screen-head-search no-print"><SearchBar compact /></div>}
      </header>
      {children}
    </div>
  );
}

/** The body of a screen: one left-aligned column with the gutter and the vertical rhythm. */
export function Body({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={className ? `screen-body ${className}` : 'screen-body'}>{children}</div>;
}
