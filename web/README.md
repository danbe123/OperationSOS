# Operation SOS frontend

React 19 + Vite. Served by Caddy over plain HTTP; used on the box's own screen (kiosk) and on phones over the hotspot.

## Commands (run in `web/`)

| Command | What it does |
|---|---|
| `pnpm install` | install dependencies (Node 22+, pnpm 10) |
| `pnpm vendor` | fetch the PDF.js prebuilt viewer into `public/pdfjs` (git-ignored; needed once, and after bumping `pdfjs-dist`) |
| `pnpm welcome`, `pnpm icons` | regenerate `public/welcome.html` and `public/icons/*.png` |
| `pnpm dev` | Vite on http://127.0.0.1:5173 proxying `/api`, `/kiwix`, `/maps`, `/docs` to the dev stack's Caddy on 8080 |
| `pnpm test` | Vitest unit and component tests |
| `pnpm lint` | eslint + `tsc --noEmit` |
| `pnpm build` | production bundle in `dist/` (refuses to run until `pnpm vendor` has been run) |
| `pnpm e2e` | Playwright in fixture mode: builds, previews on 4173, answers every backend request from `e2e/fixtures` |
| `SOS_E2E=dev pnpm e2e` | Playwright against the running dev stack (`make dev`, Caddy on 8080) |

Kiosk mode is `http://localhost/?kiosk=1` (persisted for the browser session). Themes: the button in every app bar; stored per device in `localStorage` (`sos.theme`).
