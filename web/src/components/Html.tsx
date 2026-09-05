import { useCallback, useLayoutEffect, useMemo, useRef, type MouseEvent } from 'react';
import { useStatus } from '../api/status';
import { useAppLink } from '../links';
import { tagPhoneNumbers } from '../services';

/** Render server-rendered HTML (playbooks, cards, pages) with delegated link handling. */
export function Html({ html, className }: { html: string; className?: string }) {
  const follow = useAppLink();
  const { status } = useStatus();
  const phonesDown = status?.services?.phones === false;
  const ref = useRef<HTMLDivElement>(null);
  const content = useMemo(() => {
    if (!/<table[\s>]/i.test(html)) return html;
    const template = document.createElement('template');
    template.innerHTML = html;
    for (const table of template.content.querySelectorAll('table')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'table-scroll';
      wrapper.tabIndex = 0;
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', `${table.caption?.textContent?.trim() || 'Comparison table'} (scroll horizontally for more columns)`);
      const columns = Math.max(1, ...Array.from(table.rows, (row) => Array.from(row.cells).reduce((sum, cell) => sum + cell.colSpan, 0)));
      table.style.minWidth = `${columns * 11}rem`;
      for (const heading of table.querySelectorAll('thead th:not([scope])')) heading.setAttribute('scope', 'col');
      table.before(wrapper);
      wrapper.append(table);
    }
    return template.innerHTML;
  }, [html]);
  const onClick = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as HTMLElement).closest('a[href]');
      if (!anchor || !e.currentTarget.contains(anchor)) return;
      if (follow(anchor.getAttribute('href') ?? '')) e.preventDefault();
    },
    [follow],
  );
  // key forces a fresh render of the raw HTML when the phones state flips, so tags are added or removed cleanly
  useLayoutEffect(() => {
    if (phonesDown && ref.current) tagPhoneNumbers(ref.current);
  }, [content, phonesDown]);
  return <div key={phonesDown ? 'phones-down' : 'phones-up'} ref={ref} className={className ? `html ${className}` : 'html'} onClick={onClick} dangerouslySetInnerHTML={{ __html: content }} />;
}
