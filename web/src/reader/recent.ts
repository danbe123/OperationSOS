import { useEffect } from 'react';
import { api } from '../api/client';
import type { RecentKind } from '../api/types';

/** What a screen tells the box it is showing, once it knows: the Library's front lists the last dozen. */
export type View = { key: string; kind: RecentKind; title: string; url: string; coverUrl?: string | null };

/** Record a view on the box, once per thing shown: the effect runs when the key or the title changes,
 * so a screen that does not know its title yet records nothing until it does. A box that cannot be
 * reached records nothing and says nothing: the screen is the point, the list is a convenience. */
export function useRecordView(view: View | null | undefined): void {
  const key = view?.key ?? '';
  const title = view?.title ?? '';
  const kind = view?.kind ?? 'page';
  const url = view?.url ?? '';
  const cover = view?.coverUrl ?? null;
  useEffect(() => {
    if (!key || !title || !url) return;
    try {
      void api.touchRecent(key, { kind, title, url, cover_url: cover }).catch(() => undefined);
    } catch {
      // no network at all (a test environment): the screen is unaffected
    }
  }, [key, title, kind, url, cover]);
}

/** The word a card wears for what a thing is. */
export const KIND_WORD: Record<RecentKind, string> = {
  book: 'Book', doc: 'Document', article: 'Article', page: 'Page', module: 'Module', guide: 'Guide', card: 'Quick card',
};

/** The icon a card wears when the thing has no cover. */
export const KIND_ICON: Record<RecentKind, string> = {
  book: 'library', doc: 'book', article: 'globe', page: 'book', module: 'book', guide: 'plan', card: 'medical',
};
