# Operation SOS — design spec

Date: 2026-09-03
Status: draft for owner review
Research backing this spec: `docs/research/2026-09-03-research-brief.md`

## 1. What this is

Operation SOS is an offline, UK-focused "end of the world" knowledge box. It runs on a Raspberry Pi 5 (8GB) with a touchscreen and a 500GB NVMe, plus an optional external USB drive. It broadcasts its own WiFi hotspot so phones and laptops can use it with no internet, no grid and no mobile network, and it shows the same interface on its own screen so it works when every phone is dead.

It is inspired by Project NOMAD (an x86 Docker knowledge server with a US-only catalogue) but shares no code with it. Operation SOS is Pi-native, hotspot-first, screen-first, and organised around UK scenarios rather than a library shelf.

### Goals

1. Everything needed to survive, heal, fix and rebuild in the UK after a catastrophe, readable offline from a phone or the box's screen.
2. Twenty scenario playbooks that tell someone what to do right now, over 72 hours, over a month and over years, with UK-specific detail.
3. One search box across everything: Wikipedia, NHS, manuals, maps, playbooks.
4. Full UK maps (England, Scotland, Wales, Northern Ireland, plus the Republic of Ireland, Isle of Man and Channel Islands) with terrain, footpaths and scenario overlays.
5. An intuitive, themed frontend that works on a 7" touchscreen and on any phone.
6. An optional grounded AI assistant that only answers from the library and cites its sources.
7. Reproducible: one install script on a fresh Raspberry Pi OS, one sync command for content.

### Non-goals (v1)

- Selling kits, publishing a disk image, or any distribution beyond the repo. Licence hygiene is recorded in the manifest but is not a constraint on what the owner's own box holds.
- Mesh radio (Meshtastic/MeshCore) integration.
- Multi-box sync or peer-to-peer replication.
- Any online service dependency at runtime.
- Plant or fungus identification from photos.

## 2. Users and scenarios

Primary user: the owner and whoever is with them. Secondary: anyone who joins the hotspot. No accounts. System-level actions (power mode, ethernet mode, updates) are behind an optional admin PIN set at install.

### The 20 scenarios

Grounded in the UK National Risk Register 2025 and the owner's brief.

