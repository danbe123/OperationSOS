# Hardware checklist

Manual checks on the box (spec section 14). Close a row with the date, the commit tested and the result (`pass`, `fail` plus a note, or `n/a`). The milestone "Box" criteria from spec section 15 follow the table; a milestone closes only when its CI list (recorded under "CI runs") and its Box list both pass.

## Checklist

| # | Item | Date | Commit | Result |
|---|---|---|---|---|
| 1 | Hotspot join and captive portal on an iPhone and an Android, including a Samsung with mobile data on | | | |
| 2 | Fallback URLs and QR codes: `http://10.42.0.1` and `http://sos.box` from the welcome page and the Connect a phone panel | | | |
| 3 | `sos.local` from the home LAN while the hotspot keeps running | | | |
| 4 | Direct laptop link (eth0 shared, 10.43.0.1) survives a reboot | | | |
| 5 | Update over ethernet downloads one item | | | |
| 6 | External drive hot-plug and removal while browsing (items grey out within 10 seconds and come back) | | | |
| 7 | Display is landscape and touch lands where the finger is | | | |
| 8 | Backlight device present and controllable (or the 501 fallback overlay) | | | |
| 9 | Low power mode dims and stops AI | | | |
| 10 | Idle dim, wake without a click passing through, return to Home after 30 minutes | | | |
| 11 | Keyboard usable on the panel | | | |
| 12 | Open a 300-page PDF on iPhone and Android and jump to page 200 | | | |
| 13 | NVMe boot | | | |
| 14 | Pull the power during use and reboot to Home with no dialog | | | |
| 15 | Thermal under a 10-minute AI session in the printed case | | | |
| 16 | Thermal auto-off at a lowered threshold | | | |
| 17 | RAM with AI ready and two phones browsing (zero swap) | | | |
| 18 | Load with five phones browsing, one panning the map at z14 and one AI question in flight (search p95 under 3 seconds, no OOM kills, under 80°C for 10 minutes) | | | |
| 19 | Power-bank runtime with the screen lit | | | |
| 20 | `install.sh` run twice with no changes the second time | | | |

## Milestone box criteria (spec section 15)

- **1 Skeleton**: a phone joins `SOS`; the portal pops on one iPhone and one Android; both addresses load; the kiosk shows the app; `install.sh` a second time reports no changes (rows 1, 2, 7, 20).
- **2 App shell, library, reader, search**: the Playwright suite passes against `http://10.42.0.1` from a laptop on the hotspot.
- **3 Maps**: full outputs installed, sizes recorded in `manifest/maps.json`, pan and zoom at z15 on the kiosk and one phone with zero 4xx/5xx for `/maps/*`.
- **4 Playbooks**: print view of one playbook from a phone.
- **5 Full content**: `sos sync --tier core` completes; every core item available; core size within 10% of the manifest sum; unplugging the drive greys its items within 10 seconds and replugging restores them; `sos validate-playbooks --deep` passes (row 6).
- **6 AI**: `sos eval` full run with median time to first token at most 90 seconds, generation at least 7 tokens per second, zero swap, CPU under 80°C; results file committed (rows 15, 17).
- **7 Polish and hardware**: the full checklist above in the printed case.

## CI runs

| Milestone | Date | Commit | Result |
|---|---|---|---|
| 1 Skeleton | 2026-09-04 | 49db6fa | pass (shellcheck, dry-run golden, caddy validate, systemd-analyze verify, probe paths, fixture ZIM via /kiwix/, make dev + smoke) |

## Maps

Recorded by the maps pipeline plan after its fixture build.
