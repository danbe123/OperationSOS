import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Html } from '../components/Html';

export function Card() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.card(slug), [slug]);
  return (
    <div className="screen card">
      <AppBar title="Quick card" search={false} />
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Could not load this card: {error}</p>}
      {data && (
        <>
          <h1 className="card-title">{data.title}</h1>
          <Html className="card-html" html={data.html} />
          <p className="pad warning">Life-threatening emergency: call 999.</p>
        </>
      )}
    </div>
  );
}
