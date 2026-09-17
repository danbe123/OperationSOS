import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { Shell as Layout } from '../../src/shell/Shell';
import { absentLine, LibraryItemCard, formatBytes, itemOpenPath } from '../../src/components/LibraryItemCard';
import { wikiItem, pdfItem, epubItem, extItem, mapsItem } from '../fixtures/api';

describe('formatBytes', () => {
  it('uses one decimal under 10 and whole numbers above', () => {
    expect(formatBytes(900)).toBe('900 B');
    expect(formatBytes(4_700_000)).toBe('4.5 MB');
    expect(formatBytes(206_000_000_000)).toBe('192 GB');
    expect(formatBytes(1_900_000_000)).toBe('1.8 GB');
  });
});

describe('itemOpenPath', () => {
  it('routes by kind and returns null when unavailable', () => {
    expect(itemOpenPath(wikiItem)).toBe(`/read/${wikiItem.id}/A/Main_Page`);
    expect(itemOpenPath(pdfItem)).toBe('/doc/nrr-2025');
    expect(itemOpenPath(epubItem)).toBe('/doc/where-there-is-no-doctor');
    expect(itemOpenPath(mapsItem)).toBe('/map');
    expect(itemOpenPath(extItem)).toBeNull();
    expect(itemOpenPath({ ...wikiItem, kind: 'model' })).toBeNull();
  });
});

describe('LibraryItemCard', () => {
  const routes = [{ path: '/', element: <Layout />, children: [{ index: true, element: <ul><LibraryItemCard item={wikiItem} /><LibraryItemCard item={extItem} /></ul> }] }];
  it('shows kind icon, size, as-at, drive badge and an Open button; greys out items on a missing drive', () => {
    renderRoute('/', { routes });
    const wiki = document.getElementById(`item-${wikiItem.id}`)!;
    expect(within(wiki).getByText('4.5 MB, copied 2026-01.')).toBeInTheDocument();
    // "zim" is the box's word for it, never the household's.
    expect(within(wiki).getByText('Offline copy')).toHaveClass('badge');
    expect(within(wiki).getByText('Core')).toHaveClass('badge');
    expect(within(wiki).getByRole('link', { name: 'Open' })).toHaveAttribute('href', wikiItem.url!);
    expect(wiki.querySelector('svg.icon')).not.toBeNull();
    const ext = document.getElementById('item-gutenberg_en_all')!;
    expect(ext).toHaveClass('unavailable');
    expect(within(ext).getByText('On external drive (not connected)')).toHaveClass('badge-warn');
    expect(within(ext).queryByRole('link', { name: 'Open' })).toBeNull();
    expect(screen.getAllByText('192 GB, copied 2025-11.')).toHaveLength(1);
  });
});

describe('an item that is not here', () => {
  const core = { ...wikiItem, id: 'libretexts.org_en_bio', title: 'LibreTexts Biology', available: false, url: null, size_bytes: 1_200_000_000, fetch: 'download' as const, source_type: 'kiwix' as const };
  it('offers Get it with the size when the box can fetch it, and says it is downloading once asked', () => {
    const onFetch = vi.fn();
    const routes = [{ path: '/', element: <Layout />, children: [{ index: true, element: <ul><LibraryItemCard item={core} onFetch={onFetch} /><LibraryItemCard item={{ ...core, id: 'busy' }} onFetch={onFetch} fetching /></ul> }] }];
    renderRoute('/', { routes });
    const card = document.getElementById('item-libretexts.org_en_bio')!;
    within(card).getByRole('button', { name: 'Get it (1.1 GB)' }).click();
    expect(onFetch).toHaveBeenCalledWith('libretexts.org_en_bio');
    expect(within(card).getByText('Not on this box yet.')).toBeInTheDocument();
    const busy = document.getElementById('item-busy')!;
    expect(within(busy).getByRole('button', { name: 'Getting it…' })).toBeDisabled();
    expect(within(busy).getByText(/Downloading\. It appears here when it is done/)).toBeInTheDocument();
  });

  it('says what brings each kind of absent item, and offers no button without a fetch', () => {
    expect(absentLine({ ...core, fetch: 'drive' })).toBe('On the external drive. Plug it in and it appears.');
    expect(absentLine({ ...core, fetch: 'build', build_tool: 'build-nhs' })).toBe('Made on a PC with sos build-nhs and copied here.');
    expect(absentLine({ ...core, fetch: 'own' })).toBe('Your own files: copy them onto the drive and they appear.');
    expect(absentLine({ ...core, fetch: null })).toBe('Not available.');
    const routes = [{ path: '/', element: <Layout />, children: [{ index: true, element: <ul><LibraryItemCard item={core} /></ul> }] }];
    renderRoute('/', { routes });
    expect(screen.queryByRole('button', { name: /Get it/ })).toBeNull();
    expect(screen.getByText('Not on this box yet.')).toBeInTheDocument();
  });
});
