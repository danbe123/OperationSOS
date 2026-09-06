/* The one place the box's own vocabulary is turned into a household's. The API names a source in its
 * own words — "playbook", "docs", "query" — and a household never has to learn any of them, so every
 * badge, chip and suggestion goes through here on its way to the screen. */

const WORDS: Record<string, string> = {
  playbook: 'Guide',
  playbooks: 'Guides',
  module: 'Guide',
  card: 'Quick card',
  'quick card': 'Quick card',
  page: 'Page',
  pages: 'Pages',
  doc: 'Document',
  docs: 'Documents',
  document: 'Document',
  documents: 'Documents',
  item: 'Library',
  library: 'Library',
  place: 'Place',
  places: 'Places',
  query: 'Search for this',
  zim: 'Offline copy',
  pmtiles: 'Map data',
  geojson: 'Map data',
  style: 'Map data',
  glyphs: 'Map data',
  sprites: 'Map data',
  mwm: 'Phone map',
  apk: 'Phone app',
  pdf: 'PDF',
  epub: 'Book',
};

/** The household's word for a source, a badge or a kind. Anything unknown keeps its own words. */
export function sourceWord(badge: string): string {
  const key = (badge ?? '').trim();
  const mapped = WORDS[key.toLowerCase()];
  if (mapped) return mapped;
  if (!key) return key;
  return key[0].toUpperCase() + key.slice(1);
}

/** A tile's one line. Guide summaries often open by repeating the title ("Nuclear war: what to do
 * …"), which is twenty tiles of dead text; strip the repeat, and show nothing rather than the title
 * twice. */
export function tileLine(title: string, summary?: string | null): string | undefined {
  const text = (summary ?? '').trim();
  if (!text) return undefined;
  const name = title.trim();
  let rest = text;
  if (name && rest.toLowerCase().startsWith(name.toLowerCase())) {
    rest = rest.slice(name.length).replace(/^[\s:·—–-]+/, '');
  }
  if (rest.length < 8) return undefined;
  return rest[0].toUpperCase() + rest.slice(1);
}
