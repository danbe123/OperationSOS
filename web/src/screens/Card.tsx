import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { Screen, Body } from '../shell/Screen';
import { Emergency999 } from '../situation/Emergency999';
import { Html } from '../components/Html';

/** A quick card is read at arm's length by someone kneeling over a body. The call comes first, then
 * the first compression: nothing else is on the screen. */
export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  return (
    <Screen title={data?.title ?? 'Quick card'} search={false} className="card">
      <Body>
        <Emergency999 />
        {loading && <p className="muted">Loading the card…</p>}
        {error && <p className="warning">Could not load this card: {error}</p>}
        {data && <Html className="card-html" html={data.html} />}
      </Body>
    </Screen>
  );
}
