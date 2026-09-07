import { useEffect, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Icon } from '../icons';
import { SearchBar } from '../components/SearchBar';
import { ThemeButton } from '../theme/ThemeButton';
import { printedOn } from '../tools/printing';
import { useReportScreenTitle } from './screenTitle';
import { useWide } from './useWide';

/** Every screen is a `Screen`: a title as the first line, its own actions, Back to where you came
 * from, and the search field that is on every screen. Navigation lives in the shell, so no screen
 * draws an app bar of its own. */
export function Screen({
  title, actions, children, className, back = true, search = true, fill = false, backTo,
}: {
  title: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  back?: boolean;
  search?: boolean;
  fill?: boolean;
  /** Where Back goes instead of the history stack. A screen reached by a deep link (a pin dropped
      on the map, say) has no useful "back" in history — it returns to its parent screen instead. */
  backTo?: string;
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const reportTitle = useReportScreenTitle();
  const wide = useWide();
  useEffect(() => {
    document.title = title === 'Operation SOS' ? title : `${title} · SOS`;
    reportTitle(title);
  }, [title, reportTitle]);
  const goBack = () => {
    if (backTo) navigate(backTo);
    // 'default' is the key of the first entry in this history; there is nothing to go back to.
    else if (location.key === 'default') navigate('/');
    else navigate(-1);
  };
  const classes = ['screen', fill ? 'screen-fill' : '', className ?? ''].filter(Boolean).join(' ');
  // Find is the search: it does not need a field in its head above the field in its body, or a
  // button to itself.
  const onFind = location.pathname === '/search' || location.pathname === '/find';
  return (
    <div className={classes}>
      {/* A sheet pulled out of the box has to say what it is and when it was printed, or it cannot be
          identified or put back in order. Nothing but the printer ever sees this. */}
      <div className="print-only print-head" aria-hidden="true">
        <strong>Operation SOS</strong> · {title} · printed {printedOn()}
      </div>
      <header className={back ? 'screen-head' : 'screen-head screen-head-noback'}>
        {back && (
          <button type="button" className="btn btn-quiet btn-small screen-head-back no-print" onClick={goBack}>
            <Icon name="back" size={20} /><span>Back</span>
          </button>
        )}
        <h1>{title}</h1>
        {/* The screen's own controls, and on a phone the theme is one of them: it used to have a
            boxed, two-line row of its own above the search field and above the "999 will not
            connect" panel — the most prominent control on the front door during a triple outage. */}
        {(actions || !wide) && (
          <div className="screen-head-actions no-print">
            {actions}
            {!wide && <ThemeButton className="screen-head-theme" />}
          </div>
        )}
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
