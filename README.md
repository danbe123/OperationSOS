# Operation SOS

Operation SOS is an offline, UK-focused knowledge box. It runs on a Raspberry Pi 5 with a 7" touchscreen and an NVMe drive, broadcasts its own WiFi hotspot so phones and laptops can use it with no internet, no grid and no mobile network, and shows the same interface on its own screen so it still works when every phone is dead.


## What it is

- **Twenty scenario playbooks** (nuclear war, grid collapse, pandemic, flooding, the long rebuild and more) that say what to do right now, over 72 hours, over a month and over years, with UK-specific detail, a shared checklist and citations into the library.
- **One search** across Wikipedia, the NHS, repair manuals, survival libraries, maps and the playbooks.
- **Maps** of the UK, the Republic of Ireland, the Isle of Man and the Channel Islands with footpaths, contours, hillshade and scenario overlays (hospitals, fuel, water, nuclear sites, flood zones), served from the box to any phone.
- **Medical quick cards** plus comms, legal and household-plan reference pages.
- **Kits**: fifteen tiered lists of what to have (medical, water, food, power, comms, fallout and more), ticked by everyone on the box, with quantities scaled to a one-tap people count.
- **An optional AI assistant** that only answers from the library and cites its sources; off by default.
- Plain HTTP on the hotspot at `http://10.42.0.1` (or `http://sos.box`), no accounts, no internet dependency at runtime.

## Hardware

