import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useNavigate } from 'react-router';
import { api } from '../api/client';
import type { Suggestion } from '../api/types';
import { useAppLink } from '../links';
import { sourceWord } from '../api/words';
import { Icon } from '../icons';

export const SUGGEST_DEBOUNCE_MS = 250;
export const SUGGEST_MIN_CHARS = 2;
export const SEARCH_MAX_CHARS = 512;   // the server refuses a longer query with a bare 422

export function SearchBar({
  initial = '',
  compact = false,
  autoFocus = false,
  placeholder,
}: { initial?: string; compact?: boolean; autoFocus?: boolean; placeholder?: string }) {
  // The compact field lives in the screen head, where there is no room for the long line.
  const hint = placeholder ?? (compact ? 'Search the box' : 'Search Wikipedia, NHS, manuals, maps, guides');
  const navigate = useNavigate();
  const follow = useAppLink();
  const [q, setQ] = useState(initial);
  const [items, setItems] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const abortRef = useRef<AbortController | null>(null);
  // Suggestions answer typing. Arriving on a screen that already carries a term (Find, from the URL)
  // must not drop a list of guesses over the results the reader just asked for.
  const typed = useRef(false);

  useEffect(() => { setQ(initial); typed.current = false; }, [initial]);

  useEffect(() => {
    const term = q.trim();
    if (!typed.current || term.length < SUGGEST_MIN_CHARS) {
      setItems([]);
      setOpen(false);
      return;
    }
    const timer = window.setTimeout(async () => {
      abortRef.current?.abort();
      const ctl = new AbortController();
      abortRef.current = ctl;
      try {
        const got = await api.suggest(term, ctl.signal);
        if (!ctl.signal.aborted) {
          setItems(got.slice(0, 10));
          setOpen(got.length > 0);
          setActive(-1);
        }
      } catch {
        if (!ctl.signal.aborted) setItems([]);
      }
    }, SUGGEST_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [q]);

  const go = (term: string) => {
    const t = term.trim();
    if (!t) return;
    setOpen(false);
    navigate(`/search?q=${encodeURIComponent(t)}`);
  };
  const pick = (s: Suggestion) => {
    setOpen(false);
    setQ(s.value);
    if (s.url) follow(s.url);
    else go(s.value);
  };
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (open && active >= 0 && items[active]) pick(items[active]);
    else go(q);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (!open || items.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, items.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, -1));
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <form className={compact ? 'searchbar searchbar-compact' : 'searchbar'} role="search" onSubmit={onSubmit}>
      <input
        type="search"
        role="combobox"
        aria-label="Search"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        enterKeyHint="search"
        maxLength={SEARCH_MAX_CHARS}
        placeholder={hint}
        value={q}
        autoFocus={autoFocus}
        onChange={(e) => { typed.current = true; setQ(e.target.value); }}
        onFocus={() => items.length > 0 && setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
      />
      {/* The accent belongs to the screen's own primary action, not to the search on every screen. */}
      <button type="submit" className="btn">
        <Icon name="search" />
        <span>Search</span>
      </button>
      {open && items.length > 0 && (
        <ul className="suggestions" id={listId} role="listbox">
          {items.map((s, i) => (
            <li
              key={`${s.source}:${s.value}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : undefined}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(s)}
            >
              {/* Not a separate focus stop: the combobox input keeps focus while an option list is open (ARIA combobox pattern). */}
              <button type="button" tabIndex={-1}>
                <span>{s.label}</span>
                <span className="badge">{sourceWord(s.source)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
