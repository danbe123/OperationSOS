import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { CallsNotice } from '../situation/CallsNotice';
import { Html } from '../components/Html';
import { ReadAloudBlock } from '../situation/ReadAloud';
import { PrintButton } from '../components/PrintButton';

export function Page() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.page(slug), [slug]);
  return (
    <Screen title={data?.title ?? 'Page'} search={false} actions={<PrintButton />}>
      <Body>
        <CallsNotice />
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Could not load this page: {error}</p>}
        {data && <ReadAloudBlock id={`page:${slug}`} label="Read this page aloud"><Html html={data.html} /></ReadAloudBlock>}
      </Body>
    </Screen>
  );
}
