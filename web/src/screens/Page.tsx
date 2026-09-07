import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import { Html } from '../components/Html';
import { ReadAloudBlock } from '../situation/ReadAloud';
import { PrintButton } from '../components/PrintButton';
import './page.css';

/** The printed primer is not one document but a bundle of one-page sheets, one under each `## `
 * heading. It prints as sheets — one to a side of A4 — and says so before anybody spends the paper.
 * Every other page prints as what it is: one document, printed straight through. */
const SHEETS_SLUG = 'rebuild-essentials-printed';

export function Page() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.page(slug), [slug]);
  const sheets = slug === SHEETS_SLUG && data?.category === 'rebuild';
  return (
    <Screen
      title={data?.title ?? 'Page'} search={false}
      className={sheets ? 'page-print-sheets' : undefined}
      actions={<PrintButton label={sheets ? 'Print all sheets' : 'Print'} />}
    >
      <Body>
        {sheets && <p className="muted">Each sheet prints on its own side of A4.</p>}
        <Emergency999 onlyWhenHidden />
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Could not load this page: {error}</p>}
        {data && <ReadAloudBlock id={`page:${slug}`} label="Read aloud"><Html html={data.html} /></ReadAloudBlock>}
      </Body>
    </Screen>
  );
}
