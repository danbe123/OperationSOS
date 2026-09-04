import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// jsdom has no layout engine and no canvas; stub the DOM APIs components call.
// Guarded because some test files (e.g. tests/theme/contrast.test.ts) run under the plain `node`
// environment, which has no DOM globals at all.
if (typeof window !== 'undefined') {
  Element.prototype.scrollIntoView = () => {};
  window.scrollTo = () => {};
  window.matchMedia =
    window.matchMedia ||
    ((query: string) =>
      ({ matches: false, media: query, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false }) as MediaQueryList);
}

// qrcode draws on a canvas; unit tests only check that an image is rendered with the right payload.
vi.mock('qrcode', () => ({
  default: {
    toDataURL: vi.fn(async (text: string) => `data:image/png;base64,${btoa(text)}`),
    toString: vi.fn(async (text: string) => `<svg data-text="${text}"></svg>`),
  },
}));

afterEach(() => {
  if (typeof document === 'undefined') return;
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.classList.remove('kiosk');
  document.documentElement.style.removeProperty('--kb-height');
});