| # | Slug | Scenario |
|---|---|---|
| 1 | `nuclear-war` | Nuclear war: strategic strike on the UK, fallout, shelter, iodine |
| 2 | `nuclear-accident` | Nuclear accident or dirty bomb: plume from a UK site |
| 3 | `pandemic` | Lethal pandemic with no NHS capacity |
| 4 | `grid-collapse` | National grid collapse: weeks-long blackout, water pumps and comms down |
| 5 | `solar-storm` | Solar superstorm: grid, satellites and GPS gone |
| 6 | `emp` | EMP attack: electronics, vehicles and radios dead |
| 7 | `cyber-attack` | Cyber attack on critical infrastructure: water, banking, NHS, telecoms |
| 8 | `invasion` | Invasion or occupation: conventional war on UK soil, resistance, evacuation |
| 9 | `civil-unrest` | Civil unrest and breakdown of order: riots, martial law, civil war |
| 10 | `economic-collapse` | Economic collapse: currency failure, banks closed, hyperinflation, barter |
| 11 | `supply-chain` | Supply chain collapse: food, fuel and medicine shortages |
| 12 | `flooding` | Coastal storm surge and major river flooding |
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
- Full-length (2280) NVMe carrier: Pimoroni NVMe Base (flat, stacks under the Pi; suits a printed case). 500GB NVMe, boot and core drive.
- Official Active Cooler or equivalent fan. The printed case must have an intake and exhaust path; throttling in a sealed enclosure is the known unknown.
- Official 27W USB-C PSU.
- Screen: Raspberry Pi Touch Display 2 (7", 1280x720, DSI) inset in the printed case. Any HDMI touchscreen also works.
- External drive: self-powered USB 3 HDD or SSD, ext4, filesystem label `SOS-EXT`.
- Optional: 20,000mAh USB-C PD power bank (12 to 15 hours, AI off), 250Wh LiFePO4 station (about two days).

### Storage layout

| Path | Drive | Holds |
|---|---|---|
| `/srv/sos/core/zim` | NVMe | core ZIM files |
| `/srv/sos/core/maps` | NVMe | PMTiles, styles, sprites, glyphs, overlay GeoJSON, phone map packs |
| `/srv/sos/core/docs` | NVMe | PDFs and EPUBs plus extracted text |
| `/srv/sos/core/models` | NVMe | GGUF model files |
| `/srv/sos/core/playbooks` | NVMe | rendered playbook bundle (copied from repo at install) |
| `/srv/sos/extended/{zim,docs,media,video,books}` | USB | extended library |
| `/srv/sos/state` | NVMe | `sos.db` (SQLite), `library.xml`, manifest cache, logs, config |
| `/srv/sos/web` | NVMe | built frontend |

Filesystem: ext4 with `noatime` on both drives. No filesystem compression (content is already compressed).

The box works fully with only `core`. Items in `extended` show as "on external drive" in the UI and are hidden when the drive is absent.

### RAM budget

| Process | Approx RSS |
|---|---|
| kiwix-serve | 0.3 to 0.6GB (mmap, grows with use) |
| Chromium kiosk | 0.8 to 1.2GB |
| sos-api plus Caddy plus dnsmasq | 0.3GB |
| llama-server (2B model, Q4, 2K context) | 2 to 2.5GB, only when AI is on |
| OS and page cache | remainder |

## 4. Networking

### Hotspot

- Interface `wlan0` in access-point mode via NetworkManager (`ipv4.method shared`), 2.4GHz for phone compatibility, channel auto. SSID default `SOS`, open network. SSID and an optional WPA2 passphrase are configurable in System settings.
- Address `10.42.0.1/24`. NetworkManager's dnsmasq hands out DHCP and resolves every name to `10.42.0.1` (`address=/#/10.42.0.1`), so `http://sos.box` always works.
- Captive-portal detection: Caddy answers the probe paths (`/generate_204`, `/gen_204`, `/hotspot-detect.html`, `/library/test/success.html`, `/connecttest.txt`, `/ncsi.txt`, `/canonical.html`, `/success.txt`) with a `302` to `http://sos.box/`, which makes Android, iOS, Windows and Firefox pop the landing page. Because this is unreliable on some devices, the kiosk screen and the landing page always show the SSID, `http://sos.box`, `http://10.42.0.1` and a QR code for the WiFi.

### Ethernet

- Default: `eth0` is a DHCP client. Plug it into a home router to run updates; the box is also reachable on the home LAN at `http://sos.local` (mDNS via Avahi) while the hotspot keeps running.
- "Direct laptop link" toggle in System switches `eth0` to shared mode (`10.43.0.1/24`) so a laptop can plug straight in with no router. The toggle is remembered across reboots.

### Ports

| Port | Bind | Service |
|---|---|---|
| 80 | all | Caddy |
| 8000 | localhost | sos-api |
| 8090 | localhost | kiwix-serve |
| 8081 | localhost | llama-server |
| 8096 | all | Jellyfin (optional) |

## 5. Services

All services are systemd units on 64-bit Raspberry Pi OS Lite (Trixie or later). No Docker. Binaries are pinned to versions in `install/versions.env`.

| Unit | What it runs | Notes |
|---|---|---|
| `caddy.service` | Caddy | Serves `/srv/sos/web`, proxies `/api/*` to sos-api, `/kiwix/*` to kiwix-serve, `/ai/*` to llama-server; serves `/maps/*` from `/srv/sos/core/maps` as static files with range requests and no compression (PMTiles need byte ranges); serves `/docs/*` from both tiers; captive-portal redirects |
| `kiwix-serve.service` | `kiwix-serve --library /srv/sos/state/library.xml --monitorLibrary --address 127.0.0.1 --port 8090 --urlRootLocation /kiwix` | Library file is regenerated by sos-api; `--monitorLibrary` picks up changes without restart |
| `sos-api.service` | uvicorn running the FastAPI app from a venv | See section 6 |
| `sos-llama.service` | `llama-server -m <model> -c 2048 -t 4 --port 8081` | Disabled by default; started and stopped by sos-api via `systemctl` (sudoers rule scoped to this unit) |
| `sos-kiosk.service` | `cage` (Wayland kiosk compositor) running Chromium `--kiosk --ozone-platform=wayland --noerrdialogs --disable-infobars http://localhost/?kiosk=1` | Auto-login on tty1 as user `sos`. Backlight controlled through `/sys/class/backlight/*/brightness` by sos-api |
| `sos-storage-event@.service` | `sos storage-event <add|remove> <device>` | Triggered by a udev rule matching `ENV{ID_FS_LABEL}=="SOS-EXT"`; mounts or unmounts `/srv/sos/extended` and calls `POST /api/system/rescan` |
| `avahi-daemon.service` | mDNS `sos.local` | Only useful on a home LAN |
| `jellyfin.service` | Jellyfin | Optional, installed with `install.sh --with-jellyfin`; library root `/srv/sos/extended/media` |

Boot order: network → kiwix-serve and sos-api → caddy → kiosk. The kiosk shows a "starting" page until `/api/status` responds.

## 6. sos-api

Python 3.12, FastAPI, uvicorn, SQLite via `sqlite3` with FTS5, `httpx` for calls to kiwix-serve and llama-server, `pyyaml`, `markdown-it-py`. No ORM.

### Database (`/srv/sos/state/sos.db`)

- `library_items`: manifest items with resolved local path, size, `as_at`, tier, `available` flag.
- `fts_docs` (FTS5): `doc_id, kind, title, body, category, scenarios` for playbooks, modules, quick cards, comms pages, PDF text, library item titles.
- `fts_places` (FTS5): `name, kind, lat, lon, region, postcode` from OS Open Names (GB) and OSM place nodes (NI, RoI, IoM, CI).
- `checklist_state`: `(playbook_slug, item_id, checked, updated_at)` shared across all clients.
- `notes`: `(id, title, body, updated_at)`.
- `settings`: key/value (SSID, passphrase, admin PIN hash, power mode, eth mode, AI enabled, default theme).
- `search_cache`: recent query → results, capped at 500 entries.

### Endpoints

All under `/api`. JSON unless noted.

| Method and path | Purpose |
|---|---|
| `GET /status` | CPU temperature, load, memory, disks (core and extended: mounted, free, total), hotspot (SSID, IP, client count), eth mode, power mode, AI state (off, starting, ready), version |
| `GET /library` | All items with availability, grouped by category |
| `GET /library/{id}` | One item, including deep-link base for the reader |
| `GET /search?q=&sources=&limit=` | Unified search (section 8) |
| `GET /suggest?q=` | Title autocomplete from primary ZIMs plus playbooks and cards |
| `GET /playbooks` | List with slug, title, icon, summary |
| `GET /playbooks/{slug}` | Rendered HTML per section, checklist items with shared state, related overlays and library items |
| `PUT /playbooks/{slug}/checklist/{item_id}` | Set checked true or false |
| `GET /modules/{slug}` | Rendered shared module |
| `GET /cards` and `GET /cards/{slug}` | Medical quick cards |
| `GET /pages/{slug}` | Comms pages, "what still works", UK numbers, household plan template |
| `GET /map/overlays` | Overlay catalogue: id, title, kind (geojson or pmtiles), URL, default visibility, scenarios |
| `GET /places?q=&limit=` | Place search returning name, kind, lat, lon |
| `GET /notes`, `POST /notes`, `PUT /notes/{id}`, `DELETE /notes/{id}` | Shared notes |
| `POST /ai/ask` | Body `{question, history}`; response is Server-Sent Events: `retrieving` (with passages), `token`, `done` (with citations) |
| `GET /ai/status`, `POST /ai/enable`, `POST /ai/disable` | AI control; enable starts `sos-llama.service` and waits for readiness |
| `POST /system/power-mode` | `{mode: "normal" \| "low"}`; low stops AI and dims backlight |
| `POST /system/backlight` | `{level: 0..100}` |
| `POST /system/eth-mode` | `{mode: "client" \| "direct"}` |
| `POST /system/hotspot` | `{ssid, passphrase}` |
| `POST /system/rescan` | Rebuild `library.xml` and availability; called by storage events |
| `POST /system/update` | Runs `sos sync` for available tiers in the background; `GET /system/update/progress` streams progress |
| `POST /system/pin` | Verify admin PIN; returns a short-lived token used by the other `/system/*` calls when a PIN is set |

### Library file generation

`library.xml` is regenerated by walking `/srv/sos/core/zim` and, if mounted, `/srv/sos/extended/zim`, using `kiwix-manage`. Items whose file is missing are marked unavailable rather than removed from `library_items`, so the UI can say "on external drive".

## 7. Content manifest

`manifest/core.json`, `manifest/extended.json`, `manifest/maps.json`, `manifest/overlays.json`, validated against `manifest/schema.json`.

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
  "reader_home": "A/Main_Page"
}
```

- `kind`: `zim`, `pmtiles`, `geojson`, `pdf`, `epub`, `dir`, `model`, `mwm`, `style`.
- `tier`: `core` or `extended`.
- `category`: `playbooks`, `uk-official`, `medical`, `survival`, `reference`, `practical`, `maps`, `education`, `books`, `media`, `ai`.
- `source.type`:
  - `kiwix`: resolved at sync time against the Kiwix OPDS catalogue to the newest file for that name, so date-stamped filenames never go stale.
  - `url`: direct download with `sha256` and optional `mirrors`.
  - `build`: produced on the owner's PC by a `tools/` command; `artifact` names the file to copy into place. `sos sync` reports these as "copy from build output" rather than downloading.
- `licence` and `as_at` are informational and shown in the UI. They do not gate anything.
- `priority`: download order, lowest first, so the most important content lands first on a slow connection.

### Core content (target about 200GB)

| Category | Items |
|---|---|
| uk-official | Prepare campaign (self-built ZIM), National Risk Register 2025, CMO national power-outage advice, UKHSA flooding and cold-weather guidance, FSA safe-foraging guidance, Building Regulations Approved Documents A to T, HSE guidance selection, gov.uk law summaries (knives, firearms, hunting, fishing, unauthorised encampments), legislation extracts (Theft Act s4(3), Wildlife and Countryside Act, CRoW, Deer Act, Firearms Act, CJA s139, Offensive Weapons Act, Civil Contingencies Act), Ofcom PMR446 and amateur licence documents, RSGB 2026 band plans, Ready Scotland community planning guide and templates, Wales Resilience Framework, nidirect emergency pages, Local Resilience Forum contacts, Emergency Alerts explainer, Protect and Survive (1980) |
| medical | nhs.uk medicines ZIM, nhs.uk conditions and symptoms ZIM (self-built, video excluded, dated), WikiMed, WikEM, mdwiki, MedlinePlus, zimgit-medicine, Where There Is No Doctor and Dentist, Ship Captain's Medical Guide (MCA), WHO Essential Medicines 2025, military medicine (FAS), Survival and Austere Medicine, Emergency War Surgery, FM 4-25.11 First Aid, medical Stack Exchange |
| survival | zimgit water, food-preparation, knots, post-disaster; ready.gov; Appropedia; Appropriate Technology Library (cd3wd); military survival manuals (FM 21-76 and FM 3-05.70); Nuclear War Survival Skills (Kearny); FEMA nuclear detonation guidance; urban-prepper, canadian-prepper, trueprepper, s2underground and lrnselfreliance crawls; energypedia; Low-tech Magazine; based.cooking and foss.cooking; USDA canning |
| reference | Wikipedia (maxi), Simple Wikipedia, Wiktionary, Wikibooks, Wikivoyage, OpenStreetMap wiki |
| practical | iFixit; Stack Exchange: diy, electronics, gardening, outdoors, mechanics, woodworking, cooking, homebrew, sustainability, ham, bicycles, biology, chemistry, physics, engineering, earthscience, pets; DevDocs |
| maps | see section 9 |
| ai | Gemma 4 E2B Q4_K_M (primary), Qwen 3.5 2B Q4_K_M (fallback) |

### Extended content

Gutenberg (full), Stack Overflow and all remaining Stack Exchange sites, Khan Academy, TED-Ed, LibreTexts, OpenStax, Survivor Library, video collections (Canadian Prepper and similar), Wikipedia in other languages if wanted, Jellyfin media folders for the owner's films, music and audiobooks.

## 8. Search

### Sources

1. **Kiwix**: `GET /kiwix/search?pattern=<q>&books.name=<zim>&format=xml&pageLength=8` per ZIM, in parallel with `httpx`, 1.5 second timeout per call. Only ZIMs with a full-text index are queried (checked at rescan time).
2. **FTS5 docs**: playbooks, modules, cards, comms pages, PDF text, library titles. BM25 ranking.
3. **FTS5 places**: name prefix match, returned as map results.

### Merge and rank

- Reciprocal rank fusion across sources (`score = Σ 1/(60 + rank)`), then multiplied by a source weight.
- Base weights: playbooks and cards 1.6, uk-official and NHS 1.4, medical ZIMs 1.2, everything else 1.0.
- Intent boosts from a keyword list: medical terms (symptom, bleeding, dose, fever, burn, and about 200 more) boost medical sources ×1.5; place-like queries (postcode pattern, "near", town names that hit `fts_places`) boost places ×2.
- Exact title matches jump to the top of their source group.
- Output: flat ranked list with `source`, `badge`, `title`, `snippet`, `url` (reader URL or map URL), plus a `groups` summary for the filter bar.
- Cached in `search_cache`; cache invalidated on rescan.

### Suggest

`/suggest` calls `GET /kiwix/suggest?content=<zim>&term=<q>` on the six primary ZIMs (Wikipedia, WikiMed, NHS conditions, NHS medicines, WikiHow-equivalent if present, iFixit) plus FTS5 prefix matches on docs. Returns at most 10.

## 9. Maps

### Base and terrain (built on the owner's PC by `sos build-maps`)

| Layer | Source | Output |
|---|---|---|
| Base map | Protomaps basemap build, `pmtiles extract --bbox=-11,49.5,2.2,61.2` zoom 0 to 15 | `uk-ie.pmtiles` (about 3 to 5GB) |
| OS base | OS Open Zoomstack MBTiles converted to PMTiles | `os-zoomstack.pmtiles` (2.9GB), GB only |
| Contours | OS Terrain 50 contours via tippecanoe | `contours.pmtiles` |
| Hillshade | OS Terrain 50 DTM via `gdaldem hillshade` then raster PMTiles | `hillshade.pmtiles` |
| NI terrain | OSNI 50m DTM, same pipeline | merged into contours and hillshade |
| Styles | Protomaps basemap styles (light, dark, and a Vault variant), OS Zoomstack style, sprites and glyph PBFs | `styles/`, `sprites/`, `fonts/` |
| Phone packs | Organic Maps `.mwm` files for the UK and Ireland | `packs/` with an index page |

### Overlays (`manifest/overlays.json`)

| Overlay | Source | Kind |
|---|---|---|
| Footpaths and rights of way | OSM `highway=path|footway|bridleway|track` with `designation=*` | in base tiles, toggled by style layer |
| Access land | Natural England CRoW layer | GeoJSON |
| Flood zones 2 and 3 | Environment Agency Flood Map for Planning | PMTiles (large) |
| Hospitals, pharmacies, GP surgeries | OSM `amenity=hospital|pharmacy|doctors` | GeoJSON |
| Fuel stations | OSM `amenity=fuel` | GeoJSON |
| Reservoirs and water works | OSM `landuse=reservoir`, `man_made=water_works` | GeoJSON |
| Railway stations | OSM `railway=station` | GeoJSON |
| Nuclear sites | Hand-authored: power stations (operating and decommissioning), Sellafield, AWE Aldermaston and Burghfield, Faslane and Coulport, Devonport, Barrow, Rosyth | GeoJSON |
| Major chemical and fuel sites | OSM `industrial=chemical|refinery|oil` plus hand-authored list | GeoJSON |
| Airports and military bases | OSM `aeroway=aerodrome`, `military=*` | GeoJSON |

Each overlay declares which scenarios switch it on by default (for example `nuclear-war` turns on nuclear sites, hospitals and reservoirs).

### Viewer

MapLibre GL JS with the `pmtiles` protocol reading from `/maps/*` via range requests. Features: layer panel, base switch (OSM or OS), place search (from `/api/places`), pins saved to the box (`notes` table, kind `pin`), distance and bearing measure, grid reference display (OSGB), user location if the browser supports it, share-a-place link, print current view.

## 10. Playbooks and authored content

Location: `playbooks/scenarios/<slug>.md`, `playbooks/modules/<slug>.md`, `playbooks/cards/<slug>.md`, `playbooks/pages/<slug>.md`.

### Front matter

```yaml
---
id: nuclear-war
title: Nuclear war
icon: radiation
summary: A nuclear strike on the UK. Fallout, shelter, water, radiation sickness.
modules: [radiation, water, shelter-heat, medical, sanitation, comms, evacuation]
overlays: [nuclear-sites, hospitals, reservoirs]
sources:
  - title: National Risk Register 2025
    url: https://assets.publishing.service.gov.uk/.../National_Risk_Register_2025.pdf
    as_at: 2025-01-16
  - title: Nuclear War Survival Skills
    doc: nwss-1987
---
```

### Body

Exactly these headings, in this order: `## Right now`, `## First 72 hours`, `## First month`, `## Long term`, `## UK specifics`, `## Checklist`, `## Go deeper`. The checklist section uses task-list syntax; each item gets a stable id from a slug of its text. `## Go deeper` is a list of links.

Modules are included with `{{module:water}}` on its own line and render as a collapsible section inline.

### Link scheme

- `kiwix:<zim-id>/<path>` opens the reader at that article.
- `doc:<item-id>` opens a PDF or EPUB from the library.
- `map:?overlay=nuclear-sites&overlay=hospitals` opens the map with overlays on.
- `module:<slug>`, `card:<slug>`, `page:<slug>`, `playbook:<slug>` navigate within the app.

A build step (`sos validate-playbooks`) checks front matter against a schema, that headings are present and ordered, and that every link resolves against the manifest and the playbook set.

### Medical quick cards

One screen each, large type, numbered steps, red warnings: CPR adult and child, severe bleeding, choking, burns, hypothermia, heat stroke, broken bones, radiation sickness, chemical exposure, childbirth, dehydration and rehydration solution, wound cleaning and infection, shock, drowning, seizures, anaphylaxis.

### Comms and reference pages

PMR446 channels and CTCSS table, UK amateur bands summary, UK emergency numbers and what still works when the power is off (105, 999 and 111 via Digital Voice battery limits, mast batteries, FM and DAB, Emergency Alerts), household emergency plan template, water disinfection for UK thickened bleach versus NaDCC tablets, 230V and RCD basics, grid-tied solar islanding, UK knife and firearms law summary, foraging law summary, tick and adder guidance.

### Authoring process

Playbooks and cards are drafted with AI assistance from the cited sources, then reviewed by the owner. Every factual claim that matters (a dose, a distance, a time, a law) carries an inline citation to a manifest item so the reader can check it.

## 11. Frontend

React 19 with Vite, TypeScript, React Router. Static build served by Caddy. No server rendering. Data via the API. Installable as a PWA so the app shell loads instantly on phones that have visited before; content still needs the box.

### Design rules

- Touch targets at least 48px. Text at least 16px on phones and 18px on the kiosk.
- Nothing more than two taps from Home.
- Every icon has a word next to it.
- High contrast in every theme; warnings in a colour and a symbol, never colour alone.
- Works at 1280x720 landscape (kiosk) and at phone portrait widths.

### Themes

CSS custom properties on `:root[data-theme]`. Chosen from a theme button on every screen, stored in `localStorage` per device, with a box-wide default in settings. All fonts bundled locally (OFL faces: a retro monospace for Vault, a humanist sans for the others).

| Theme | Look |
|---|---|
| `vault` (default) | Vault-Tec inspired: phosphor green on near-black, amber accent, faint scanlines and glow, bevelled buttons, monospace display face. Original artwork only |
| `field` | Field manual: paper and khaki, black text, red warnings, serif headings. Sunlight-readable and used as the print stylesheet |
| `blackout` | Dim red on black, minimal chrome. Night vision and lowest screen power |

### Kiosk mode

Detected via `?kiosk=1` on the launch URL and persisted in `sessionStorage`. In kiosk mode: a persistent Home button, an in-app on-screen keyboard that appears for any text input, return to Home and dim the backlight after five minutes idle (configurable), wake on touch, and a status strip showing SSID, addresses, QR code, external drive state and CPU temperature.

### Screens

| Route | Screen |
|---|---|
| `/` | Home: search bar, "What's happening?" scenario grid (20 tiles, icon and name), five big tiles (Medical, Maps, Library, Radio, Plan), status strip |
| `/s/:slug` | Scenario playbook: section tabs, inline modules, shared checklist, print button, Go deeper list |
| `/search?q=` | Results list with source badges and filter chips; suggestions while typing |
| `/read/:zim/*` | Reader: Kiwix article in an iframe under the app bar (back, home, text size, open in library, theme). Links inside the iframe stay inside the reader |
| `/doc/:id` | PDF or EPUB viewer (browser PDF viewer in an iframe; EPUB via a bundled reader) |
| `/medical` | Quick cards grid, NHS conditions A to Z, medicines A to Z, medical library |
| `/map` | Full-screen map (section 9) |
| `/library` | Categories, item cards with size, date, drive, availability |
| `/radio` | Comms pages |
| `/plan` | Household plan template, shared notes, pins list |
| `/ai` | Assistant, shown only when AI is ready; otherwise a "turn on in System" card |
| `/system` | Status, storage, hotspot settings, ethernet mode, power mode, backlight, AI toggle, update (when online), theme default, admin PIN |

## 12. AI assistant

Off by default. Enabled from System (PIN if set). Low power mode disables it.

### Runtime

`llama-server` from a native llama.cpp build with ARM dot-product and i8mm flags, `-c 2048 -t 4 -ngl 0`, KV cache `q4_0`. Model files in `/srv/sos/core/models`; the active model is a setting. Primary Gemma 4 E2B Q4_K_M; fallback Qwen 3.5 2B Q4_K_M. Expected 8 to 12 tokens per second generation and 20 to 25 tokens per second prompt processing on the Pi 5, so a 1,200-token context gives roughly 60 seconds to first token.

### Flow for `POST /ai/ask`

1. Run the unified search for the question (no cache).
2. Health router: if the query matches the medical keyword list or hits an NHS or quick-card title, emit a `verbatim` event first with that page's URL and its first two paragraphs.
3. Take the top three non-place results. For ZIM hits, fetch the article via kiwix-serve, strip to text, and pick the best 400-token window around the query terms. For docs, use the FTS5 body around the match.
4. Emit `retrieving` with the three passages and their citations.
5. Prompt: system text stating that the assistant answers only from the numbered passages, cites them as `[1]` `[2]` `[3]`, says "The library doesn't cover this" when they don't answer the question, uses British English and UK terms (999, 111, 105, paracetamol), never invents doses or laws. History capped at four turns; question capped at 400 characters.
6. Stream tokens. On completion, verify that every `[n]` in the answer maps to an emitted passage; strip any that don't. Emit `done` with citations as reader links.

### UI

Every answer carries a line: "AI can be wrong. The library pages linked below are the source of truth." NHS or card content shown from the health router is visually separate from AI text. No image input.

### Evaluation

`tools/eval/questions.jsonl`: about 50 UK questions (outage, first aid, medicines, foraging law, radio, water) with expected source ids. `sos eval` reports whether the expected source was retrieved and prints answers for human review. Run before any model or prompt change lands.

## 13. Install and tools

### `install/install.sh`

Run as root on a fresh 64-bit Raspberry Pi OS Lite with the NVMe as boot device. Idempotent. Steps:

1. `apt` packages: `network-manager`, `dnsmasq-base`, `avahi-daemon`, `cage`, `chromium`, `python3-venv`, `aria2`, `udev` extras, `libzim` runtime, build tools for llama.cpp.
2. Download pinned binaries from `install/versions.env`: kiwix-tools (aarch64 static), Caddy (arm64), optionally Jellyfin.
3. Build llama.cpp from a pinned tag with ARM flags (about 10 minutes on the Pi) unless `--skip-llama`.
4. Create user `sos`, the `/srv/sos` tree, and the Python venv with `api/requirements.txt`.
5. Install the prebuilt frontend from `web/dist` (built on the PC or in CI) to `/srv/sos/web`.
6. Install systemd units, Caddyfile, NetworkManager hotspot profile, udev rule, sudoers rule, auto-login drop-in, and `config.txt` fragments (PCIe Gen 3, DSI display).
7. Copy `playbooks/` and `manifest/` to `/srv/sos/state`, run `sos index`.
8. Prompt for admin PIN and SSID (or read from `install/answers.env` for unattended installs).
9. Enable units. Reboot recommended.

### `sos` CLI (`tools/sos`, Python, installed into the venv)

| Command | Purpose |
|---|---|
| `sos sync --tier core\|extended [--only id,...] [--dry-run]` | Resolve sources, download with aria2c (resumable, 4 connections, checksum verify), place into tier root, then `sos index`. Prints copy instructions for `build` sources |
| `sos index` | Regenerate `library.xml`, rebuild `fts_docs` and `fts_places`, refresh `library_items` |
| `sos storage-event add\|remove <dev>` | Mount or unmount the external drive and trigger rescan |
| `sos validate-playbooks` | Schema, headings, links |
| `sos build-maps` | PC only: base map extract, OS conversions, contours, hillshade, overlays, phone packs. Requires `pmtiles`, `tippecanoe`, `gdal`, `osmium` |
| `sos build-nhs` | PC only: zimit crawl of nhs.uk conditions, symptoms and medicines with Brightcove and asset video excluded, stamped with the crawl date |
| `sos build-docs` | PC only: gather PDFs listed in the manifest, extract text with `pdftotext`, write sidecar `.txt` and metadata |
| `sos eval` | Run the AI question set |
| `sos status` | Same as `/api/status`, for the terminal |

### Development

Develop on the owner's PC (WSL2). `make dev` runs sos-api with a sample library (Kiwix's 4.5MB `wikipedia_en_100_mini` ZIM and a handful of playbooks) and the Vite dev server with a proxy. `make deploy HOST=sos.local` rsyncs `api/`, `web/dist`, `playbooks/`, `manifest/` and `install/` to the Pi and restarts the units. Content sync runs on the Pi itself.

## 14. Testing

| Layer | Tooling | What is covered |
|---|---|---|
| API | pytest, `httpx` test client, a sample ZIM fixture | manifest loading and validation, library file generation, rescan with a missing extended tier, search merge and ranking with fixed inputs, suggest, playbook rendering and checklist state, places, notes, AI flow with a fake llama-server (SSE order, citation stripping, health router), system endpoints with mocked `systemctl` and sysfs |
| Frontend | Vitest and Testing Library; Playwright | component tests for search, playbook, reader bar, keyboard, themes; Playwright smoke against a mock API for Home → scenario → checklist tick, Home → search → reader, map loads and toggles an overlay, theme switch persists, kiosk keyboard appears |
| Content | `sos validate-playbooks` in CI | front matter schema, heading order, link resolution, every scenario present |
| Manifest | JSON schema test | every item valid, ids unique, `dest` unique, `build` items have an `artifact` |
| Install | shellcheck; a dry-run mode that prints actions | script stays valid; hardware checklist in `docs/hardware-checklist.md` |
| Hardware checklist (manual) | | hotspot join and captive portal on an iPhone and an Android, fallback URLs, external drive hot-plug and removal while browsing, thermal under a 10-minute AI session in the printed case, power-bank runtime, kiosk idle and wake |
| AI | `sos eval` | expected source retrieved for each question; answers eyeballed |

## 15. Milestones

1. **Skeleton**: repo layout, install script, Caddy, kiwix-serve with the sample ZIM, hotspot with captive portal, kiosk showing a placeholder. Ships when a phone can join `SOS` and see a page.
2. **App shell, library, reader, search**: frontend routes and themes, library browsing, reader with app bar, unified search over ZIMs and FTS5, suggest.
3. **Maps**: `sos build-maps`, viewer, overlays, places, pins, phone packs.
4. **Playbooks and authored content**: 20 scenarios, modules, quick cards, comms pages, checklists, print view, validation.
5. **Full content**: complete manifests, `sos sync`, `sos build-nhs`, `sos build-docs`, external drive handling, library at target size.
6. **AI**: llama.cpp build, `sos-llama` unit, ask flow, health router, eval set.
7. **Polish**: kiosk keyboard and idle behaviour, low power mode, backlight, PWA, admin PIN, Jellyfin option, hardware checklist pass in the printed case.

## 16. Risks and open points

- **Thermal in a sealed printed case**: unmeasured. Mitigation: fan path in the case design, temperature on the status strip, AI auto-off above 80°C.
- **Combined load on the Pi**: no published benchmark of hotspot plus Kiwix plus maps plus a 2B model with several clients. Mitigation: AI off by default, measure in milestone 6, drop to the 1B-class fallback if needed.
- **Captive portal flakiness**: mitigated by printed and on-screen fallback addresses and QR code.
- **NHS conditions ZIM**: Kiwix's own build was withdrawn over embedded video; the self-build must exclude video hosts. Sizes above are estimates until the first crawl.
- **Map extract size**: the UK and Ireland Protomaps extract at zoom 15 is estimated at 3 to 5GB; confirm on the first build.
- **Content sources move**: `kiwix` source resolution handles renamed ZIMs; `url` items need checksum updates when a host changes a file.
- **Licensing**: recorded per item, not enforced. If the owner ever publishes an image or sells kits, the research brief lists the items that would need swapping and the obligations that would apply (PSTI, MHRA, NHS OGL attribution, trademark on the NOMAD name).
- **Tide tables**: no open UK source exists; omitted from v1.
