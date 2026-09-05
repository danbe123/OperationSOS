import { describe, it, expect } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderRoute } from '../render';
import { Shell as Layout } from '../../src/shell/Shell';
import { LibraryItemCard, formatBytes, itemOpenPath } from '../../src/components/LibraryItemCard';
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
    expect(within(wiki).getByText('4.5 MB · as at 2026-01 · CC BY-SA 4.0')).toBeInTheDocument();
    expect(within(wiki).getByText('Core')).toHaveClass('badge');
    expect(within(wiki).getByRole('link', { name: 'Open' })).toHaveAttribute('href', wikiItem.url!);
    expect(wiki.querySelector('svg.icon')).not.toBeNull();
    const ext = document.getElementById('item-gutenberg_en_all')!;
    expect(ext).toHaveClass('unavailable');
    expect(within(ext).getByText('On external drive (not connected)')).toHaveClass('badge-warn');
    expect(within(ext).queryByRole('link', { name: 'Open' })).toBeNull();
    expect(screen.getAllByText('192 GB · as at 2025-11 · Public domain')).toHaveLength(1);
  });
});
