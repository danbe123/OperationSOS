import { useCallback, useMemo, type MouseEvent } from 'react';
import { useAppLink } from '../links';
import { useCallsHidden } from '../situation/SituationProvider';

/** Render server-rendered HTML (playbooks, cards, pages) with delegated link handling.
 * While both phone networks are down every `tel:` link becomes the no-phones page instead:
 * a number that cannot connect must not look like one that can. */
export function Html({ html, className }: { html: string; className?: string }) {
  const follow = useAppLink();
  const callsHidden = useCallsHidden();
  const content = useMemo(() => {
    const hasTel = callsHidden && /href="tel:/i.test(html);
    if (!/<table[\s>]/i.test(html) && !hasTel) return html;
    const template = document.createElement('template');
    template.innerHTML = html;
    if (hasTel) {
      for (const anchor of template.content.querySelectorAll('a[href^="tel:"]')) {
        const number = (anchor.getAttribute('href') ?? '').slice('tel:'.length);
        anchor.setAttribute('href', '/p/no-phones');
        anchor.textContent = `${anchor.textContent?.trim() || number} will not connect: get help without phones`;
      }
    }
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
  }, [html, callsHidden]);
  const onClick = useCallback(
    (e: MouseEvent<HTMLDivElement>) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const anchor = (e.target as HTMLElement).closest('a[href]');
      if (!anchor || !e.currentTarget.contains(anchor)) return;
      if (follow(anchor.getAttribute('href') ?? '')) e.preventDefault();
    },
    [follow],
  );
  return <div className={className ? `html ${className}` : 'html'} onClick={onClick} dangerouslySetInnerHTML={{ __html: content }} />;
}
