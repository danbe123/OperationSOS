import { useEffect, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Icon } from '../icons';
import { SearchBar } from '../components/SearchBar';
import { ThemeButton } from '../theme/ThemeButton';
import { useReportScreenTitle } from './screenTitle';

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
  const reportTitle = useReportScreenTitle();
  useEffect(() => {
    document.title = title === 'Operation SOS' ? title : `${title} · SOS`;
    reportTitle(title);
  }, [title, reportTitle]);
  const goBack = () => {
    // 'default' is the key of the first entry in this history; there is nothing to go back to.
    if (location.key === 'default') navigate('/');
    else navigate(-1);
  };
  const classes = ['screen', fill ? 'screen-fill' : '', className ?? ''].filter(Boolean).join(' ');
  // Find is the search: it does not need a field in its head above the field in its body, or a
  // button to itself.
  const onFind = location.pathname === '/search' || location.pathname === '/find';
  return (
    <div className={classes}>
      {/* With no Back button the theme button had a phone row to itself above the title; it shares
          the title's line instead, and the screen keeps the 40 pixels. */}
      <header className={back ? 'screen-head' : 'screen-head screen-head-noback'}>
        {back && (
          <button type="button" className="btn btn-quiet btn-small screen-head-back no-print" onClick={goBack}>
            <Icon name="back" size={20} /><span>Back</span>
          </button>
        )}
        <h1>{title}</h1>
        {actions && <div className="screen-head-actions no-print">{actions}</div>}
        <ThemeButton className="screen-head-theme no-print" />
        {/* Search is on every screen, phones included: the field where the screen has room for it,
            and the way to Find where it has not. A phone had neither, on twenty-three screens. */}
        {!onFind && (search
          ? <div className="screen-head-search no-print"><SearchBar compact /></div>
          : (
            <Link className="btn btn-quiet btn-small screen-head-find no-print" to="/search">
              <Icon name="search" size={18} /><span>Find</span>
            </Link>
          ))}
      </header>
      {children}
    </div>
  );
}

/** The body of a screen: one left-aligned column with the gutter and the vertical rhythm. */
export function Body({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={className ? `screen-body ${className}` : 'screen-body'}>{children}</div>;
}
