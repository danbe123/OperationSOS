/** What the EPUB reader remembers about how you read, across every book: the text size, whether the
 * book scrolls or turns pages, and whether the chrome is out of the way. Storage is optional (a private
 * window, a kiosk profile with it blocked): a reader with no memory still reads. */
export type Flow = 'paginated' | 'scrolled';

export const FLOW_KEY = 'sos.reader.flow';
export const SIZE_KEY = 'sos.reader.size';
export const IMMERSED_KEY = 'sos.reader.immersed';

/** The sizes the Text size button cycles through, as a percentage of the reader's own base. */
export const EPUB_SIZES = [100, 125, 150];

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Storage is optional.
  }
}

export function storedFlow(): Flow {
  return read(FLOW_KEY) === 'scrolled' ? 'scrolled' : 'paginated';
}

export function storedSize(): number {
  const n = Number(read(SIZE_KEY));
  return EPUB_SIZES.includes(n) ? n : EPUB_SIZES[0];
}

export function storedImmersed(): boolean {
  return read(IMMERSED_KEY) === 'on';
}

/** Where a tap on the page landed: the left third turns back, the right third turns on, and the middle
 * is for the controls. `x` is the tap's offset within the page's visible width, `width` that width; a
 * width that is not known (a test, a frame not yet laid out) treats every tap as the middle. */
export function tapZone(x: number, width: number): 'previous' | 'next' | 'middle' {
  if (!(width > 0)) return 'middle';
  const share = x / width;
  if (share < 0.3) return 'previous';
  if (share > 0.7) return 'next';
  return 'middle';
}