| Part | Reference choice |
|---|---|
| Computer | Raspberry Pi 5, 8 GB |
| Storage | 1 TB NVMe (2280) on a Pimoroni NVMe Base; boot and core drive, including the two book collections; PCIe Gen 2 (`install.sh --pcie-gen3` opts in) |
| Screen | Raspberry Pi Touch Display 2 (7", DSI), rotated to landscape by the kiosk session; any HDMI touchscreen also works |
| Cooling | Official Active Cooler; the printed case needs an intake and an exhaust path |
| Power | Official 27 W USB-C PSU; optional 20,000 mAh USB-C PD power bank (roughly 8 to 15 hours) |
| External drive | Optional self-powered USB 3 HDD or SSD, ext4, filesystem label `SOS-EXT`, for Khan Academy, media and your own files |

Storage layout on the box: `/srv/sos/core/{zim,maps,docs,models}` (NVMe), `/srv/sos/extended/{zim,docs,media,video,books}` (USB), `/srv/sos/state` (database, `library.xml`, playbooks, manifest, config), `/srv/sos/web` (built frontend), `/srv/sos/api` (the `sos` package and its venv).

## Install on the Pi

1. Flash 64-bit Raspberry Pi OS Lite (Trixie) to the NVMe, boot it, and set the boot order once with `sudo raspi-config` (Advanced Options, Boot Order, NVMe/USB).
2. Get the repository onto the Pi over ethernet on the home LAN: `git clone <this repository> ~/OperationSOS`.
3. Optionally copy `install/answers.env.example` to `install/answers.env` and fill in the admin PIN, SSID and passphrase; without it the installer prompts.
4. Run the installer as root:

   ```bash
   cd ~/OperationSOS
   sudo install/install.sh --dry-run   # prints every step and file, writes nothing
   sudo install/install.sh             # the llama.cpp build is most of the time (about 10 minutes)
   sudo reboot
   ```

   Flags: `--skip-llama` (no AI build), `--with-jellyfin` (media server; not together with the AI on 8 GB), `--pcie-gen3` (NVMe at Gen 3 once you have tested your drive), `--dev` (PC profile: no hotspot, mount, backlight, kiosk or boot steps).

5. After the reboot the screen shows the app, the hotspot `SOS` is up, and a phone on it opens `http://10.42.0.1` (or `http://sos.box`). Plug ethernet into a home router and the box is also at `http://sos.local`.

The installer is idempotent: run it again after pulling changes and every step that is already done reports `unchanged`, ending in `install complete: no changes`. From the PC, `make deploy HOST=sos.local` rsyncs the API, the built frontend, the playbooks and the manifest to a box on the LAN, runs `sos index` and restarts `sos-api`. Pinned versions live in `install/versions.env`; the systemd units, Caddyfile, NetworkManager profiles, udev rule, sudoers rule, kiosk wrapper and boot fragment are the files under `install/`.

## Develop on the PC

Prerequisites: Python 3.12 or newer, Node 22 or newer with pnpm, and on `PATH` `kiwix-serve`, `kiwix-manage` and `kiwix-search` 3.8.2 and `caddy` 2.11.4 (on the reference PC they live in `~/.local/bin`). Sample content lives in `~/sos-content` (`zim/` with six sample ZIMs, `models/` with two GGUF files); `dev/manifest/core.json` describes it.

```bash
make venv      # api/.venv with the sos package and the dev tools (pytest, respx, ruff, shellcheck)
make test      # pytest, vitest (when web/ exists), sos validate-playbooks, the smoke self-test
make dev       # kiwix-serve :8090, sos-api :8000 (SOS_DEV=1), caddy :8080 with the production Caddyfile
dev/smoke.sh   # in another terminal: one PASS or FAIL line per check against http://127.0.0.1:8080
make build     # vite build into web/dist; make dev then serves the real app instead of the placeholder
make e2e       # Playwright against the dev stack
```

If `make venv` fails with `ensurepip is not available` (an Ubuntu without `python3-venv`), create the venv once by hand and `make` takes over from there:

```bash
python3 -m venv --without-pip api/.venv
python3 -m pip --python api/.venv/bin/python install pip
api/.venv/bin/pip install -e './api[dev]'
```

Playwright's Chromium on this PC needs the vendored system libraries, so run the browser tests as `LD_LIBRARY_PATH=$HOME/.local/chromium-deps/usr/lib/x86_64-linux-gnu make e2e` (the same variable in front of `pnpm --dir web exec playwright test`).

The dev stack keeps its state and logs under `.dev/` (ignored by git). Overrides: `SOS_CORE` (content root, default `/home/dan/sos-content`), `SOS_MANIFEST_DIR` (default `dev/manifest`), `SOS_PLAYBOOKS_DIR` (default `playbooks`; use `api/tests/fixtures/playbooks` for a populated tree before the content plan lands), `SOS_MODEL` (which GGUF the AI dev spawn uses), `SOS_HTTP_PORT`, `SOS_PORT`, `SOS_KIWIX_PORT`. `pnpm --dir web dev` serves the frontend with hot reload on 5173 and proxies `/api`, `/kiwix`, `/maps` and `/docs` to the Caddy on 8080.

`SOS_DEV=1` makes `sos-api` return fake values for the hotspot, temperature, backlight and NetworkManager instead of touching the system, and makes the AI spawn `llama-server` directly instead of through systemd.

## Content sync

Content is described by `manifest/*.json` (`core.json`, `extended.json`, `maps.json`, `overlays.json`) and validated against `manifest/schema.json`. On the box:

```bash
sudo -u sos /srv/sos/api/.venv/bin/sos sync --tier core --dry-run   # resolve every source, print what would be fetched
sudo -u sos /srv/sos/api/.venv/bin/sos sync --tier core             # download (aria2c, resumable, sha256-checked), then sos index
sudo -u sos /srv/sos/api/.venv/bin/sos sync --tier extended         # with the SOS-EXT drive plugged in
sudo -u sos /srv/sos/api/.venv/bin/sos validate-playbooks --deep    # every kiwix: and doc: target really exists
```

`kiwix` sources resolve to the newest file in the Kiwix catalogue; `url` sources download directly; `build` items (the NHS ZIM, the maps, the phone packs) are produced on the PC with `sos build-nhs` and `sos build-maps` and copied to the path the dry run prints. `sos index` (also run by the installer and at the end of `sync`) regenerates `library.xml`, rebuilds the search index for playbooks and documents, and imports `places.csv.gz` when it changes. The System screen's Update button runs the same sync over ethernet.

On the PC the same commands run against the dev manifest: `SOS_MANIFEST_DIR=dev/manifest SOS_CORE=$HOME/sos-content api/.venv/bin/sos sync --tier core --dry-run` reports every sample file as present.

## Repository structure

```
Makefile          dev, test, e2e, build, fixtures, deploy, venv, smoke
api/              the sos Python package (FastAPI API, CLI, sync, search, content) and its tests
web/              the React frontend (Vite), its unit tests and Playwright specs
playbooks/        authored Markdown: scenarios/, modules/, cards/, pages/, schema.json, README.md
manifest/         content manifests and their JSON schema
install/          install.sh, versions.env, systemd units, Caddyfile, NetworkManager, udev, sudoers, kiosk, boot
dev/              run-dev.sh, smoke.sh, the smoke self-test and the dev manifest
tools/            map style build and AI evaluation questions
docs/             the design spec, research, the implementation plans and the hardware checklist
```

