# Operation SOS — design spec

Date: 2026-09-03 (revised after multi-lens review the same day)
Status: approved design, revised
Research backing this spec: `docs/research/2026-09-03-research-brief.md`
Review findings applied: `docs/research/2026-09-03-spec-review-findings.md`

## 1. What this is

Operation SOS is an offline, UK-focused "end of the world" knowledge box. It runs on a Raspberry Pi 5 (8GB) with a touchscreen and a 500GB NVMe, plus an optional external USB drive. It broadcasts its own WiFi hotspot so phones and laptops can use it with no internet, no grid and no mobile network, and it shows the same interface on its own screen so it works when every phone is dead.

It is inspired by Project NOMAD (an x86 Docker knowledge server with a US-only catalogue) but shares no code with it. Operation SOS is Pi-native, hotspot-first, screen-first, and organised around UK scenarios rather than a library shelf.

### Goals

1. Everything needed to survive, heal, fix and rebuild in the UK after a catastrophe, readable offline from a phone or the box's screen.
2. Twenty scenario playbooks that tell someone what to do right now, over 72 hours, over a month and over years, with UK-specific detail.
3. One search box across everything: Wikipedia, NHS, manuals, maps, playbooks.
4. Full maps of the UK, the Republic of Ireland, the Isle of Man and the Channel Islands, with footpaths and scenario overlays, and contours and hillshade everywhere terrain data exists (Great Britain and Northern Ireland from Ordnance Survey and OSNI, the rest from Copernicus DEM).
5. An intuitive, themed frontend that works on a 7" touchscreen and on any phone.
6. An optional grounded AI assistant that only answers from the library and cites its sources.
7. Reproducible: one install script on a fresh Raspberry Pi OS, one sync command for content, and a dev profile that runs the whole stack on a PC.

### Non-goals (v1)

- Selling kits, publishing a disk image, or any distribution beyond the repo. Licence is recorded per item and never gates behaviour.
- Mesh radio (Meshtastic/MeshCore) integration.
- Multi-box sync or peer-to-peer replication.
- Any online service dependency at runtime.
- HTTPS on the hotspot (impossible offline without installing a private CA on every phone), so no service worker, PWA install prompt, phone geolocation, Web Share or clipboard API on phones.
- Plant or fungus identification from photos.

## 2. Users and scenarios

Primary user: the owner and whoever is with them. Secondary: anyone who joins the hotspot. No accounts. An optional admin PIN, set at install, gates exactly: power mode, ethernet mode, hotspot settings, updates, changing the PIN, and turning the AI on or off. Everything else is open.

### The 20 scenarios

Grounded in the UK National Risk Register 2025 and the owner's brief.

| # | Slug | Scenario |
|---|---|---|
| 1 | `nuclear-war` | Nuclear war: strategic strike on the UK, fallout, shelter, iodine |
| 2 | `nuclear-accident` | Nuclear accident or dirty bomb: plume from a UK site |
| 3 | `pandemic` | Lethal pandemic with no NHS capacity |
| 4 | `grid-collapse` | National grid collapse: weeks-long blackout, water pumps and comms down; UK specifics also cover regional storm outages (Arwen, Éowyn): 105, DNO lookup, Priority Services Register, rest centres, restoration timescales |
| 5 | `solar-storm` | Solar superstorm: grid, satellites and GPS gone |
| 6 | `emp` | EMP attack: electronics, vehicles and radios dead |
| 7 | `cyber-attack` | Cyber attack on critical infrastructure: water, banking, NHS, telecoms |
| 8 | `invasion` | Invasion or occupation: conventional war on UK soil, resistance, evacuation |
| 9 | `civil-unrest` | Civil unrest and breakdown of order: riots, martial law, civil war |
| 10 | `economic-collapse` | Economic collapse: currency failure, banks closed, hyperinflation, barter |
| 11 | `supply-chain` | Supply chain collapse: food, fuel and medicine shortages |
| 12 | `storms-flooding` | Severe storms, coastal storm surge and major river flooding |
| 13 | `severe-winter` | Prolonged severe winter: deep freeze, snow, no heating fuel |
| 14 | `heat-drought` | Heatwave, drought and water supply failure |
| 15 | `volcanic` | Volcanic ash and gas event (Icelandic Laki-style) |
| 16 | `chemical` | Chemical or industrial disaster: toxic plume, CBRN |
| 17 | `famine` | Agricultural collapse and famine: crop blight, livestock disease, fertiliser cut-off |
| 18 | `impact-winter` | Nuclear or impact winter: multi-year cold and dark |
| 19 | `terrorism` | Mass-casualty terrorism: marauding attack, bombing, poisoning |
| 20 | `long-rebuild` | Total collapse and the long rebuild: no state, years 1 to 10 |

### Shared modules

Written once, included by playbooks: `water`, `food`, `shelter-heat`, `medical`, `sanitation`, `power`, `comms`, `security-law`, `navigation`, `community`, `mental-health`, `radiation`, `evacuation`, `vehicles-fuel`, `tools-repair`, `growing-food`, `livestock`.

## 3. Hardware and storage

### Reference hardware

