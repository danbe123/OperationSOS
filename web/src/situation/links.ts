import { resolveLink } from '../links';
import type { BriefingItem } from '../api/types';

/** Rules and the engine speak the content link scheme ("module:water"); the app speaks paths. */
export function contentHref(link: string | null | undefined): string | null {
  if (!link) return null;
  if (link.startsWith('/')) return link;
  return resolveLink(link);
}

/** A briefing entry names what to open: a playbook section, a module, a page, a card or a document. */
export function briefingHref(item: BriefingItem): string {
  switch (item.kind) {
    case 'playbook-section': {
      const [slug, section] = item.ref.split('#');
      return section ? `/s/${slug}#${section}` : `/s/${slug}`;
    }
    case 'module': return `/m/${item.ref}`;
    case 'page': return `/p/${item.ref}`;
    case 'card': return `/medical/card/${item.ref}`;
    case 'doc': return `/doc/${item.ref}`;
    default: return '/';
  }
}
