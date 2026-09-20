import type { AiEvent } from '../src/api/types';
import { sseBody } from '../tests/fixtures/api';
import { test, expect } from './test';

/* The assistant's screen against the fixture box: what it shows when it is off, how a streamed answer
 * is laid out (the NHS's own words first, the passages it read, the answer, its sources), and what it
 * says when the answer is not backed by the library or the slot is taken. The model itself is not here:
 * ai.spec.ts is the run against the dev stack with a real one. */

const WARNING = 'AI can be wrong. The library pages linked below are the source of truth.';
const ready = { state: 'ready' as const, model: 'fixture', message: null };

test('the assistant is off: the screen says so and points at System to turn it on', async ({ page }) => {
  await page.goto('/ai');
  await expect(page.getByText('The assistant is off.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Your question' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Turn it on in System' })).toHaveAttribute('href', '/system');
});

test('a question is answered from the library: the words first, the passages, the answer and its sources', async ({ page, state }) => {
  state.status = { ...state.status, ai: ready };
  await page.goto('/ai');
  await expect(page.getByText(WARNING)).toBeVisible();
  const field = page.getByRole('textbox', { name: 'Your question' });
  await expect(page.getByRole('button', { name: 'Ask' })).toBeDisabled();
  await expect(page.getByText('Type a question, then Ask.')).toBeVisible();
  await field.fill('how do I know if I am dehydrated');
  await field.press('Enter');

  await expect(page.getByText('You: how do I know if I am dehydrated')).toBeVisible();
  // the library's own words, verbatim, before anything the model wrote
  const verbatim = page.getByRole('region', { name: 'From the library, word for word' });
  await expect(verbatim.getByRole('link', { name: 'Dehydration' })).toHaveAttribute('href', '/read/nhs_uk/www.nhs.uk/conditions/dehydration/');
  await expect(verbatim).toContainText('Dehydration means your body loses more fluids than you take in.');
  await expect(verbatim).toContainText('as at 2026-08');
  // the answer, and every source it cites as a link into the box
  await expect(page.locator('.answer')).toHaveText('Signs include dark yellow urine and dizziness [1], and stored water helps [2].');
  const sources = page.getByRole('list', { name: 'Sources' });
  await expect(sources.getByRole('link')).toHaveText(['[1] Dehydration (NHS)', '[2] Water (Guides)']);
  await expect(sources.getByRole('link', { name: /^\[2\]/ })).toHaveAttribute('href', '/m/water');
  // the warning stays above it all, and the field is free for the next question
  await expect(page.getByText(WARNING)).toBeVisible();
  await expect(field).toBeEnabled();
  await expect(field).toHaveValue('');
  // a source opens in the app, not in a new page
  await sources.getByRole('link', { name: /^\[2\]/ }).click();
  await expect(page).toHaveURL(/\/m\/water$/);
});

test('an answer no library passage backs says so, and lists what was found instead', async ({ page, state }) => {
  state.status = { ...state.status, ai: ready };
  const events: AiEvent[] = [
    { event: 'retrieving', data: { query: 'weather', passages: [{ n: 1, title: 'Reading the weather', url: '/p/weather', source: 'playbooks', text: 'What the sky and the wind say about the next few hours.' }] } },
    { event: 'token', data: { text: 'I cannot tell you tomorrow.' } },
    { event: 'done', data: { answer: 'I cannot tell you tomorrow.', grounded: false, citations: [] } },
  ];
  await page.route('**/api/ai/ask', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(events) }));
  await page.goto('/ai');
  await page.getByRole('textbox', { name: 'Your question' }).fill('what is the weather forecast for tomorrow');
  await page.getByRole('button', { name: 'Ask' }).click();
  await expect(page.getByText('This answer is not backed by a library passage.')).toBeVisible();
  const found = page.getByRole('list', { name: 'Passages found' });
  await expect(found.getByRole('link', { name: '[1] Reading the weather (Guides)' })).toHaveAttribute('href', '/p/weather');
  await expect(page.getByRole('list', { name: 'Sources' })).toHaveCount(0);
});

test('a question the box is too busy for says so in words, and can be asked again', async ({ page, state }) => {
  state.status = { ...state.status, ai: ready };
  const events: AiEvent[] = [{ event: 'error', data: { code: 'busy', message: 'busy', retry_after: 20 } }];
  await page.route('**/api/ai/ask', (route) => route.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody(events) }));
  await page.goto('/ai');
  await page.getByRole('textbox', { name: 'Your question' }).fill('how do I make water safe to drink');
  await page.getByRole('button', { name: 'Ask' }).click();
  await expect(page.getByText('The AI is answering another question. Try again in 20 s.')).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Your question' })).toBeEnabled();
});

test('Find hands what was searched for to the assistant, ready to send', async ({ page, state }) => {
  state.status = { ...state.status, ai: ready };
  await page.goto('/search?q=water');
  await page.getByRole('region', { name: 'Ask the assistant' }).getByRole('link', { name: /Ask the assistant/ }).click();
  await expect(page).toHaveURL(/\/ai\?q=water$/);
  await expect(page.getByRole('textbox', { name: 'Your question' })).toHaveValue('water');
  await expect(page.getByRole('button', { name: 'Ask' })).toBeEnabled();
});
