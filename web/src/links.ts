import { useCallback } from 'react';
import { useNavigate } from 'react-router';
import { notify } from './components/Notice';

export const NOT_IN_LIBRARY = 'Not in the library (needs the internet)';

/** Resolve the Markdown link scheme to an app path; null when `href` is not a scheme link. Mirrors sos.content.resolve_link. */
export function resolveLink(href: string): string | null {
  const m = /^(kiwix|doc|map|playbook|module|card|page):([\s\S]*)$/.exec(href);
  if (!m) return null;
  const scheme = m[1];
  const rest = m[2];
  switch (scheme) {
    case 'kiwix': {
      const slash = rest.indexOf('/');
      if (slash <= 0) return null;
      return readerRoute(rest.slice(0, slash), rest.slice(slash + 1));
    }
    case 'doc': {
      const hash = rest.indexOf('#');
      const id = hash === -1 ? rest : rest.slice(0, hash);
      const fragment = hash === -1 ? '' : rest.slice(hash);
      return id ? `/doc/${id}${fragment}` : null;
    }
    case 'map':
      if (!rest) return '/map';
      return `/map${rest.startsWith('?') ? rest : `?${rest}`}`;
    case 'playbook':
      return rest ? `/s/${rest}` : null;
    case 'module':
      return rest ? `/m/${rest}` : null;
    case 'card':
      return rest ? `/medical/card/${rest}` : null;
    case 'page':
      return rest ? `/p/${rest}` : null;
    default:
      return null;
  }
}

export function parseKiwixContentPath(pathname: string): { id: string; path: string } | null {
  const m = /^\/kiwix\/content\/([^/]+)\/(.*)$/.exec(pathname);
  return m ? { id: m[1], path: m[2] } : null;
}
export function readerRoute(id: string, path: string): string {
  return `/read/${id}/${path}`;
}
export function kiwixContentUrl(id: string, path: string): string {
  return `/kiwix/content/${id}/${path}`;
}

/** Move a same-origin frame without adding a history entry. Kept as a function so tests can mock it (jsdom's Location is not spyable). */
export function replaceFrameLocation(win: Window, url: string): void {
  win.location.replace(url);
}

/** A native document viewer or redirect can expose a protected, cross-origin Location. */
export function sameOriginFrameUrl(win: Window): URL | null {
  try {
    const url = new URL(win.location.href);
    return url.origin === window.location.origin ? url : null;
  } catch {
    return null;
  }
}

export type HrefClass =
  | { kind: 'app'; to: string }
  | { kind: 'external'; href: string }
  | { kind: 'hash'; hash: string }
  | { kind: 'other' };

/** Classify an href found in rendered content. `base` is the URL the href is relative to (defaults to the app's location). */
export function classifyHref(href: string, base: string = window.location.href): HrefClass {
  const scheme = resolveLink(href);
  if (scheme) return { kind: 'app', to: scheme };
  if (href.startsWith('#')) return { kind: 'hash', hash: href };
  let url: URL;
  let origin: string;
  try {
    url = new URL(href, base);
    origin = new URL(base).origin;
  } catch {
    return { kind: 'other' };
  }
  if (url.protocol === 'http:' || url.protocol === 'https:') {
    if (url.origin !== origin) return { kind: 'external', href: url.href };
    if (url.pathname.startsWith('/kiwix/catch/external')) return { kind: 'external', href: url.searchParams.get('source') ?? url.href };
    const kiwix = parseKiwixContentPath(url.pathname);
    if (kiwix) return { kind: 'app', to: readerRoute(kiwix.id, kiwix.path) + url.search + url.hash };
    if (url.pathname.startsWith('/docs/') || url.pathname.startsWith('/maps/') || url.pathname.startsWith('/kiwix/')) return { kind: 'other' };
    return { kind: 'app', to: url.pathname + url.search + url.hash };
  }
  if (url.protocol === 'mailto:' || url.protocol === 'tel:') return { kind: 'other' };
  return { kind: 'external', href };
}

/** Turn every link the box cannot follow into plain text, keeping its wording. An archived page carries
 * hundreds of links to the internet (citations, infoboxes, "official site"); on a box with no internet a
 * tappable link that only ever produces a notice reads as broken. Returns how many were unlinked. */
export function unlinkExternal(doc: Document, base: string): number {
  let count = 0;
  for (const anchor of Array.from(doc.querySelectorAll('a[href]'))) {
    const c = classifyHref(anchor.getAttribute('href') ?? '', base);
    if (c.kind !== 'external') continue;
    const span = doc.createElement('span');
    span.className = 'sos-unlinked';
    while (anchor.firstChild) span.appendChild(anchor.firstChild);
    anchor.replaceWith(span);
    count++;
  }
  return count;
}

/** Returns a function that follows an href the app way. It returns true when it handled the link (caller should preventDefault). */
export function useAppLink(): (href: string, base?: string) => boolean {
  const navigate = useNavigate();
  return useCallback(
    (href: string, base?: string) => {
      const c = classifyHref(href, base);
      if (c.kind === 'app') {
        navigate(c.to);
        return true;
      }
      if (c.kind === 'external') {
        notify(NOT_IN_LIBRARY);
        return true;
      }
      return false;
    },
    [navigate],
  );
}
