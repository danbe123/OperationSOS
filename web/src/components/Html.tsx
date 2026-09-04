import { useCallback, type MouseEvent } from 'react';
import { useAppLink } from '../links';

/** Render server-rendered HTML (playbooks, cards, pages) with delegated link handling. */
export function Html({ html, className }: { html: string; className?: string }) {
  const follow = useAppLink();
  const onClick = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as HTMLElement).closest('a[href]');
      if (!anchor || !e.currentTarget.contains(anchor)) return;
      if (follow(anchor.getAttribute('href') ?? '')) e.preventDefault();
    },
    [follow],
  );
  return <div className={className ? `html ${className}` : 'html'} onClick={onClick} dangerouslySetInnerHTML={{ __html: html }} />;
}
