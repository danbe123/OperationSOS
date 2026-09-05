import { useEffect, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Icon } from '../icons';
import { ThemeButton } from '../theme/ThemeButton';
import { SearchBar } from './SearchBar';
import { ChipStrip } from '../situation/ChipStrip';

export function AppBar({ title, actions, back = true, search = true }: { title: string; actions?: ReactNode; back?: boolean; search?: boolean }) {
  const navigate = useNavigate();
  const location = useLocation();
  useEffect(() => {
    document.title = title === 'Operation SOS' ? title : `${title} · SOS`;
  }, [title]);
  const goBack = () => {
    // 'default' is the key of the first entry in this history; nothing to go back to.
    if (location.key === 'default') navigate('/');
    else navigate(-1);
  };
  return (
    <>
    <header className="appbar chrome">
      {back && (
        <button type="button" className="btn btn-chrome" onClick={goBack} aria-label="Back">
          <Icon name="back" /><span>Back</span>
        </button>
      )}
      <h1 className="appbar-title">{title}</h1>
      <div className="appbar-actions">{actions}</div>
      {search && (
        <div className="appbar-search">
          <SearchBar compact />
        </div>
      )}
      <Link
        className={`btn btn-chrome appbar-search-link${search ? ' appbar-search-link-replaced' : ''}`}
        to="/search"
        aria-label="Search"
      ><Icon name="search" /><span>Search</span></Link>
      <Link className="btn btn-chrome" to="/" aria-label="Home"><Icon name="home" /><span>Home</span></Link>
      <ThemeButton />
    </header>
    <ChipStrip />
    </>
  );
}
