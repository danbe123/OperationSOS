import { resolveLink } from '../links';
import type { BriefingItem } from '../api/types';

/** Rules and the engine speak the content link scheme ("module:water"); the app speaks paths. */
export function contentHref(link: string | null | undefined): string | null {
  if (!link) return null;
  if (link.startsWith('/')) return link;
  return resolveLink(link);
}

/** A briefing entry names what to open: a playbook section, a module, a page, a card, a document,
 * the map or an article. The engine splits the content link into kind and ref; this puts it back. */
export function briefingHref(item: BriefingItem): string {
  const scheme = item.kind === 'playbook-section' ? 'playbook' : item.kind;
  return resolveLink(`${scheme}:${item.ref}`) ?? '/';
}