- Raspberry Pi 5, 8GB.
- Full-length (2280) NVMe carrier: Pimoroni NVMe Base (flat, stacks under the Pi; suits a printed case). 500GB NVMe, boot and core drive. PCIe stays at Gen 2 (the carrier's rating); `install.sh --pcie-gen3` opts into Gen 3 for owners who have tested their drive. Boot order is set once with `raspi-config` (Advanced, Boot Order, NVMe/USB).
- Official Active Cooler or equivalent fan. The printed case must have an intake and exhaust path; throttling in a sealed enclosure is the known unknown.
- Official 27W USB-C PSU.
- Screen: Raspberry Pi Touch Display 2 (7", DSI, natively 720x1280 portrait, about 210 DPI) inset in the printed case, rotated to landscape by the kiosk session (section 5). The connector is DSI-1 or DSI-2 depending on which Pi 5 port the ribbon uses; the panel is auto-detected on a Pi 5. Any HDMI touchscreen also works.
- External drive: self-powered USB 3 HDD or SSD, ext4, filesystem label `SOS-EXT`, 2TB minimum for the full extended list.
- Optional: 20,000mAh USB-C PD power bank (12 to 15 hours headless, roughly 8 to 10 with the screen lit; idle dimming recovers most of the difference), 250Wh LiFePO4 station (about two days).

### Storage layout

| Path | Drive | Holds |
|---|---|---|
| `/srv/sos/core/zim` | NVMe | core ZIM files |
| `/srv/sos/core/maps` | NVMe | PMTiles, styles, sprites, glyphs, overlay GeoJSON, `places.csv.gz`, phone packs |
| `/srv/sos/core/docs` | NVMe | PDFs and EPUBs plus `.txt` sidecars written by `sos index` |
| `/srv/sos/core/models` | NVMe | GGUF model files |
| `/srv/sos/extended/{zim,docs,media,video,books}` | USB | extended library |
| `/srv/sos/state` | NVMe | `sos.db` (SQLite), `library.xml`, `playbooks/` (Markdown source), `manifest/` (JSON source), `config/`, logs |
| `/srv/sos/web` | NVMe | built frontend |
| `/srv/sos/api` | NVMe | the `sos` Python package and its venv |

Filesystem: ext4 with `noatime` on both drives. No filesystem compression.

The box works fully with only `core`. Extended items are always listed in the library with a drive badge; when the drive is absent they are greyed out with the label "On external drive (not connected)", cannot be opened, and are excluded from search, suggest and AI retrieval until the next rescan finds them.

### RAM and CPU budget (8GB, four cores)

| Process | Approx RSS |
|---|---|
| kiwix-serve | 0.3 to 0.6GB |
| Chromium kiosk | 0.8 to 1.2GB |
| sos-api plus Caddy plus dnsmasq | 0.3GB |
| llama-server (Gemma 4 E2B Q4_K_M, 2.9GB file, 4K context, f16 KV) | 3.5GB, only when AI is on; `MemoryMax=4500M` |
| Jellyfin (optional) | 0.4 to 0.8GB; not enabled together with the AI on the 8GB board |
| OS and page cache | remainder |

llama-server runs at `Nice=10`, `CPUWeight=30`, `IOWeight=50`, `OOMScoreAdjust=500` so search, the kiosk and the hotspot pre-empt generation.

## 4. Networking

### Hotspot

- Interface `wlan0` in access-point mode via NetworkManager (`ipv4.method shared`), 2.4GHz, channel auto. SSID default `SOS`, open network. SSID and an optional WPA2 passphrase are configurable in System settings (PIN-gated).
- Address `10.42.0.1/24`. NetworkManager's shared-mode dnsmasq reads `/etc/NetworkManager/dnsmasq-shared.d/sos.conf` containing `address=/#/10.42.0.1`, so every name resolves to the box and `http://sos.box` works when the phone uses the box's DNS.
- Captive-portal detection: Caddy answers the probe paths (`/generate_204`, `/gen_204`, `/hotspot-detect.html`, `/library/test/success.html`, `/connecttest.txt`, `/ncsi.txt`, `/canonical.html`, `/success.txt`) with a `302` to `http://10.42.0.1/welcome`. That is a static page under 20KB with no app JavaScript: the SSID, one big line "Open http://10.42.0.1 in your browser (or http://sos.box)", a QR code of that URL, and two help lines: "If the page will not load, turn mobile data off" and "Tap Done or Cancel to leave this screen; the WiFi stays connected". The app itself is never served as the portal page, because the phone's portal webview is a throwaway sandbox. Every printed and on-screen instruction lists the IP address first and `sos.box` second.

### Ethernet

- Default: `eth0` is a DHCP client. Plug it into a home router to run updates; the box is also reachable on the home LAN at `http://sos.local` (mDNS via Avahi) while the hotspot keeps running.
- "Direct laptop link" toggle in System switches `eth0` to shared mode (`10.43.0.1/24`) so a laptop can plug straight in with no router. The toggle is remembered across reboots.

### Ports

| Port | Bind | Service |
|---|---|---|
| 80 | all | Caddy |
| 8000 | localhost | sos-api |
| 8090 | all (kiwix-serve refuses `127.0.0.1` on some systems; the hotspot firewall allows 80 only) | kiwix-serve |
| 8081 | localhost only, never proxied | llama-server |
| 8096 | all | Jellyfin (optional) |

## 5. Services

All services are systemd units on 64-bit Raspberry Pi OS Lite (Trixie, Debian 13, Python 3.13). No Docker. Binaries are pinned to versions in `install/versions.env`.

| Unit | What it runs | Notes |
|---|---|---|
| `caddy.service` | Caddy | Serves `/srv/sos/web` with SPA fallback to `index.html`; proxies `/api/*` to sos-api and `/kiwix/*` to kiwix-serve; serves `/maps/*` from `/srv/sos/core/maps` as static files with range requests, no compression and `Cache-Control: no-cache`; serves `/docs/core/*` and `/docs/extended/*` from the two `docs` directories; captive-portal redirects; `/welcome` static page. Hashed assets get `Cache-Control: public, max-age=31536000, immutable`; `index.html` gets `no-cache`. llama-server is never exposed |
| `kiwix-serve.service` | `kiwix-serve --library /srv/sos/state/library.xml --monitorLibrary --address all --port 8090 --urlRootLocation /kiwix --nosearchbar --nolibrarybutton --blockexternal` | `Restart=on-failure`, `RestartSec=2` (a yanked USB drive can SIGBUS it). Library file is regenerated by sos-api |
| `sos-api.service` | uvicorn running the FastAPI app from `/srv/sos/api/.venv` as user `sos` | See section 6 |
| `sos-llama.service` | `llama-server -m /srv/sos/core/models/${SOS_MODEL} --host 127.0.0.1 --port 8081 -c 4096 -t 4 -ngl 0 -fa on -np 1 --no-webui --reasoning off` with `EnvironmentFile=/srv/sos/state/config/ai.env` | Disabled by default; started and stopped by sos-api via `systemctl` (sudoers rule scoped to this unit). `ExecStartPre` sets the CPU governor to performance; `ExecStopPost` restores ondemand. KV cache is left at f16 (default): at 1 KV head and 28/35 layers sliding-window, the whole cache is only ~130MB, so quantizing it would save under 2% of `MemoryMax` while degrading the citation-marker tokens the hold-back logic depends on (2026-09-16 model review). Thinking is disabled via `--reasoning off`, not the deprecated `--reasoning-budget`/`enable_thinking` levers |
| `sos-kiosk.service` | `cage -- /usr/local/bin/sos-kiosk-app` | Owns tty1 itself (no getty autologin): `PAMName=login`, `TTYPath=/dev/tty1`, `Conflicts=getty@tty1.service`, `After=systemd-user-sessions.service`, `User=sos` (in groups `video`, `input`, `render`), `Restart=always`, `RestartSec=3`, `WantedBy=graphical.target`; the install script runs `systemctl set-default graphical.target`. `ExecStartPre` waits up to 60s for `http://localhost/api/status`. The wrapper script rotates the panel with `wlr-randr --output <DSI-n> --transform 90` (or 270 for the other case orientation), resets Chromium's `exit_type` and `exited_cleanly` preferences so no restore bubble appears after power loss, then runs `chromium --kiosk --ozone-platform=wayland --force-device-scale-factor=1.5 --noerrdialogs --no-first-run --overscroll-history-navigation=0 http://localhost/starting`. `/starting` is a static page in the web build that polls `/api/status` and replaces itself with `/?kiosk=1` |
| `srv-sos-extended.mount` | mount unit `What=/dev/disk/by-label/SOS-EXT Where=/srv/sos/extended Type=ext4 Options=noatime`, `BindsTo=` and `WantedBy=` the label's device unit | systemd mounts it on plug-in and unmounts on removal; no udev RUN scripts |
| `sos-extended-rescan.service` | `Type=oneshot RemainAfterExit=yes`, `ExecStart=sos storage-event add`, `ExecStop=sos storage-event remove`, `BindsTo=srv-sos-extended.mount`, `After=srv-sos-extended.mount sos-api.service`, `WantedBy=srv-sos-extended.mount` | `storage-event` only calls `POST /api/system/rescan` (remove regenerates `library.xml` first so `--monitorLibrary` drops the books before the unmount, and falls back to `umount -l` if busy) |
| `avahi-daemon.service` | mDNS `sos.local` | Only useful on a home LAN |
| `jellyfin.service` | Jellyfin | Optional, `install.sh --with-jellyfin`; library root `/srv/sos/extended/media` |

Backlight: a udev rule (`SUBSYSTEM=="backlight", ACTION=="add", RUN+="chgrp video ...brightness", RUN+="chmod g+w ...brightness"`) lets user `sos` write it. The Touch Display 2 exposes `max_brightness` 31; levels are scaled, idle dim uses level 10 and never 0. If no backlight device exists, `POST /api/kiosk/backlight` returns 501 and the kiosk page draws a translucent black overlay instead.

Map files are written to `/srv/sos/core/maps/.incoming/` and moved into place with `rename(2)`, so open viewers never see a partial file.

Boot order: network → kiwix-serve and sos-api → caddy → kiosk.

## 6. sos-api

Python 3.12 or newer (Trixie ships 3.13), FastAPI, uvicorn, httpx, pydantic and pydantic-settings, SQLite via `sqlite3` with FTS5, `python-frontmatter`, `markdown-it-py`, `jsonschema`, `pyproj` (PC-side only, for `build-maps`). No ORM. Text extraction on the Pi uses `pdftotext` from `poppler-utils`.

### Database (`/srv/sos/state/sos.db`)

- `library_items`: manifest fields plus `available`, `local_path`, `fts` (ZIM has a full-text index), `resolved_name`, `resolved_size`, `resolved_as_at` (from the Kiwix catalogue at sync time), `search_weight`, `suggest`.
- `fts_docs` (FTS5): `title, body, doc_id UNINDEXED, kind UNINDEXED, category UNINDEXED, scenarios UNINDEXED, page UNINDEXED, url UNINDEXED`, `tokenize='porter unicode61 remove_diacritics 2'`, ranked with `bm25(fts_docs, 5.0, 1.0)`. Rows: playbooks, modules, cards, pages (one row per section), library item titles, and one row per PDF page (`doc_id = <item>#p<N>`, body capped at 600 words).
- `fts_places` (FTS5): `name, kind UNINDEXED, lat UNINDEXED, lon UNINDEXED, region UNINDEXED, postcode UNINDEXED`, `tokenize='unicode61 remove_diacritics 2'`, `prefix='2 3 4'`. Loaded from `/srv/sos/core/maps/places.csv.gz` (about 2.5 million rows, 400 to 600MB) only when that file changes.
- `checklist_state`: `(playbook, item_id, checked, updated_at)`. Task lists inside included modules are stored under the including playbook.
- `notes`: `(id, kind ∈ {note, pin}, title, body, lat, lon, updated_at)`; `lat`/`lon` required for pins.
- `settings`: key/value (SSID, passphrase, PIN hash, power mode, eth mode, AI enabled, active model, default theme, `thermal_ai_off_c` default 80, idle minutes).
- `search_cache`: recent query → results, capped at 500 entries, flushed on rescan.

### Endpoints

All under `/api`. JSON unless noted. Errors are `{"detail": string}`.

| Method and path | Purpose |
|---|---|
| `GET /status` | Version, uptime, CPU temperature, load, memory, disks (core and extended: mounted, free, total), hotspot (SSID, IP, client count), eth mode, power mode, AI state (`off`, `starting`, `ready`, `error`, `off-thermal`, `busy`) and model, `pin_required`, `dev`, default theme |
| `GET /library` | All items grouped by category with availability and reader URL |
| `GET /library/{id}` | One item |
| `GET /search?q=&sources=&limit=` | Unified search (section 8); response carries `partial: true` if any source timed out |
| `GET /suggest?q=` | Title autocomplete from every available ZIM with `suggest: true` plus `fts_docs` prefix matches; at most 10 |
| `GET /playbooks` | List with slug, title, icon, summary, order |
| `GET /playbooks/{slug}` | Rendered HTML per section, included modules, checklist items with shared state and `updated_at`, overlays, sources |
| `PUT /playbooks/{slug}/checklist/{item_id}` | Set checked; returns the full list with `updated_at` per item |
| `DELETE /playbooks/{slug}/checklist` | Clear the list |
| `GET /modules/{slug}`, `GET /cards`, `GET /cards/{slug}`, `GET /pages/{slug}` | Rendered authored content |
| `GET /map/config` | Base styles, overlays, packs and availability |
| `GET /map/overlays` | Overlay catalogue only: `id, title, kind, url, default_on, scenarios_on, coverage, color, icon, available` |
| `GET /places?q=&limit=` | Prefix place search for the map (at least 3 characters, default 10, max 25) |
| `GET /notes?kind=`, `POST /notes`, `PUT /notes/{id}`, `DELETE /notes/{id}` | Shared notes and pins |
| `POST /ai/ask` | Body `{question ≤ 400 chars, history: [{role, content}]}`; Server-Sent Events, section 12 |
| `GET /ai/status`, `POST /ai/enable`, `POST /ai/disable` | AI control (PIN-gated when a PIN is set) |
| `POST /kiosk/backlight {level}` and `POST /kiosk/idle {state}` | Accepted only from 127.0.0.1, never PIN-gated |
| `POST /system/backlight {level}` | Same as kiosk backlight, for the System screen |
| `POST /system/power-mode {mode}` | `normal` or `low`; low stops AI and dims |
| `POST /system/eth-mode {mode}` | `client` or `direct` |
| `POST /system/hotspot {ssid, passphrase}` | Hotspot settings |
| `POST /system/rescan` | Regenerate `library.xml`, refresh availability and `fts` flags, flush `search_cache`. Seconds; never touches `fts_docs` or `fts_places`. Accepted only from 127.0.0.1 |
| `POST /system/update` and `GET /system/update/progress` | Runs `sos sync` for available tiers in the background and streams progress |
| `POST /system/pin {pin}` | Returns `{token, expires_in: 600}`; wrong PIN is 401 and rate-limited to five attempts a minute. When a PIN is set, `power-mode`, `eth-mode`, `hotspot`, `update`, `pin` change, `/ai/enable` and `/ai/disable` require `Authorization: Bearer <token>` |

A background task polls `/sys/class/thermal/thermal_zone0/temp` every 10 seconds. At or above `thermal_ai_off_c` with the AI on, it stops `sos-llama.service`, sets AI state `off-thermal`, and does not restart it. The threshold is editable in System so the path can be exercised on the box.

### Library file generation

`library.xml` is regenerated by walking `/srv/sos/core/zim` and, if mounted, `/srv/sos/extended/zim`, using `kiwix-manage add`. Items whose file is missing are marked unavailable rather than removed. A ZIM is searchable when its catalogue entry tags contain `_ftindex:yes` (`GET /kiwix/catalog/v2/entries?count=-1`).

Playbooks, modules, cards and pages are rendered on request from `/srv/sos/state/playbooks` with an in-memory cache keyed by file mtime. `sos index` parses the same files into `fts_docs`.

## 7. Content manifest

`manifest/core.json`, `manifest/extended.json`, `manifest/maps.json`, `manifest/overlays.json`, each `{"items": [...]}` validated against `manifest/schema.json`.

### Item schema

```json
{
  "id": "wikipedia_en_all_maxi",
  "title": "Wikipedia (English, with images)",
  "kind": "zim",
  "tier": "core",
  "category": "reference",
  "scenarios": [],
  "source": { "type": "kiwix", "name": "wikipedia_en_all_maxi" },
  "dest": "zim/wikipedia_en_all_maxi.zim",
  "size_bytes": 123980647016,
  "as_at": "2026-02",
  "licence": "CC BY-SA 4.0",
  "priority": 10,
  "reader_home": "A/Main_Page",
  "description": "One sentence shown in the library",
  "search_weight": 1.0,
  "suggest": true
}
```

- `kind`: `zim | pmtiles | geojson | pdf | epub | dir | model | mwm | apk | style | glyphs | sprites | places`.
- `tier`: `core | extended`.
- `category`: `playbooks | uk-official | medical | survival | reference | practical | maps | education | books | media | ai`.
- `source.type`: `kiwix` (`name`, resolved at sync time against `https://opds.library.kiwix.org/catalog/v2/entries?name=<name>` to the newest file; `size_bytes` and `as_at` are hints and the resolved values are stored in `library_items`), `url` (`url`, optional `sha256`, optional `mirrors[]`), `build` (`tool`, `artifact`, produced on the owner's PC and copied into place).
- Invariant for `kind: zim`: `dest == "zim/" + id + ".zim"`, enforced by the schema test; `sos sync` renames downloaded files to `dest`. kiwix-serve names a book after its filename stem, so `id` is the value used in `books.name=`, `content=`, `kiwix:<id>/<path>` links and the `/read/<id>/*` route; the reader iframe loads `/kiwix/content/<id>/<path>`.
- `search_weight` (default 1.0): 1.4 on every uk-official item and the NHS ZIMs, 1.2 on other medical ZIMs. `suggest` (default false): true on Wikipedia, WikiMed, the NHS ZIMs and iFixit.
- `as_at` is `YYYY-MM-DD`, or `YYYY-MM` when only a month is known, in manifests and front matter alike.
- Overlay items (`manifest/overlays.json`) add an `overlay` object: `{"id", "kind": "geojson" | "pmtiles" | "style-layer", "layer_id" (style-layer only), "default_on": bool, "scenarios_on": [slugs], "coverage": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"], "color", "icon"}`.
- `priority`: download order, lowest first.

### Core content (target about 200GB)

| Category | Items |
|---|---|
| uk-official | Prepare campaign (self-built ZIM `prepare_uk`), National Risk Register 2025 (`nrr-2025`), CMO national power-outage advice, UKHSA flooding and cold-weather guidance, FSA safe-foraging guidance, Building Regulations Approved Documents A to T, HSE guidance selection, gov.uk law summaries (knives, firearms, hunting, fishing, unauthorised encampments), legislation extracts (Theft Act s4(3), Wildlife and Countryside Act, CRoW, Deer Act, Firearms Act, CJA s139, Offensive Weapons Act, Civil Contingencies Act), Ofcom PMR446 and amateur licence documents, RSGB 2026 band plans, Ready Scotland community planning guide and templates, Wales Resilience Framework, Northern Ireland direct emergency pages, Local Resilience Forum contacts, Emergency Alerts explainer, Protect and Survive (1980) |
| medical | `nhs_uk` (self-built by `sos build-nhs`: conditions, symptoms, medicines, mental health, tests and treatments, pregnancy, live well; dated), `nhs_medicines` (Kiwix `nhs.uk_en_medicines`, lower-priority fallback), WikiMed (`wikipedia_en_medicine_maxi`), WikEM, mdwiki, MedlinePlus, zimgit-medicine, Where There Is No Doctor and Dentist, Ship Captain's Medical Guide (MCA), WHO Essential Medicines 2025, military medicine (FAS), Survival and Austere Medicine, Emergency War Surgery, FM 4-25.11 First Aid, Medical Sciences Stack Exchange (`medicalsciences.stackexchange.com_en_all`) |
| survival | zimgit water, food-preparation, knots, post-disaster; ready.gov; Appropedia; CD3WD Project (`cd3wdproject.org_en_all`); military survival manuals (FM 21-76 and FM 3-05.70); Nuclear War Survival Skills (`nwss`); FEMA nuclear detonation guidance; urban-prepper, trueprepper and lrnselfreliance crawls; energypedia; Low-tech Magazine; based.cooking and foss.cooking; USDA canning |
| reference | Wikipedia (`wikipedia_en_all_maxi`), Simple Wikipedia, Wiktionary (`wiktionary_en_all_nopic`, 8.5GB), Wikibooks, Wikivoyage, OpenStreetMap wiki |
| practical | iFixit (`ifixit_en_all`); Stack Exchange: diy, electronics, gardening, outdoors, mechanics, woodworking, cooking, homebrew, sustainability, ham, bicycles, biology, chemistry, physics, engineering, earthscience, pets; DevDocs as named ZIMs (`devdocs_en_python`, `devdocs_en_bash`, `devdocs_en_sqlite`, `devdocs_en_html`, `devdocs_en_css`, `devdocs_en_javascript`) |
| maps | section 9 |
| ai | Gemma 4 E2B Q4_K_M (primary, 2.9GB), Qwen 3.5 2B Q4_K_M (fallback, 1.3GB), Gemma 3 1B Q4_K_M (last resort) |

### Extended content

Gutenberg (`gutenberg_en_all`, 206GB), Stack Overflow (115GB) and all remaining Stack Exchange sites, Khan Academy (`khanacademy_en_all`, 180GB, 2023-03 build), TED-Ed, LibreTexts, OpenStax textbooks as `url` PDF items (no Kiwix ZIM exists), Survivor Library (252GB), video crawls (Canadian Prepper, S2 Underground and similar), Wikipedia in other languages if wanted, Jellyfin media folders for the owner's films, music and audiobooks.

## 8. Search

### Query construction

Tokenise on non-alphanumerics, lowercase, drop a bundled UK-English stopword and question-word list (what, how, should, do, if, my, can, is, the, and about 200 more). FTS5 MATCH is built as one double-quoted term per token joined by implicit AND, so `wi-fi`, `St John's`, `1:1 ratio` and bare `AND` never produce a syntax error. Kiwix gets the tokens space-joined. The reduced query is returned with the results.

### Sources

1. **Kiwix**: ZIMs are grouped by class (uk-official, NHS, medical, reference, practical, survival, extended) and one multi-book request per class is issued in parallel: `GET /kiwix/search?pattern=<q>&books.name=<a>&books.name=<b>...&format=xml&pageLength=8`. All books in one request must share a language (`eng`); a ZIM with another language gets its own request. Timeouts: 4 seconds for the reference class, 2 seconds for the others; a timed-out class is dropped and the response is marked `partial`. Only ZIMs with `fts = 1` and `available = 1` are queried. On boot and after rescan, sos-api warms the Wikipedia and NHS indexes with three canned queries. If latency is still poor in milestone 2, retrieval moves in-process with python-libzim.
2. **FTS5 docs**: playbooks, modules, cards, pages, PDF pages, library titles. BM25 with title weighting.
3. **Places**: enter unified search only when the whole query (or the query with a leading or trailing `near`/`in` removed) exactly equals a place name, or matches the UK postcode regex `^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$` or a district `^[A-Z]{1,2}\d[A-Z\d]?$` (case-insensitive). Prefix matching is only for `GET /places`.

### Merge and rank

Each hit appears in exactly one source list, so there is nothing to fuse: `score = w / (k + rank)` with `k = 5`, `rank` starting at 1, and `w` = the item's `search_weight` (playbooks and cards 1.6). With `k = 5` a playbook hit at rank 4 (0.178) still beats a Wikipedia rank-1 hit (0.167) but rank 5 (0.160) does not; a medical (1.2) rank-2 hit (0.171) beats Wikipedia rank 1, rank 3 (0.150) does not. These three comparisons are the fixed-input ranking test. Intent boosts from a keyword list: medical terms boost medical sources ×1.5; a place match applies ×2 to the place result. Exact title matches jump to the top of their source group. Output: flat ranked list with `source`, `badge`, `title`, `snippet`, `url`, `kind`, plus `groups` for the filter bar.

### Suggest

`/kiwix/suggest?content=<id>&term=<q>` on every available ZIM with `suggest: true`, plus `fts_docs` title prefix matches. At most 10.

## 9. Maps

### Base and terrain (built on the owner's PC by `sos build-maps`)

| Layer | Source | Output |
|---|---|---|
| Base map | Protomaps daily build pinned in `install/versions.env` (`20260902` today): `pmtiles extract https://build.protomaps.com/<YYYYMMDD>.pmtiles uk-ie.pmtiles --bbox=-11,49.1,2.2,61.2 --download-threads=8` (the build is already z0 to 15). Measured 3.2GB for the 49.5 edge; the 49.1 edge adds Jersey and Guernsey. The build fails if no zoom-12 tile covers St Helier (49.19, -2.11) or Lerwick (60.15, -1.15) | `uk-ie.pmtiles` |
| OS base | OS Open Zoomstack MBTiles (2,853MB) via the OS downloads API, `pmtiles convert` | `os-zoomstack.pmtiles` (GB only) |
| Contours | GB: OS Terrain 50 vector tiles (`terr50_mbtiles_gb.zip`, 1,071MB, layers `contour_line`, `spot_height`, `land_water_boundary`), `pmtiles convert`. NI, RoI, IoM, CI: `gdal_contour -i 10` over the EPSG:4326 warp of the non-GB DTMs, tippecanoe with the same layer and attribute names, merged with `tile-join` | `contours.pmtiles` |
| Hillshade | Mosaic in one CRS first: OS Terrain 50 ASCII grids (EPSG:27700), OSNI 50m DTM (Irish Grid), Copernicus DEM GLO-30 COGs for RoI, IoM and CI (later inputs win) → `gdalwarp -t_srs EPSG:3857 -tr 30 30` → `gdaldem hillshade -compute_edges -z 1 -az 315 -alt 45` → `gdal_translate -of MBTILES -co TILE_FORMAT=PNG8` → `gdaladdo` → `pmtiles convert` | `hillshade.pmtiles` |
| Styles, sprites, glyphs | Protomaps styles generated with `@protomaps/basemaps` (`light` for Field and `black` for Mono), the package major pinned to the tile schema of the pinned build; `protomaps/basemaps-assets` sprites and Noto Sans glyphs vendored. OS Open Zoomstack Outdoor (Field) and Night (Mono) styles rewritten with jq to the local PMTiles source, local sprites and glyphs, and `Arial Unicode MS Regular` removed from every `text-font` stack; the repo's Source Sans Pro and Open Sans glyphs vendored; every `source-layer` in the style asserted present in the tiles | `styles/`, `sprites/`, `fonts/` |
| Places | OS Open Names CSV (GB) with `LOCAL_TYPE` in City, Town, Village, Hamlet, Other Settlement, Postcode, Named Road, road sections collapsed to one row per name and populated place, `GEOMETRY_X/Y` transformed from EPSG:27700 with pyproj; plus `osmium tags-filter n/place=city,town,village,hamlet,suburb,locality` over the Britain and Ireland PBF for NI, RoI, IoM and CI | `places.csv.gz` (`name, kind, lat, lon, region, postcode`) |
| Phone packs | Organic Maps `.mwm` for all 24 ids (17 `UK_*`, 4 `Ireland_*`, Isle of Man, Jersey, Guernsey) from `https://cdn.organicmaps.app/maps/<v>/<id>.mwm`, `<v>` and the id list read from `data/countries.json` at build time and pinned in `install/versions.env` with the matching Android APK from GitHub Releases | `packs/` with an index page that says: install the APK first; copy `.mwm` files from a PC over USB into `Android/data/app.organicmaps/files/<v>/` (Android 11+ blocks browser writes there); the ethernet direct-laptop link is the intended route; iOS is not supported |

OSM input for everything below: Geofabrik `europe/britain-and-ireland-latest.osm.pbf` (2.4GB; its extent includes IoM and CI).

### Overlays (`manifest/overlays.json`)

| id | Title | Source and build | Kind | Coverage |
|---|---|---|---|---|
| `footpaths` | Footpaths and rights of way | `osmium tags-filter w/highway=path,footway,bridleway,track,cycleway,steps` → `osmium export -f geojsonseq --geometry-types=linestring` keeping `highway, designation, name, prow_ref, sac_scale, trail_visibility, foot, access, surface` → tippecanoe `-Z10 -z15`, designated rights of way from z10 and everything else from z13; styled by `designation` (public_footpath, public_bridleway, restricted_byway, byway_open_to_all_traffic, core_path) on both bases | pmtiles | all |
| `access-land` | Open access land | Natural England CRoW layer (England), NRW open access land (Wales); Scotland's right of responsible access is text in the navigation module | geojson | england, wales |
| `flood-zones` | Flood zones | EA Flood Map for Planning zones 2 and 3 (England), NRW Flood Map for Planning zones 3 and 2 (Wales, two FeatureServer layers), SEPA river and coastal medium-likelihood extents (Scotland), OPW community-scale river 1-in-100 and coastal 1-in-200 extents (RoI, CC BY-NC-ND); DfI's NI extents are not open data. Each source is one `ogr2ogr -f FlatGeobuf -t_srs EPSG:4326` and one tippecanoe layer `flood_<region>[_<tag>]` (tags z2, z3, river, coastal; source grammar `url[|layer][#tag]` in `install/versions.env`, several per region) | pmtiles | england, wales, scotland, roi (`coverage_note` says why NI is missing) |
| `health` | Hospitals, pharmacies, GP surgeries | `nwr/amenity=hospital,pharmacy,doctors,clinic` → `osmium export` → `ST_PointOnSurface` via ogr2ogr; every OSM overlay keeps its own tag allow-list (`OsmOverlay.tags`, map places spec section 5: here `name, amenity, healthcare, emergency, beds, operator, phone, website, opening_hours, wheelchair, dispensing`) | pmtiles (over 5MB) | all |
| `fuel` | Fuel stations | `nwr/amenity=fuel`, same pattern | geojson | all |
| `water` | Reservoirs, water works and springs | `nwr/landuse=reservoir nwr/water=reservoir nwr/man_made=water_works nwr/natural=spring` | pmtiles (over 5MB) | all |
| `rail` | Railway stations | `nwr/railway=station` | geojson | all |
| `nuclear-sites` | Nuclear sites | Hand-authored GeoJSON: every civil nuclear power station (operating and decommissioning), Sellafield, AWE Aldermaston, AWE Burghfield, HMNB Clyde Faslane, RNAD Coulport, HMNB Devonport, Barrow-in-Furness, Rosyth, Dounreay, Harwell, Winfrith, Springfields, Capenhurst | geojson | all |
| `chemical-sites` | Major chemical and fuel sites | `nwr/industrial=chemical,refinery,oil` plus a hand-authored list | geojson | all |
| `airports` | Airports and airfields | `nwr/aeroway=aerodrome`, polygons kept, tags `name, aeroway, aerodrome, aerodrome:type, icao, iata, operator, surface, military` | pmtiles | all |
| `military` | Military bases and land | `nwr/military=* nwr/landuse=military`, polygons kept, tags `name, military, landuse, operator, description, access` | pmtiles | all |

Any overlay whose GeoJSON exceeds 5MB is tiled with tippecanoe and declared `pmtiles`. `scenarios_on` is derived at `sos index` from playbook `overlays:` front matter; overlays.json holds the static fields. The chip for an overlay carries "No data for …" from `coverage` in its title, or the manifest's `coverage_note` when a region is missing for a reason worth saying (NI flood maps are not open data; Scotland needs no access-land layer).

### Viewer

MapLibre GL JS with the `pmtiles` protocol reading from `/maps/*` via range requests. There is one base for the viewer, the OSM Protomaps style for the current theme (the OS Zoomstack tiles and styles stay in the build for a later decision; nothing in the interface offers them). A theme switch uses `map.setStyle(next, {transformStyle})` carrying overlay, contour and hillshade sources and layers across. On `EtagMismatch` the PMTiles source is re-created rather than surfacing an error. Features: a chip row above the map with one chip per overlay plus Contours and Hillshade (map places spec, 2026-09-07), a hover tooltip with the name and type, a place card on tap (what it has, distance and walking time from home or the map centre, "what to expect here" from `playbooks/map/places.yaml` via `GET /api/map/places`, route, pin and nearby actions), place search (`/api/places`), pins saved to the box (`notes` kind `pin`), measure (distance and bearing), grid reference readout for the map centre and a tapped point (proj4 with the OSGB36 `towgs84` Helmert parameters, two letters plus 6 or 8 figures; Irish Grid EPSG:29903 over NI and RoI; lat/lon only over the Channel Islands), "Locate me" on the kiosk only (phones get a note that GPS is blocked over HTTP and are offered postcode, place or grid-reference entry and the phone map packs), share-a-place as selectable text and a QR code of `/map?lat=&lon=&z=&label=`, and print (map rendered to an image with `preserveDrawingBuffer`, printed with scale bar, grid reference and legend). `/map` accepts repeatable `overlay=<id>`, which is what `map:` links expand to.

## 10. Playbooks and authored content

Location: `playbooks/scenarios/<slug>.md`, `playbooks/modules/<slug>.md`, `playbooks/cards/<slug>.md`, `playbooks/pages/<slug>.md`. Front matter schema in `playbooks/schema.json`.

### Front matter (scenarios)

```yaml
---
id: nuclear-war
title: Nuclear war
icon: radiation
order: 1
summary: A nuclear strike on the UK. Fallout, shelter, water, radiation sickness.
modules: [radiation, water, shelter-heat, medical, sanitation, comms, evacuation]
overlays: [nuclear-sites, health, water]
reviewed: 2026-09-10
sources:
  - title: National Risk Register 2025
    doc: nrr-2025
    url: https://assets.publishing.service.gov.uk/media/67b5f85732b2aab18314bbe4/National_Risk_Register_2025.pdf
    as_at: 2025-01-16
  - title: Nuclear War Survival Skills
    doc: nwss
---
```

A `sources` entry must have `doc:` or `kiwix:` if the source is in the manifest; `url` is provenance only and is never rendered as a link. `reviewed` is the owner's sign-off date. Modules, cards and pages have `id, title, icon, order, summary` (modules also `sources`) and free headings.

### Body

Scenario bodies contain exactly, in order: `## Right now`, `## First 72 hours`, `## First month`, `## Long term`, `## UK specifics`, `## Checklist`, `## Go deeper`; all non-empty. `## Checklist` contains only task-list lines; an item's id is the slug of its text unless the line ends with `{#id}`. `modules:` is the declaration; the renderer inserts each module where `{{module:<slug>}}` appears, and the validator errors if a listed module has no include or an include names an unlisted module.

### Link scheme

- `kiwix:<id>/<path>` opens the reader at that article.
- `doc:<id>` opens a PDF or EPUB; `doc:<id>#page=<n>` opens at a page.
- `map:?overlay=nuclear-sites&overlay=health` opens the map with overlays on.
- `module:<slug>`, `card:<slug>`, `page:<slug>`, `playbook:<slug>` navigate within the app.

### Validation

`sos validate-playbooks` (CI) checks front matter against the schema, that the seven headings are present, ordered and non-empty, that every `kiwix:`, `doc:`, `module:`, `card:`, `page:` and `playbook:` target id exists in the manifest or playbook set, that `map:` overlays and `overlays:` entries exist in `manifest/overlays.json`, that module declarations and includes agree, that checklist ids are unique within a playbook, and that every `sources[].doc` or `kiwix:` resolves (warn on `url`-only sources). `sos validate-playbooks --deep` (on the box after `sos sync`) also requests every `kiwix:` path from kiwix-serve and every `doc:` file from disk and fails on any non-200 or missing file. Rewording a checklist item without an explicit id changes its id and resets its state; `playbooks/README.md` says so.

### Medical quick cards

One screen each: the title and first three steps fit without scrolling at 853x480 CSS px and at 360px phone width; later steps scroll. Large type, numbered steps, red warnings, when to stop or escalate, source. Cards: CPR adult, CPR child, severe bleeding, choking, burns, hypothermia, heat stroke, broken bones, radiation sickness, chemical exposure, childbirth, dehydration and rehydration solution, wound cleaning and infection, shock, drowning, seizures, anaphylaxis, carbon monoxide poisoning (generators, BBQs, stoves indoors), stroke (FAST), heart attack, unconscious but breathing (recovery position), low blood sugar, asthma attack.

### Comms and reference pages

`pmr446` (channels 1 to 16, 446.00625 to 446.19375 MHz, CTCSS table), `amateur-bands`, `uk-numbers` (105, 999, 111, Floodline 0345 988 1188, Priority Services Register), `what-still-works` (Digital Voice battery limits, mast batteries, FM and DAB, Emergency Alerts), `household-plan`, `water-disinfection` (UK thickened bleach versus NaDCC tablets), `mains-electricity` (230V, ring mains, RCDs), `solar-islanding`, `knife-firearms-law`, `foraging-law`, `ticks-adders`, `about-sos`.

### Authoring process

Playbooks and cards are drafted with AI assistance from the cited sources, then reviewed by the owner. Every factual claim that matters (a dose, a distance, a time, a law) carries an inline citation to a manifest item and page so the reader can check it.

## 11. Frontend

React 19 with Vite, TypeScript, React Router. Static build served by Caddy over plain HTTP. No service worker (not a secure context on the hotspot); returning phones load the shell from HTTP cache. A web manifest is still shipped so "Add to Home Screen" gets the SOS icon and name.

### Design rules

- Kiosk layouts are designed and tested at 853x480 CSS px (1280x720 at scale 1.5), which makes 48px targets about 8.7mm and 18px text about 3.3mm on the 7" panel. Phone layouts at 360 to 430px wide.
- Touch targets at least 48px. Body text at least 16px on phones and 18px on the kiosk.
- Every quick card, every scenario's Right now tab, the map and the Connect a phone panel are at most two taps from Home; everything else is reachable from the search bar, which is present on every screen.
- Every icon has a word next to it. Warnings use a colour and a symbol, never colour alone.
- Scanlines, glow, bevels and the display face apply only to app chrome and headings. Body text, quick cards, checklists and the Right now tab use the humanist sans with no overlay and no text shadow, at a contrast of at least 7:1, in every theme.

### Themes

CSS custom properties on `:root[data-theme]`, chosen from a theme button on every screen, stored in `localStorage` per device, with a box-wide default in settings. Two themes, on the owner's direction of 2026-09-06 ("i only want the light theme, and a black and white power saving one"); the dark-green `vault` and the red `blackout` are gone. All fonts bundled locally (OFL: VT323 for the display face, Inter for body, Source Serif 4 for Field headings).

| Theme | Look |
|---|---|
| `field` (default) | Field manual: paper and khaki, black text, red warnings, serif headings. Sunlight-readable and used as the print stylesheet |
| `mono` | White on pure black, no hue anywhere: the three states are separated by luminance and each carries its symbol. Night vision, and an OLED phone draws nothing for a black pixel — the cheapest screen the box has to read |

The reader injects a per-theme stylesheet into the Kiwix document on every load: `mono` sets a black background, white text, underlined links and `img{filter:brightness(.55)}` (`.35` in dim); `field` leaves the ZIM's own light styling. The PDF viewer chrome follows the theme (inverted page in `mono`).

### Kiosk mode

Detected via `?kiosk=1` on the launch URL and persisted in `sessionStorage`.

- A persistent Home button in the app bar. Print buttons are hidden.
- **Keyboard**: a bottom-docked panel about 210 CSS px tall that reduces the layout viewport (not an overlay). The focused field scrolls into view above it and search suggestions render between the field and the keyboard. Layouts: QWERTY with a symbols page and a numeric pad chosen by `inputmode`. Keys at least 64 CSS px wide; Enter submits the form; Done blurs and hides it. It types by calling the native `HTMLInputElement` value setter then dispatching an `input` event so React controlled inputs update, and attaches focus listeners to the reader iframe document so forms inside ZIM content work.
- **Idle**: after 5 minutes without touch (configurable) the backlight drops to the idle level and a translucent "Touch to wake" overlay appears; the page underneath does not change. The first touch while dimmed is consumed by the overlay. Return to Home happens only after 30 minutes idle (configurable) and never while a quick card or a Right now tab is open.
- **Status strip**: SSID, `http://10.42.0.1`, `http://sos.box`, external drive state, CPU temperature, and a **Connect a phone** button that opens a full-screen panel with two QR codes each at least 200 CSS px (the `WIFI:` join code and the URL), the SSID and both addresses in 32px text.

### Screens

| Route | Screen |
|---|---|
| `/` | Home: search bar; the five big tiles in this order Medical, Maps, Library, Phone and radio, Plan (two columns on phones, above the fold); then the "What is happening?" scenario grid (20 tiles); status strip. Home scrolls |
| `/s/:slug` | Scenario playbook: section tabs, inline modules as accordions, shared checklist ("n of m done, last change 12 min ago", tick time per item, Reset list with confirm, optimistic ticks that revert with a notice on failure, refetched on focus and every 15 seconds), print (all sections expanded, modules open, checklist boxes with ticks and times, sources and as-at dates), Go deeper list |
| `/m/:slug` | Module standalone |
| `/search?q=` | Results with source badges and filter chips; suggestions while typing; `partial` notice |
| `/read/:id/*` | Reader: same-origin iframe to `/kiwix/content/<id>/<path>` with `sandbox="allow-same-origin allow-scripts allow-forms"`. On each load the app attaches a capture-phase click listener to the iframe document: links to `/kiwix/content/...` become `navigate("/read/<id>/<path>")` and the article loads with `contentWindow.location.replace()` (`iframe.src` is set once only, so browser history holds one entry per article and the app URL always matches the screen); links to `http(s)://` or `/kiwix/catch/external` show an in-app notice "Not in the library (needs the internet)"; `target` and `window.open` are ignored. App bar: back, home, text size (style injected into the iframe), open in library. Print calls `iframe.contentWindow.print()` |
| `/doc/:id` | Bundled PDF.js viewer (page thumbnails, text search, pinch zoom, `#page=n` deep links) and a bundled EPUB reader. The browser's native PDF plugin is never used |
| `/medical` | Quick cards grid, NHS A to Z (conditions, medicines) into the `nhs_uk` reader, medical library |
| `/medical/card/:slug` | One card, extra-large type |
| `/map` | Section 9 |
| `/library` | Categories, item cards with kind, size, as-at, tier, availability and drive badge |
| `/radio` and `/p/:slug` | Comms pages |
| `/p/household-plan`, `/notes` | Superseded by the no-setup cut (`2026-09-07-no-setup-design.md`): the household plan template is now a content page (`/p/household-plan`, covered by `/p/:slug` above); shared notes and the pins list moved to `/notes` |
| `/ai` | Assistant when AI is ready; otherwise a card explaining how to turn it on |
| `/system` | Status, storage, hotspot settings, ethernet mode, power mode, backlight, AI toggle, thermal threshold, update progress, theme default, admin PIN |
| `/starting`, `/welcome` | Static pages in the build (kiosk boot page; captive-portal landing page) |

## 12. AI assistant

Off by default. Enabled via `POST /ai/enable` from System (PIN token if a PIN is set). Low power mode and the thermal watchdog disable it.

### Runtime

llama-server from a native llama.cpp build made on the Pi: `cmake -S . -B build -DGGML_NATIVE=ON -DGGML_CPU_KLEIDIAI=ON -DLLAMA_BUILD_TESTS=OFF && cmake --build build --config Release -j4` (native detection yields `armv8.2-a+dotprod+fp16`; never `+i8mm`, the Cortex-A76 lacks it). Unit flags in section 5. sos-api calls `POST /v1/chat/completions` with `stream: true`, `cache_prompt: true`, `max_tokens: 400`, `temperature: 0.2`; thinking is disabled at the server (`--reasoning off`), not per-request. Readiness is `GET /health` returning 200. Measured on a Pi 5 8GB with this exact model and quant (2026-09-16 model review, an idle board): about 28 to 32 tokens per second prompt processing and 5.97 generation, so a 1,500-token prompt gives roughly 50 seconds to first token and a 200-token answer about 33 seconds more; the UI shows progress for both phases. `Q4_K_M` is not the format `GGML_CPU_KLEIDIAI` accelerates (it covers `Q4_0`/`Q8_0`/`F16` only); Google's official QAT `q4_0` GGUF is the candidate to `llama-bench` against it on the box, and `--spec-type ngram-mod` or Gemma 4's own MTP drafter (`--spec-type draft-mtp`) are free-or-cheap ways to buy generation speed back if the milestone 6 gate needs it. Concurrency: `-np 1` and a single asyncio lock in sos-api; a second question while one is running gets `error {code: "busy", retry_after}` at once.

### Token budget (context 4096)

Counted with llama-server `POST /tokenize` (fallback 4 characters per token): system prompt at most 250, passages 3 × 400, question at most 150 (400 characters), history trimmed oldest-first to what remains under a hard prompt cap of 2,000 tokens, leaving at least 1,000 for the answer. The `verbatim` excerpt is shown in the UI only and is not part of the prompt.

### Flow for `POST /ai/ask`

1. Build the reduced query (section 8) keeping at most six content terms; FTS5 uses `"t1" OR "t2"` ranked by bm25; if fewer than three non-place results come back, retry with the three longest terms.
2. **Health router**: if the reduced query matches an `nhs_uk` article title or a quick-card title (exact, or a suggest or `fts_docs` prefix hit within edit distance 2), emit `verbatim {title, url, paragraphs[2], as_at}` for that page first. A keyword-only medical match emits nothing; it applies the ×1.5 boost and forces the disclaimer line.
3. Take the top three non-place results. ZIM articles are fetched from `GET /kiwix/raw/<id>/content/<path>` (no injected taskbar); keep `<main>` or `#maincontent` if present, else `<body>`; remove `nav, header, footer, aside, script, style, noscript, [role=navigation], .nhsuk-header, .nhsuk-footer, .nhsuk-skip-link`; convert to paragraphs; choose the best 400-token window around the query terms. For PDF pages, the matching page's body trimmed around the first query term.
4. Emit `retrieving {query, passages: [{n, title, url, source, text}]}`. If no passage is available, skip the model and emit `done {answer: "The library doesn't cover this.", grounded: false, citations: []}`.
5. Prompt: the assistant answers only from the numbered passages, cites them as `[1]` `[2]` `[3]`, says "The library doesn't cover this" when they don't answer, uses British English and UK terms (999, 111, 105, paracetamol), never invents doses or laws.
6. Stream `token {text}`. While streaming, hold back text from a `[` until the matching `]` (or 6 characters) so a citation that does not map to an emitted passage is dropped before the client sees it. A `: ping` comment goes out every 10 seconds while waiting. Overall timeout 180 seconds → `error {code: "timeout"}`.
7. Emit `done {answer, grounded, citations: [{n, title, url, source}]}`; `answer` is the final text and the client replaces its streamed buffer with it; `grounded` is false when no citation survived, and the UI then says "This answer is not backed by a library passage" and lists the passages instead.

Events in order: optional `verbatim`; `retrieving`; `token` repeated; exactly one of `done` or `error {code, message}`.

### UI

Every answer carries the line "AI can be wrong. The library pages linked below are the source of truth." Verbatim NHS or card content is visually separate from AI text. No image input. Progress is shown for prompt processing and generation.

### Evaluation

`tools/eval/questions.jsonl`, one object per line: `{id, question, kind: "answer" | "refuse" | "health", expected: [{item, path}], notes}`; about 50 answer, 10 refuse and 10 health cases. `sos eval --retrieval-only` runs on the PC and in CI with no model and fails below 80% retrieval@3 (an expected item and path among the three passages) on the fixture library. `sos eval` on the Pi additionally generates answers and writes `tools/eval/runs/<date>-<model>.jsonl` with per-question time to first token, tokens per second, peak RSS, `grounded`, and the answer for owner review. Gates: retrieval@3 at least 0.80, refusal rate at least 0.90, `verbatim` hit rate on health cases at least 0.90, no metric more than 5 points below the previous run. Both modes run before any model, prompt or retrieval change lands.

## 13. Install and tools

### `install/install.sh`

Run as root on a fresh 64-bit Raspberry Pi OS Lite with the NVMe as boot device. Idempotent: every step is a shell function that is a no-op when its result already exists. `--dry-run` prints the step names and the files it would write. `--dev` (on the PC) skips the hotspot, kiosk, mount, backlight and boot steps. `--skip-llama`, `--with-jellyfin`, `--pcie-gen3`. `web/dist` is optional (a placeholder `index.html` is installed if absent).

1. `apt install network-manager dnsmasq-base avahi-daemon cage wlr-randr chromium python3-venv aria2 cmake build-essential poppler-utils`.
2. Download pinned binaries from `install/versions.env`: kiwix-tools (aarch64 or x86_64 static), Caddy, optionally Jellyfin.
3. Build llama.cpp from the pinned tag with the flags in section 12 (about 10 minutes on the Pi) unless `--skip-llama`.
4. Create user `sos` (groups `video`, `input`, `render`), the `/srv/sos` tree, and the venv in `/srv/sos/api/.venv` with the `sos` package.
5. Install the built frontend to `/srv/sos/web` (or the placeholder).
6. Install systemd units, Caddyfile, NetworkManager profiles and `dnsmasq-shared.d/sos.conf`, the backlight udev rule, sudoers rule, kiosk wrapper, and `config.txt` fragment; `systemctl set-default graphical.target`.
7. Copy `playbooks/` and `manifest/` to `/srv/sos/state/`, then run `sos index`.
8. Prompt for admin PIN and SSID (or read `install/answers.env`).
9. Enable units. Reboot recommended.

### `sos` CLI (Python, part of the `sos` package)

| Command | Purpose |
|---|---|
| `sos sync --tier core\|extended [--only id,...] [--dry-run]` | Resolve sources, download with aria2c (resumable, checksum verify; built-in httpx downloader with Range resume as fallback), rename to `dest`, record resolved name, size and date, then `sos index`. Prints copy instructions for `build` items |
| `sos index` | Everything rescan does, then rebuild `fts_docs` from `/srv/sos/state/playbooks` and doc sidecars (extracting text for any `pdf` or `epub` item lacking one, with `pdftotext -layout` split at form feeds into pages), and `fts_places` from `places.csv.gz` when it changed |
| `sos storage-event add\|remove` | Calls `POST /api/system/rescan` (remove regenerates `library.xml` first) |
| `sos validate-playbooks [--deep]` | Section 10 |
| `sos build-maps [--out DIR] [--steps ...] [--fixture]` | PC only. Ends with `pmtiles verify` on every output, a bbox and zoom check on the base map, a style-sources check, and writes sizes into `manifest/maps.json`. `--fixture` runs every stage over a 0.1° bbox in under five minutes and is the CI test |
| `sos build-nhs [--out DIR]` | PC only: zimit crawl of nhs.uk `/conditions/`, `/symptoms/`, `/medicines/`, `/mental-health/`, `/tests-and-treatments/`, `/pregnancy/`, `/live-well/` with `--lang eng`, Brightcove and asset video excluded, stamped with the crawl date. Verification: no entry matching `brightcove`, no external `<script src>` or `<video>` hosts, at least 2,700 articles, ZIM `Date` equals the crawl date, `Title` includes "as at <date>" |
| `sos eval [--retrieval-only]` | Section 12 |
| `sos pin reset` | Clears a forgotten PIN |
| `sos status` | Prints `/api/status` |

### Development

`make dev` starts the dev stack on the PC: kiwix-serve (x86_64 static) on 8090 over the sample library, sos-api on 8000 with `SOS_DEV=1`, Caddy on 8080 using the production Caddyfile with the web, maps and docs roots overridden, and the Vite dev server behind it. `make test` runs pytest, Vitest, `sos validate-playbooks` and the manifest schema test. `make e2e` runs Playwright against the dev stack. `make deploy HOST=sos.local` rsyncs `api/` to `/srv/sos/api`, `web/dist` to `/srv/sos/web`, `playbooks/` and `manifest/` to `/srv/sos/state/`, and `install/` to `/srv/sos/install`, then runs `sos index` and restarts `sos-api.service`.

Fixtures: `tests/fixtures/library/` holds two small ZIMs committed with their sha256: `wikipedia_en_100_mini_2026-01.zim` (4.5MB, full-text index on) and `sos-test-noindex.zim` (built once with `zimwriterfs --withoutFTIndex` from `tests/fixtures/pages/`); `tests/fixtures/maps/test.pmtiles` (a 0.1° extract under 5MB), fixture overlays, styles, an OPDS catalogue XML, a 200-row `places.csv`, sample playbooks, and saved kiwix-serve responses.

## 14. Testing

| Layer | Tooling | What is covered |
|---|---|---|
| API | pytest, FastAPI TestClient, respx, the fixture ZIMs and a real kiwix-serve | manifest validation including the `dest` invariant; library file generation; rescan with the extended tier missing; search over both fixture ZIMs (indexed hit, unindexed excluded, XML parser against a saved response); the three fixed ranking comparisons; query construction with `wi-fi`, `St John's`, `999 vs 111`, `1:1 ratio`, `AND`; a fake kiwix-serve that sleeps 3 seconds is dropped and the response is `partial`; cache hit on repeat and miss after rescan; suggest cap; playbook rendering, checklist state, reset and module inclusion; places (Oxford first for `oxf`); notes and pins; AI flow with a fake llama-server (event order, token budget via fake `/tokenize`, hold-back citation stripping, zero-passage refusal, health router title hit, busy lock, timeout); thermal watchdog with mocked sysfs (79°C stays on, 80°C stops, cooling does not restart); PIN gating (open with no PIN, 401 without token, rate limit, expiry) and the localhost-only endpoints; hotspot and eth-mode with a recorded `nmcli`; backlight scaling to `max_brightness` |
| CLI | pytest with the fixture OPDS catalogue, a local HTTP server and a stubbed `aria2c` | `sos sync` resolves `kiwix` names to the newest entry, downloads `url` items, fails on sha256 mismatch, prints copy instructions for `build` items, honours `--only` and `--dry-run`, renames to `dest`, records resolved values, and runs index; `sos index` extracts PDF pages; `sos validate-playbooks` against one valid and one broken example per rule |
| Frontend | Vitest and Testing Library | search bar and suggestions, result list, playbook tabs and checklist, reader link capture and history, kiosk keyboard typing into a controlled input, idle overlay with fake timers, themes and reader stylesheet injection, links resolver for every scheme, OSGB and Irish Grid conversion against known points (OS HQ Southampton SU 38726 14830 ≈ 50.9379, -1.4708) |
| E2E | Playwright against the dev stack | Home → scenario → checklist tick visible from a second browser context; Home → search → reader; follow three article links in the reader, Back returns to each, app URL matches; map renders from the fixture PMTiles (first tile request 206 with no `Content-Encoding`), base switch keeps an overlay, overlay toggle, place search, pin saved and visible after reload, grid reference for a known point; theme persists after reload; kiosk: keyboard on focus, pick a suggestion, PIN on the numeric pad; each captive-portal probe path returns 302 to `http://10.42.0.1/welcome`; `/welcome` and `/starting` load with no app JavaScript |
| Content | `sos validate-playbooks` in CI | front matter, headings, links, overlays, modules, checklist ids, every scenario present |
| Manifest | JSON schema test | every item valid, ids unique, `dest` unique, `zim` dest invariant, `build` items have an `artifact` |
| Build pipelines | `sos build-maps --fixture` in CI; `build-nhs` verification stage on the PC | outputs verified before they reach the box |
| Install | shellcheck; `install.sh --dry-run` matched against `tests/golden/install-dry-run.txt`; `caddy validate`; `systemd-analyze verify` when available | script and units stay valid |
| Hardware checklist (manual, `docs/hardware-checklist.md`, each item with date, commit and result) | | hotspot join and captive portal on an iPhone and an Android, including a Samsung with mobile data on; fallback URLs and QR; `sos.local` from the home LAN; direct laptop link survives a reboot; update over ethernet downloads one item; external drive hot-plug and removal while browsing; display is landscape and touch lands where the finger is; backlight device present and controllable (or the 501 fallback); low power mode dims and stops AI; idle dim, wake without a click passing through, return to Home after 30 minutes; keyboard usable on the panel; open a 300-page PDF on iPhone and Android and jump to page 200; NVMe boot; pull the power during use and reboot to Home with no dialog; thermal under a 10-minute AI session in the printed case; thermal auto-off at a lowered threshold; RAM with AI ready and two phones browsing (zero swap); load with five phones browsing, one panning the map at z14 and one AI question in flight (search p95 under 3 seconds, no OOM kills, under 80°C for 10 minutes); power-bank runtime with the screen lit; `install.sh` run twice with no changes the second time |

## 15. Plans and exit criteria

The spec is implemented as five sub-plans (`docs/superpowers/plans/`): 01 backend and install, 02 frontend, 03 content, 04 maps pipeline, 05 AI; 01 and 02 in parallel, then 03 and 04, then 05, then integration. Content authoring (03) is one task per document, each closed by the validator passing and the owner setting `reviewed:`. Each milestone below closes only when both lists pass; "CI" runs on the PC, "Box" on the hardware and is recorded in the checklist.

1. **Skeleton** (01). CI: shellcheck; dry-run golden; `caddy validate`; `systemd-analyze verify`; Caddy on the PC answers each probe path with 302 to `/welcome` and serves the fixture ZIM through `/kiwix/`; `make dev` then `dev/smoke.sh` all PASS. Box: a phone joins `SOS`; the portal pops on one iPhone and one Android; both addresses load; the kiosk shows the app; `install.sh` a second time reports no changes.
2. **App shell, library, reader, search** (01 + 02). CI: `GET /api/library` lists the fixture ZIM as available; `GET /api/search` returns a Kiwix hit and an FTS5 hit in one ranked list; the slow-ZIM test returns `partial` in under 2.5 seconds; suggest at most 10; the Playwright flows above; all three themes pass an automated contrast check at 853x480 and 390x844. Box: the same Playwright suite passes against `http://10.42.0.1` from a laptop on the hotspot.
3. **Maps** (04 + 02). CI: `sos build-maps --fixture` passes with `pmtiles verify` on every output; the map Playwright flows. Box: full outputs installed, sizes recorded in `manifest/maps.json`, pan and zoom at z15 on the kiosk and one phone with zero 4xx/5xx for `/maps/*`.
4. **Playbooks** (03). CI: validator passes for all 20 scenarios, 17 modules, every card and page; every scenario has at least one citation in Right now, First 72 hours and UK specifics; `reviewed:` present on every scenario. Box: print view of one playbook from a phone.
5. **Full content** (01 + 03). CI: `sos sync --dry-run --tier core` resolves every `kiwix` item against the fixture catalogue and prints copy instructions for every `build` item. Box: `sos sync --tier core` completes; every core item available; core size within 10% of the manifest sum; unplugging the drive greys its items within 10 seconds and replugging restores them; `sos validate-playbooks --deep` passes.
6. **AI** (05). CI: the fake llama-server suite; `sos eval --retrieval-only` at least 80% on the fixture library. Box: `sos eval` full run with median time to first token at most 90 seconds, generation at least 5 tokens per second (raise to 7 once speculative decoding — section 12 — is measured on the box and lands there; the 2026-09-16 model review found no published measurement of this model and quant on Pi 5 hardware reaching 7 tok/s idle, let alone under kiosk/hotspot contention), zero swap, CPU under 80°C, `vcgencmd get_throttled` recorded alongside the run so a throttled result is visibly invalid rather than silently read as a slow model; results file committed.
7. **Polish and hardware** (02 + 01). CI: idle and wake with fake timers; PIN gating suite. Box: the full hardware checklist in the printed case.

## 16. Risks and open points

- **Thermal in a sealed printed case**: unmeasured. Fan path in the case, temperature on the status strip, the thermal watchdog.
- **Combined load**: no published benchmark of hotspot plus Kiwix plus maps plus a 2B model with several clients. Measured in milestone 6 with a search and a map pan on a second client during generation; drop to the 1B model if needed.
- **Backlight on Touch Display 2 under cage**: unverified; the 501 fallback covers it. Confirm in milestone 1.
- **Captive portal**: unreliable by nature; the `/welcome` page, printed addresses and QR codes are the mitigation.
- **NHS ZIM**: Kiwix's own conditions build was withdrawn over embedded video; the self-build verification stage checks for it. Sizes are estimates until the first crawl.
- **Map extract size**: 3.2GB measured for the 49.5 edge on the 2026-09-02 build; the 49.1 edge and flood, footpath and hillshade layers are recorded after the first full build.
- **Content sources move**: `kiwix` resolution handles renamed ZIMs; `url` items need checksum updates when a host changes a file.
- **Licensing**: recorded per item, not enforced. If the owner ever publishes an image or sells kits, the research brief lists what would change.
- **Tide tables**: no open UK source exists; omitted.
- **HTTPS**: out of scope (no offline CA path to phones).
