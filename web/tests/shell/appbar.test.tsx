import { describe, it, expect } from 'vitest';
import { screen, act } from '@testing-library/react';
import { useLocation } from 'react-router';
import { renderRoute } from '../render';
import { AppBar } from '../../src/components/AppBar';
import { Layout } from '../../src/router';

function Where() {
  const loc = useLocation();
  return <span data-testid="where">{loc.pathname}</span>;
}
const routes = [
  { path: '/', element: <Layout />, children: [
    { index: true, element: <div><AppBar title="Operation SOS" back={false} /><Where /></div> },
    { path: 'a', element: <div><AppBar title="Screen A" actions={<button>Extra</button>} /><Where /></div> },
  ] },
];

describe('AppBar', () => {
  it('renders title, Home, Search, theme button and extra actions; sets document.title', async () => {
    renderRoute('/a', { routes });
    expect(screen.getByRole('heading', { name: 'Screen A' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /home/i })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: /search/i })).toHaveAttribute('href', '/search');
    expect(screen.getByRole('button', { name: /theme: vault/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Extra' })).toBeInTheDocument();
    expect(document.title).toBe('Screen A · SOS');
  });

  it('Back goes to the previous entry, or Home when there is none', async () => {
    const { router } = renderRoute('/a', { routes });
    await act(async () => { screen.getByRole('button', { name: /back/i }).click(); });
    expect(screen.getByTestId('where')).toHaveTextContent('/');
    await act(async () => { await router.navigate('/a'); });
    await act(async () => { screen.getByRole('button', { name: /back/i }).click(); });
    expect(screen.getByTestId('where')).toHaveTextContent('/');
  });

  it('hides Back on the home screen', () => {
    renderRoute('/', { routes });
    expect(screen.queryByRole('button', { name: /back/i })).toBeNull();
  });
});
