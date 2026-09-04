import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      // contrast.test.ts only reads themes.css from disk via `new URL(..., import.meta.url)`; under
      // jsdom, Vitest rewrites that pattern's import.meta.url to the fake `http://localhost:3000/`
      // location, so it must run under the real (SSR) `node` environment to get a file:// URL.
      environmentMatchGlobs: [['tests/theme/contrast.test.ts', 'node']],
      setupFiles: ['tests/setup.ts'],
      include: ['tests/**/*.test.{ts,tsx}'],
      css: false,
      restoreMocks: true,
      clearMocks: true,
    },
  }),
);
