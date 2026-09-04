import { defineConfig, devices } from '@playwright/test';

export const MODE: 'dev' | 'fixture' = process.env.SOS_E2E === 'dev' ? 'dev' : 'fixture';
const baseURL = MODE === 'dev' ? 'http://127.0.0.1:8080' : 'http://127.0.0.1:4173';

export default defineConfig({
  testDir: 'e2e',
  testMatch: /.*\.spec\.ts/,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: [['list']],
  use: {
    ...devices['Desktop Chrome'],
    baseURL,
    viewport: { width: 853, height: 480 },
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 853, height: 480 } } }],
  webServer:
    MODE === 'fixture'
      ? {
          command: 'pnpm build && pnpm exec vite preview --port 4173 --strictPort',
          url: baseURL,
          reuseExistingServer: true,
          timeout: 240_000,
        }
      : undefined,
});
