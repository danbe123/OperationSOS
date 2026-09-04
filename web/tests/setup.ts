import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { JSDOM } from 'jsdom';

// jsdom has no layout engine and no canvas; stub the DOM APIs components call.
// Guarded because some test files (e.g. tests/theme/contrast.test.ts) run under the plain `node`
// environment, which has no DOM globals at all.
if (typeof window !== 'undefined') {
  Element.prototype.scrollIntoView = () => {};
  window.scrollTo = () => {};
  // maplibre-gl reads this at module load time (to spin up its worker) even in test files that never
  // touch the map screen, since router.tsx imports it transitively; jsdom has no Blob URL registry.
  window.URL.createObjectURL = window.URL.createObjectURL || (() => 'blob:stub');
  window.matchMedia =
    window.matchMedia ||
    ((query: string) =>
      ({ matches: false, media: query, onchange: null, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false }) as MediaQueryList);

  // This suite runs with no jsdom resource loader configured (real network fetches in tests would be
  // flaky and slow), so an <iframe src> pointing at a real path — the reader's Kiwix article frame —
  // never gets a parsed document: jsdom's navigation algorithm is synchronous only for `about:blank`,
  // and otherwise leaves contentDocument.documentElement null until a fetch that will never happen
  // resolves. A real browser instead keeps the frame's previous (initially blank) document in place
  // until the new one is ready, which is exactly what reader tests need in order to inject a fake
  // article's markup and fire `load`. Stand in a small same-shape Window/Document per <iframe> whenever
  // jsdom's own navigation hasn't produced a usable one. Its origin stays opaque (`about:blank`) — the
  // reader mocks `replaceFrameLocation` in these tests, so the frame never really navigates and its
  // `location.href` must stay a non-match for the reader's own "did the frame already get there"
  // check — but an opaque origin throws on `localStorage` access, which Vitest's own assertion matchers
  // touch when diffing a Window, so that one accessor is stubbed out below.
  const docDescriptor = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentDocument')!;
  const winDescriptor = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow')!;
  const standIns = new WeakMap<HTMLIFrameElement, Window>();
  function standInWindow(el: HTMLIFrameElement): Window {
    let win = standIns.get(el);
    if (!win) {
      win = new JSDOM('', { url: 'about:blank' }).window as unknown as Window;
      Object.defineProperty(win, 'localStorage', { configurable: true, get: () => undefined });
      Object.defineProperty(win, 'sessionStorage', { configurable: true, get: () => undefined });
      standIns.set(el, win);
    }
    return win;
  }
  Object.defineProperty(HTMLIFrameElement.prototype, 'contentDocument', {
    configurable: true,
    get(this: HTMLIFrameElement) {
      const real = docDescriptor.get!.call(this) as Document | null;
      return real?.documentElement ? real : standInWindow(this).document;
    },
  });
  Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
    configurable: true,
    get(this: HTMLIFrameElement) {
      const real = winDescriptor.get!.call(this) as Window | null;
      return real?.document?.documentElement ? real : standInWindow(this);
    },
  });
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
