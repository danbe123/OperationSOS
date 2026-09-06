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
  /* Source ids as the engine and the assistant name them. Without these `sourceWord` merely
     capitalised them, so a citation read "[3] Cyber attack on infrastructure (Playbooks)" and a
     badge read "Nhs". */
  nhs: 'NHS',
  medical: 'Medical',
  wikipedia: 'Wikipedia',
  wikimed: 'Wikipedia medicine',
  practical: 'Practical',
  survival: 'Survival',
  reference: 'Reference',
  'uk-official': 'UK official',
  extended: 'Extra library',
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

/** The log's own suffixes. The engine tags every entry with where it came from — "(kiosk)",
 * "(phone)", "(drill)" — which is the box talking about itself. A household reads the same fact as
 * a place: on the box, on a phone, in the drill. */
export function eventTitle(title: string): string {
  return (title ?? '')
    .replace(/\s*\(kiosk\)\s*$/i, ' on the box')
    .replace(/\s*\(phone\)\s*$/i, ' on a phone')
    .replace(/\s*\(drill\)\s*$/i, ' in the drill');
}

/** The bulletin line as a household reads it. The engine names its own screens — "see the comms
 * module for your station" — on the one screen that is read from a doorway. */
export function bulletinWords(text: string): string {
  return (text ?? '')
    .replace(/,?\s*see the comms module for your station/i, '')
    .replace(/\bcomms module\b/gi, 'phone and radio pages')
    .trim();
}
