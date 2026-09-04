import { describe, it, expect } from 'vitest';
import { resolveLink, classifyHref, parseKiwixContentPath, readerRoute, kiwixContentUrl } from '../src/links';

const BASE = 'http://10.42.0.1/s/grid-collapse';

describe('resolveLink: every scheme in the overview', () => {
  it.each([
    ['kiwix:wikipedia_en_all_maxi/A/Water', '/read/wikipedia_en_all_maxi/A/Water'],
    ['kiwix:nhs_uk/www.nhs.uk/conditions/dehydration/', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/'],
    ['doc:nrr-2025', '/doc/nrr-2025'],
    ['doc:nrr-2025#page=12', '/doc/nrr-2025#page=12'],
    ['map:?overlay=nuclear-sites&overlay=health', '/map?overlay=nuclear-sites&overlay=health'],
    ['map:', '/map'],
    ['playbook:nuclear-war', '/s/nuclear-war'],
    ['module:water', '/m/water'],
    ['card:cpr-adult', '/medical/card/cpr-adult'],
    ['page:pmr446', '/p/pmr446'],
  ])('%s -> %s', (href, expected) => {
    expect(resolveLink(href)).toBe(expected);
  });
  it('returns null for non-scheme and malformed links', () => {
    expect(resolveLink('/s/x')).toBeNull();
    expect(resolveLink('https://example.org')).toBeNull();
    expect(resolveLink('kiwix:no-slash')).toBeNull();
    expect(resolveLink('card:')).toBeNull();
  });
});

describe('classifyHref', () => {
  it('maps scheme links and same-origin app paths to app navigation', () => {
    expect(classifyHref('card:cpr-adult', BASE)).toEqual({ kind: 'app', to: '/medical/card/cpr-adult' });
    expect(classifyHref('/m/water', BASE)).toEqual({ kind: 'app', to: '/m/water' });
    expect(classifyHref('/doc/nrr-2025#page=3', BASE)).toEqual({ kind: 'app', to: '/doc/nrr-2025#page=3' });
    expect(classifyHref('http://10.42.0.1/map?overlay=health', BASE)).toEqual({ kind: 'app', to: '/map?overlay=health' });
  });
  it('turns Kiwix content URLs into reader routes, keeping search and hash', () => {
    expect(classifyHref('/kiwix/content/wikipedia_en_100_mini_2026-01/A/Water#Uses', 'http://10.42.0.1/kiwix/content/wikipedia_en_100_mini_2026-01/A/Main_Page'))
      .toEqual({ kind: 'app', to: '/read/wikipedia_en_100_mini_2026-01/A/Water#Uses' });
    expect(classifyHref('../A/Ice', 'http://10.42.0.1/kiwix/content/wikipedia_en_100_mini_2026-01/A/Water'))
      .toEqual({ kind: 'app', to: '/read/wikipedia_en_100_mini_2026-01/A/Ice' });
  });
  it('flags other origins and the kiwix external catcher as external', () => {
    expect(classifyHref('https://en.wikipedia.org/wiki/Water', BASE)).toEqual({ kind: 'external', href: 'https://en.wikipedia.org/wiki/Water' });
    expect(classifyHref('/kiwix/catch/external?source=https%3A%2F%2Fexample.org%2Fx', BASE)).toEqual({ kind: 'external', href: 'https://example.org/x' });
  });
  it('leaves in-page fragments, static files and mailto/tel to the browser', () => {
    expect(classifyHref('#Section', BASE)).toEqual({ kind: 'hash', hash: '#Section' });
    expect(classifyHref('/docs/core/docs/nrr-2025.pdf', BASE)).toEqual({ kind: 'other' });
    expect(classifyHref('/maps/packs/index.html', BASE)).toEqual({ kind: 'other' });
    expect(classifyHref('tel:999', BASE)).toEqual({ kind: 'other' });
  });
});

describe('kiwix path helpers', () => {
  it('round-trips ids and paths', () => {
    expect(parseKiwixContentPath('/kiwix/content/nhs_uk/www.nhs.uk/conditions/')).toEqual({ id: 'nhs_uk', path: 'www.nhs.uk/conditions/' });
    expect(parseKiwixContentPath('/kiwix/raw/nhs_uk/content/x')).toBeNull();
    expect(readerRoute('nhs_uk', 'www.nhs.uk/index.html')).toBe('/read/nhs_uk/www.nhs.uk/index.html');
    expect(kiwixContentUrl('nhs_uk', 'www.nhs.uk/index.html')).toBe('/kiwix/content/nhs_uk/www.nhs.uk/index.html');
  });
});
