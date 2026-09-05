// web/e2e/ai.spec.ts
// Runs only against the dev stack with a model loaded: SOS_E2E_AI=1 pnpm exec playwright test e2e/ai.spec.ts
import { expect, test, type APIRequestContext } from '@playwright/test';

const QUESTION = 'how do I make water safe to drink';
const DISCLAIMER = 'AI can be wrong. The library pages linked below are the source of truth.';

test.skip(!process.env.SOS_E2E_AI, 'set SOS_E2E_AI=1 with `make dev` running and a model in $SOS_CORE/models');
test.describe.configure({ mode: 'serial' });
test.setTimeout(240_000);

async function aiState(request: APIRequestContext): Promise<string> {
  return (await (await request.get('/api/ai/status')).json()).state;
}

async function ensureReady(request: APIRequestContext) {
  if ((await aiState(request)) !== 'ready') {
    await request.post('/api/ai/enable');
    await expect.poll(() => aiState(request), { timeout: 120_000, intervals: [1000] }).toBe('ready');
  }
}

test('shows the off card while the AI is off', async ({ page, request }) => {
  if ((await aiState(request)) !== 'off') await request.post('/api/ai/disable');
  await page.goto('/ai');
  await expect(page.getByText(/turn it on/i)).toBeVisible();
  await page.screenshot({ path: '../docs/screenshots/ai/01-off-card.png', fullPage: true });
});

test('answers from the library with citations and the disclaimer line', async ({ page, request }) => {
  await ensureReady(request);
  await page.goto('/ai');
  const box = page.getByRole('textbox');
  await box.fill(QUESTION);
  await box.press('Enter');
  await expect(page.getByText(/water/i).first()).toBeVisible({ timeout: 30_000 });   // retrieving: passages listed
  await page.screenshot({ path: '../docs/screenshots/ai/03-retrieving.png', fullPage: true });
  await expect(page.getByText(DISCLAIMER)).toBeVisible({ timeout: 180_000 });
  await expect(page.locator('a[href^="/read/"], a[href^="/p/"], a[href^="/m/"], a[href^="/s/"], a[href^="/doc/"], a[href^="/medical/card/"]').first()).toBeVisible({ timeout: 180_000 });
  await page.screenshot({ path: '../docs/screenshots/ai/04-answer-citations.png', fullPage: true });
});

test('shows the NHS verbatim block for a medicine name', async ({ page, request }) => {
  await ensureReady(request);
  await page.goto('/ai');
  const box = page.getByRole('textbox');
  await box.fill('paracetamol');
  await box.press('Enter');
  await expect(page.getByText('Find out how paracetamol for adults treats')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(DISCLAIMER)).toBeVisible({ timeout: 180_000 });
  await expect(page.getByText(/If someone is seriously ill or injured, call 999/)).toBeVisible({ timeout: 180_000 });
  await page.screenshot({ path: '../docs/screenshots/ai/05-verbatim-nhs.png', fullPage: true });
});

test('a second question while one is running is refused as busy', async ({ page, request }) => {
  await ensureReady(request);
  await page.goto('/ai');
  const secondBody = await page.evaluate(async (q) => {
    const init = { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ question: q, history: [] }) };
    const first = fetch('/api/ai/ask', init);
    await new Promise((r) => setTimeout(r, 1500));
    const second = await (await fetch('/api/ai/ask', init)).text();
    await (await first).text();
    return second;
  }, QUESTION);
  expect(secondBody).toContain('event: error');
  expect(secondBody).toContain('"code": "busy"');
  expect(secondBody).toContain('"retry_after"');
});

test('refuses a question the library cannot answer', async ({ page, request }) => {
  await ensureReady(request);
  await page.goto('/ai');
  const box = page.getByRole('textbox');
  await box.fill('what is the weather forecast for tomorrow');
  await box.press('Enter');
  await expect(page.getByText(/The library doesn't cover this|not backed by a library passage/)).toBeVisible({ timeout: 180_000 });
  await page.screenshot({ path: '../docs/screenshots/ai/07-refusal.png', fullPage: true });
});
