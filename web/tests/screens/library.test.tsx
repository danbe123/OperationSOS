import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { api } from '../../src/api/client';
import { cards, library, pages } from '../fixtures/api';
import { TOOL_TILES } from '../../src/screens/Tools';

describe('Library hub', () => {
  beforeEach(() => {
    vi.spyOn(api, 'pages').mockResolvedValue(pages);
    vi.spyOn(api, 'library').mockResolvedValue(library);
    vi.spyOn(api, 'cards').mockResolvedValue(cards);
  });

  it('is four shelves as tiles, the medical shelf first, each saying what is on it', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 60366, available: true });
    renderRoute('/library');
    const shelves = await screen.findByRole('navigation', { name: 'Shelves' });
    const links = within(shelves).getAllByRole('link');
    expect(links.map((a) => a.getAttribute('href'))).toEqual(['/library/medical', '/library/guides', '/library/books', '/library/sources']);
    expect(await within(shelves).findByText(`999, ${cards.length} quick cards, the NHS A to Z, children's doses`)).toBeInTheDocument();
    expect(await within(shelves).findByText(`${pages.length} pages and ${TOOL_TILES.length} tools, written for this box`)).toBeInTheDocument();
    expect(await within(shelves).findByText('60,366 books to read, Project Gutenberg')).toBeInTheDocument();
    expect(await within(shelves).findByText('Wikipedia, the NHS, manuals, maps: 8 sources, 7 on this box')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Back' })).not.toBeInTheDocument();
  });

  it('greys the Books shelf when the collection is not on the box', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    renderRoute('/library');
    const shelves = await screen.findByRole('navigation', { name: 'Shelves' });
    expect(await within(shelves).findByText('Project Gutenberg is not on this box yet')).toBeInTheDocument();
    expect(within(shelves).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual(['/library/medical', '/library/guides', '/library/sources']);
  });

  it('sends the old Guides address to its shelf', async () => {
    const { router } = renderRoute('/guides');
    expect(await screen.findByRole('searchbox', { name: 'Filter these guides' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/library/guides');
  });

  it('sends the old Medical address to its shelf, which has Back to the Library and the same cards', async () => {
    const { router } = renderRoute('/medical');
    expect(await screen.findByRole('navigation', { name: 'Quick cards' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/library/medical');
    expect(screen.getByRole('button', { name: /Back/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /CPR/ })).toHaveAttribute('href', expect.stringMatching(/^\/medical\/card\//));
  });

  it('sends the old Books address to its shelf', async () => {
    vi.spyOn(api, 'books').mockResolvedValue({ items: [], total: 0, available: false });
    vi.spyOn(api, 'reading').mockResolvedValue([]);
    vi.spyOn(api, 'bookShelves').mockResolvedValue([]);
    const { router } = renderRoute('/books');
    await screen.findByText(/Project Gutenberg is not on this box yet/);
    expect(router.state.location.pathname).toBe('/library/books');
  });
});

describe('Sources', () => {
  it('is one tile per kind of source, each naming what it holds', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    renderRoute('/library/sources');
    const kinds = await screen.findByRole('navigation', { name: 'Kinds of source' });
    const tiles = within(kinds).getAllByRole('link');
    expect(tiles.map((a) => a.getAttribute('href'))).toEqual(['/library/sources/medical', '/library/sources/uk-official', '/library/sources/practical', '/library/sources/reference', '/library/sources/maps', '/library/sources/books']);
    expect(tiles[0]).toHaveTextContent('Medical');
    expect(tiles[0]).toHaveTextContent('3 sources: NHS website, NHS Medicines A to Z and 1 more');
    expect(tiles[5]).toHaveTextContent('1 source, 0 on this box: Project Gutenberg');
  });

  it('lists one kind of source and scrolls to the item named in the hash', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const scroll = vi.spyOn(Element.prototype, 'scrollIntoView');
    renderRoute('/library/sources/uk-official#item-nrr-2025');
    expect(await screen.findByRole('heading', { name: 'UK official' })).toBeInTheDocument();
    await screen.findByText('National Risk Register 2025');
    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    expect(scroll).toHaveBeenCalled();
    expect((scroll.mock.instances[0] as unknown as Element).id).toBe('item-nrr-2025');
  });

  it('sends an unknown kind back to the Sources shelf, and the old Collections address too', async () => {
    vi.spyOn(api, 'library').mockResolvedValue(library);
    const { router } = renderRoute('/library/sources/nonsense');
    await screen.findByRole('navigation', { name: 'Kinds of source' });
    expect(router.state.location.pathname).toBe('/library/sources');
    const old = renderRoute('/library/collections');
    expect(old.router.state.location.pathname).toBe('/library/sources');
  });

  it('shows an error state', async () => {
    vi.spyOn(api, 'library').mockRejectedValue(new Error('db locked'));
    renderRoute('/library/sources');
    expect(await screen.findByText('Library unavailable: db locked')).toBeInTheDocument();
  });
});
