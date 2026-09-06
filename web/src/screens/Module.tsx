import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import { Html } from '../components/Html';
import { ReadAloudBlock } from '../situation/ReadAloud';
import { PrintButton } from '../components/PrintButton';

export function Module() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.module(slug), [slug]);
  return (
    <Screen title={data?.title ?? 'Module'} search={false} actions={<PrintButton />}>
      <Body>
        <Emergency999 onlyWhenHidden />
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="warning">Could not load this module: {error}</p>}
        {data && <ReadAloudBlock id={`module:${slug}`} label="Read aloud"><Html html={data.html} /></ReadAloudBlock>}
      </Body>
    </Screen>
  );
}
