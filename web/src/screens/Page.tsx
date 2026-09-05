import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { Html } from '../components/Html';

export function Page() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.page(slug), [slug]);
  return (
    <div className="screen reference-page">
      <AppBar title={data?.title ?? 'Page'} search={false} />
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Could not load this page: {error}</p>}
      {data && <Html html={data.html} />}
    </div>
  );
}
