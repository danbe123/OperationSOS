import type { Page } from '@playwright/test';
import { test, expect } from './test';

/* A Gutenberg book in the app's own EPUB reader, in a real browser: it opens on its first chapter, a place
 * read to is written to the box after a pause (never one write per page), and opening the book again puts
 * the reader back where it was left. It is run in both ways of reading, scrolling (the default) and pages.
 * The box's side of that (the write and the read-back) is the fixture's; the reader's is what is under test.
 * Every fixture book is the same three-chapter EPUB, eight numbered paragraphs to a chapter. */

/** The first thing at the top of the reader's window, as its own words ("Chapter Two, paragraph 5."). Each
 * chapter is a frame of its own and several are on the screen at once, so "where is the reader" is the
 * topmost paragraph that is wholly in the window (the first column, when the book is in pages). Scrolling, a
 * place restored lands inside the paragraph it was saved at, a line or so down, so the topmost paragraph
 * that reaches into the window is the one. */
async function placeOnScreen(page: Page, flow: 'scrolled' | 'paginated' = 'paginated'): Promise<string | null> {
  const window = await page.locator('.epub-container').boundingBox();
  if (!window) return null;
  let first: { x: number; y: number; text: string } | null = null;
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    try {
      for (const item of await frame.locator('h1, p').all()) {
        const box = await item.boundingBox();
        if (!box) continue;
        const inside = flow === 'scrolled'
          ? box.y + box.height > window.y + 1 && box.y < window.y + window.height && box.x >= window.x - 1 && box.x + box.width <= window.x + window.width + 1
          : box.y >= window.y - 1 && box.y + box.height <= window.y + window.height + 1 && box.x >= window.x - 1 && box.x + box.width <= window.x + window.width + 1;
        if (!inside) continue;
        if (!first || box.x < first.x - 1 || (Math.abs(box.x - first.x) <= 1 && box.y < first.y)) {
          first = { x: box.x, y: box.y, text: ((await item.textContent()) ?? '').trim().replace(/\. The kettle.*$/, '.') };
        }
      }
    } catch {
      // the reader recycles its chapter frames as it scrolls: one that has gone is one that is not on the screen
    }
  }
  return first?.text ?? null;
}

/** Read on to a paragraph the way a reader does. Scrolling, the reader takes hold of the page and moves it,
 * so the paragraph is brought to the top of the window; in pages the arrow key turns until it is there. */
async function readOnTo(page: Page, flow: 'scrolled' | 'paginated', place: string) {
  if (flow === 'paginated') {
    for (let turns = 0; turns < 20; turns += 1) {
      if ((await placeOnScreen(page, 'paginated')) === place) return;
      await page.keyboard.press('ArrowRight');
      await page.waitForTimeout(250);
    }
    throw new Error(`never reached ${place}`);
  }
  // the chapters are loaded as the reader scrolls towards them, so scroll until the paragraph's frame exists
  const window = (await page.locator('.epub-container').boundingBox())!;
  await page.mouse.move(window.x + window.width / 2, window.y + window.height / 2);
  for (let scrolls = 0; scrolls < 20; scrolls += 1) {
    for (const frame of page.frames()) {
      if (frame === page.mainFrame()) continue;
      try {
        const item = frame.locator('p', { hasText: place });
        if ((await item.count()) > 0) return await item.evaluate((el) => el.scrollIntoView({ block: 'start' }));
      } catch {
        // a frame the reader has just recycled: look again after the next scroll
      }
    }
    await page.mouse.wheel(0, 300);
    await page.waitForTimeout(250);
  }
  throw new Error(`no frame ever held ${place}`);
}

for (const flow of ['scrolled', 'paginated'] as const) {
  test(`a book opens on its first chapter, remembers where it was read to, and comes back to it, ${flow}`, async ({ page, state }) => {
    await page.addInitScript((f) => localStorage.setItem('sos.reader.flow', f), flow);
    // the book has never been read here: the box has no place to hand back
    const first = page.waitForResponse((r) => r.url().endsWith('/api/books/gutenberg/2'));
    await page.goto('/book/gutenberg/2');
    expect(((await (await first).json()) as { position: unknown }).position).toBeNull();
    await expect(page.getByRole('heading', { level: 1, name: 'The Water-Babies' })).toBeVisible();
    await expect(page.getByText('Charles Kingsley')).toBeVisible();
    await expect.poll(() => placeOnScreen(page, flow)).toBe('Chapter One');

    // read on into the second chapter: the box is told where the reader is, after a pause (the front of the
    // book was told too, at 0%), and it is the place the reader is at, not the start of the book
    const saved = page.waitForRequest((r) => r.method() === 'PUT' && r.url().endsWith('/api/reading/gutenberg%3A2') && (r.postDataJSON() as { percent: number }).percent > 0);
    await readOnTo(page, flow, 'Chapter Two, paragraph 5.');
    const body = (await saved).postDataJSON() as { title: string; author: string; cfi: string; percent: number };
    expect(body).toMatchObject({ title: 'The Water-Babies', author: 'Charles Kingsley' });
    expect(body.cfi).toMatch(/^epubcfi\(/);
    expect(body.percent).toBeGreaterThan(20);   // some way into the second of three chapters
    await expect.poll(() => state.reading.get('gutenberg:2')?.cfi).toBe(body.cfi);
    await expect.poll(() => placeOnScreen(page, flow)).toBe('Chapter Two, paragraph 5.');

    // leave the book, and the Library lists it as the last thing viewed
    await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Library' }).click();
    const lastViewed = page.getByRole('region', { name: 'Last viewed' });
    await expect(lastViewed.getByRole('link', { name: /The Water-Babies/ })).toHaveAttribute('href', '/book/gutenberg/2');

    // open it again: the box hands back the place, and the reader opens on the paragraph it was left at
    const detail = page.waitForResponse((r) => r.url().endsWith('/api/books/gutenberg/2'));
    await lastViewed.getByRole('link', { name: /The Water-Babies/ }).click();
    expect(((await (await detail).json()) as { position: { cfi: string } }).position.cfi).toBe(state.reading.get('gutenberg:2')!.cfi);
    await expect(page.getByRole('heading', { level: 1, name: 'The Water-Babies' })).toBeVisible();
    await expect.poll(() => placeOnScreen(page, flow), { timeout: 15_000 }).toBe('Chapter Two, paragraph 5.');
    // and it stays there: the reader does not slip back once the book has settled
    await page.waitForTimeout(1500);
    expect(await placeOnScreen(page, flow)).toBe('Chapter Two, paragraph 5.');
  });
}

test('a book that was never opened starts at the front, and a book the catalogue lacks says so', async ({ page }) => {
  await page.goto('/book/gutenberg/3');
  await expect.poll(() => placeOnScreen(page, 'scrolled')).toBe('Chapter One');
  await page.goto('/book/gutenberg/999');
  await expect(page.getByText('Could not open this book')).toBeVisible();
  await expect(page.locator('.epub')).toHaveCount(0);
});
