import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

const base = mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      setupFiles: ['tests/setup.ts'],
      css: false,
      restoreMocks: true,
      clearMocks: true,
    },
  }),
);

export default mergeConfig(
  base,
  defineConfig({
    test: {
      projects: [
        mergeConfig(base, {
          test: {
            name: 'jsdom',
            environment: 'jsdom',
            include: ['tests/**/*.test.{ts,tsx}'],
            exclude: ['tests/theme/contrast.test.ts'],
          },
        }),
        // contrast.test.ts only reads themes.css from disk via `new URL(..., import.meta.url)`; under
        // jsdom, Vitest rewrites that pattern's import.meta.url to the fake `http://localhost:3000/`
        // location, so it must run under the real (SSR) `node` environment to get a file:// URL.
        mergeConfig(base, {
          test: {
            name: 'node',
            environment: 'node',
            include: ['tests/theme/contrast.test.ts'],
          },
        }),
      ],
    },
  }),
);
