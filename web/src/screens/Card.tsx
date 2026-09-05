import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { CallsNotice } from '../situation/CallsNotice';
import { Html } from '../components/Html';

export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  return (
    <Screen title={data?.title ?? 'Quick card'} search={false} className="card">
      <Body>
        <CallsNotice />
        {loading && <p className="muted">Loading the card…</p>}
        {error && <p className="warning">Could not load this card: {error}</p>}
        {data && (
          <>
            <Html className="card-html" html={data.html} />
            <p className="warning">Life-threatening emergency: call 999.</p>
          </>
        )}
      </Body>
    </Screen>
  );
}
