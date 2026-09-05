import { useParams } from 'react-router';
import { api } from '../api/client';
import { useQuery } from '../api/useQuery';
import { AppBar } from '../components/AppBar';
import { OutageNotice } from '../components/ServiceToggles';
import { Html } from '../components/Html';

export function Module() {
  const { slug = '' } = useParams();
  const { data, error, loading } = useQuery(() => api.module(slug), [slug]);
  return (
    <div className="screen reference-page">
      <AppBar title={data?.title ?? 'Module'} search={false} />
      <OutageNotice />
      {loading && <p className="pad muted">Loading…</p>}
      {error && <p className="pad warning">Could not load this module: {error}</p>}
      {data && <Html html={data.html} />}
    </div>
  );
}
