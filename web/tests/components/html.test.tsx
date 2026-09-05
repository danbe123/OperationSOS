import { describe, it, expect } from 'vitest';
import { screen, act, fireEvent } from '@testing-library/react';
import { useLocation } from 'react-router';
import { renderRoute } from '../render';
import { Shell as Layout } from '../../src/shell/Shell';
import { Html } from '../../src/components/Html';
import { NOT_IN_LIBRARY } from '../../src/links';

function Where() {
  const loc = useLocation();
  return <span data-testid="where">{loc.pathname}{loc.search}{loc.hash}</span>;
}
const html = `
<p><a id="card" href="card:cpr-adult">CPR</a>
<a id="doc" href="/doc/nrr-2025#page=12">NRR</a>
<a id="ext" href="https://example.org/">Outside</a>
<a id="frag" href="#more">More</a></p>
<h2 id="more">More</h2>`;
const routes = [{ path: '/', element: <Layout />, children: [{ path: '*', element: <div><Html html={html} /><Where /></div> }] }];

describe('Html', () => {
  it('renders the HTML and navigates app links through the router', async () => {
    renderRoute('/s/grid-collapse', { routes });
    expect(screen.getByRole('heading', { name: 'More' })).toBeInTheDocument();
    await act(async () => { fireEvent.click(document.getElementById('card')!); });
    expect(screen.getByTestId('where')).toHaveTextContent('/medical/card/cpr-adult');
  });
  it('keeps the #page fragment on doc links', async () => {
    renderRoute('/s/grid-collapse', { routes });
    await act(async () => { fireEvent.click(document.getElementById('doc')!); });
    expect(screen.getByTestId('where')).toHaveTextContent('/doc/nrr-2025#page=12');
  });
  it('shows the in-app notice for external links instead of leaving', async () => {
    renderRoute('/s/grid-collapse', { routes });
    await act(async () => { fireEvent.click(document.getElementById('ext')!); });
    expect(screen.getByText(new RegExp(NOT_IN_LIBRARY.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))).toBeInTheDocument();
    expect(screen.getByTestId('where')).toHaveTextContent('/s/grid-collapse');
  });
  it('lets fragment links through to the browser', async () => {
    renderRoute('/s/grid-collapse', { routes });
    const ev = new MouseEvent('click', { bubbles: true, cancelable: true });
    await act(async () => { document.getElementById('frag')!.dispatchEvent(ev); });
    expect(ev.defaultPrevented).toBe(false);
  });
});
