import type { Locator } from '@playwright/test';
import { test, expect } from './test';
import { MEANING_QUERY } from './fixtures/search';

/** One result row by the word before its title and the title itself, as a household reads it. */
const resultRow = (group: Locator, source: string, title: string) => group.getByRole('link').filter({
  has: group.page().locator('.result-source', { hasText: new RegExp(`^${source}$`) }),
}).filter({ has: group.page().locator('.result-title', { hasText: new RegExp(`^${title}$`) }) });

test('Now -> Find -> search -> open an article in the reader', async ({ page }) => {
  // Now has no search field of its own: the rail's Find is the way to the search, and the field is its first row.
  await page.goto('/');
  await expect(page.getByRole('combobox', { name: 'Search' })).toHaveCount(0);
  await page.getByRole('navigation', { name: 'Sections' }).getByRole('link', { name: 'Find' }).click();
  await expect(page).toHaveURL(/\/search$/);
  const search = page.getByRole('combobox', { name: 'Search' });
  await search.fill('water');
  await search.press('Enter');
  await expect(page).toHaveURL(/\/search\?q=water$/);
  // Two groups: the box's own guidance first, then everything else from the library.
  await expect(page.getByRole('region', { name: 'From this box' })).toBeVisible();
  const library = page.getByRole('region', { name: 'From the library' });
  await expect(library.getByRole('listitem')).not.toHaveCount(0);
  // The source is a word before the title, and the whole row is the link.
  const row = resultRow(library, 'Wikipedia', 'Water');
  await expect(row).toHaveCount(1);
  await expect(row.locator('.result-source')).toHaveText('Wikipedia');
  await row.click();
  await expect(page).toHaveURL(/\/read\/wikipedia_en_100_mini_2026-01\/A\/Water$/);
  const frame = page.frameLocator('iframe[title="Article"]');
  await expect(frame.getByRole('heading', { name: 'Water' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 1, name: 'Water' })).toBeVisible();
});

test('a search for what is meant marks the rows it found by meaning "related", and the books are their own source', async ({ page }) => {
  await page.goto(`/search?q=${encodeURIComponent(MEANING_QUERY)}`);
  const own = page.getByRole('region', { name: 'From this box' });
  const library = page.getByRole('region', { name: 'From the library' });
  await expect(own.getByRole('listitem')).toHaveCount(2);
  await expect(page.getByText('5 results')).toBeVisible();

  // "related" is on the rows found by meaning, in both groups, and only on those.
  const related = page.locator('.result-via');
  await expect(related).toHaveCount(2);
  await expect(related.first()).toHaveText('related');
  await expect(related.first()).toHaveAttribute('title', 'Found by what the question means, not by its words');
  const found = resultRow(own, 'Page', 'Finding water');
  const byWords = resultRow(own, 'Page', 'Water disinfection');
  const article = resultRow(library, 'Wikipedia', 'Water');
  for (const row of [found, byWords, article]) await expect(row).toHaveCount(1);   // a count of none below would prove nothing
  await expect(found.locator('.result-via')).toHaveText('related');
  await expect(byWords.locator('.result-via')).toHaveCount(0);
  await expect(article.locator('.result-via')).toHaveCount(0);
  await expect(resultRow(library, 'Books', 'Robinson Crusoe').locator('.result-via')).toHaveText('related');

  // The Gutenberg catalogue is a source of its own: a word before the title, a chip with its count, and a link to the book.
  const book = resultRow(library, 'Books', 'The Water-Babies');
  await expect(book.locator('.result-source')).toHaveText('Books');
  await expect(book).toHaveAttribute('href', '/book/gutenberg/2');
  const sources = page.getByRole('group', { name: 'Filter by source' });
  await expect(sources.getByRole('button', { name: /^Books\s*2$/ })).toBeVisible();

  // Turning the Books chip on narrows the results to the books and puts the choice in the address.
  await sources.getByRole('button', { name: /^Books/ }).click();
  await expect(page).toHaveURL(/sources=books$/);
  await expect(sources.getByRole('button', { name: /^Books/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('2 results')).toBeVisible();
  await expect(page.getByRole('region', { name: 'From this box' })).toHaveCount(0);
  await expect(library.getByRole('link')).toHaveCount(2);
  // The chips keep their counts while a filter is on, so the others are still there to turn on.
  await expect(sources.getByRole('button', { name: /^Wikipedia\s*1$/ })).toBeVisible();
});
