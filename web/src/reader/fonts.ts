/** The book face, declared inside the reader's frame. A frame has none of the app's stylesheets, and
 * a stylesheet linked into it arrives when it arrives: the rules go in as text, at once, and the faces
 * are then asked for by name so the reader can wait for them before it places the book. */
const FAMILY = 'Source Serif 4';
const FILES: [string, string, string][] = [
  ['normal', '400', '/fonts/source-serif-4-v14-latin-regular.woff2'],
  ['italic', '400', '/fonts/source-serif-4-v14-latin-italic.woff2'],
  ['normal', '600', '/fonts/source-serif-4-v14-latin-600.woff2'],
  ['normal', '700', '/fonts/source-serif-4-v14-latin-700.woff2'],
];

/** `@font-face` rules in the shape epub.js's `addStylesheetRules` inserts: one selector, a list of declarations. */
export function fontFaceRules(origin: string): Record<string, Record<string, string>[]> {
  return {
    '@font-face': FILES.map(([style, weight, file]) => ({
      'font-family': `'${FAMILY}'`, 'font-style': style, 'font-weight': weight, 'font-display': 'swap',
      src: `url('${origin}${file}') format('woff2')`,
    })),
  };
}

/** Resolve once every face the book uses is in (or has failed, which is not the reader's problem). */
export async function fontsIn(doc: Document | null | undefined): Promise<void> {
  const fonts = doc?.fonts;
  if (!fonts) return;
  await Promise.all(FILES.map(([style, weight]) => fonts.load(`${style} ${weight} 18px '${FAMILY}'`).catch(() => undefined)));
  await fonts.ready;
}
