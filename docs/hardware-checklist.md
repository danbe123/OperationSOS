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
| 21 | Mains sensor detects a power cut: pull the plug on the UPS HAT and the box records `mains 0` within two polls (120 s) and offers "Mains power off" on the situation sheet | | | |
| 22 | Internet probe flips within three minutes: unplug the uplink and the box proposes "Internet off" after three failed probes | | | |
| 23 | Board appears on the kiosk when a condition is set off from a phone (kiosk idle, phone sets power off, board within one poll) | | | |
| 24 | Read aloud plays through the speaker: a briefing spoken from the kiosk at arm's length in a quiet room | | | |
| 25 | A drill runs end to end: start from the sheet, work the board, tick the tasks, end the drill and read the summary event | | | |
| 26 | A situation export scans between two phones: QR sequence on one, scanned and imported on the other, summary names what changed | | | |

## What the hardware has to provide

Every driver in `api/sos/sensors.py` is optional; the box runs with none of them. What each one needs on the Pi:

| Driver | Sensor rows | What it needs | Settings |
|---|---|---|---|
| Internet probe | `internet` | Nothing but the uplink: one DNS lookup and one short HTTP GET on a three-second timeout. Three failed polls running before the box proposes "Internet off" | `SOS_SENSOR_PROBE_HOST`, `SOS_SENSOR_PROBE_URL`, `SOS_SENSOR_PROBE_TIMEOUT_S` |
| Mains | `mains` | A UPS HAT that registers as a power supply and publishes `/sys/class/power_supply/*/online` (battery paths are skipped), or a HAT that only pulls a GPIO pin, exported to sysfs and named in the settings | `SOS_SENSOR_MAINS_GLOB`, `SOS_SENSOR_MAINS_GPIO`, `SOS_SENSOR_MAINS_GPIO_ACTIVE_LOW` |
| Box | `hotspot_clients`, `cpu_temp` | Nothing beyond what `sos.system` already reads: the hostapd station list and the thermal zone | — |
| File | any name in the map | A script of your own writing one number per file — an I2C thermometer, a leak pad, a Geiger counter. The name fixes the unit (`temp_in` C, `humidity` %, `pressure_hpa` hPa, `co_ppm` ppm, `radiation_usvh` uSv/h, `leak` bool) | `SOS_SENSOR_FILES='{"temp_in": "/run/sos/temp_in"}'` |
| Sweeps | `band_fm`, `band_dab`, `band_mobile_800`, `band_mobile_900` | `rtl_power` on PATH and an RTL-SDR dongle in a USB socket. A mobile band 10 dB below its own recent best, after at least three readings, is what makes the box suspect the masts have gone | `SOS_RTL_POWER_BIN`, `SOS_RTL_POWER_DWELL_S` |
| Recording | bulletin WAVs in `state/recordings/` | The same dongle plus `rtl_fm`. Long and medium wave (Radio 4 on 198 kHz) is below the dongle's 24 MHz floor and is marked `recordable: false` in `playbooks/rules/bulletins.yaml` | `SOS_RTL_FM_BIN` |

The cheap drivers run every `SOS_SENSOR_INTERVAL_S` (60 s by default) and the sweeps every `SOS_RTL_INTERVAL_S` (10 minutes); `SOS_SENSORS=0` turns the whole background task off.

Hardware the box expects around it:

- **RTL-SDR dongle** (RTL2832U, R820T2 or R860 tuner). USB 2 socket, tunes 24 MHz to 1.766 GHz, so it hears FM, DAB and the mobile downlink bands but not long or medium wave. It draws about 300 mA and runs warm; keep it out of the case airflow and on a short extension away from the Pi's own USB 3 noise. A telescopic whip on a ground plane is enough for the sweeps; recording a bulletin wants the whip outside or in a window.
- **UPS HAT** with an 18650 pair or a supercapacitor bank. It has to hold the Pi and the panel long enough to finish a write and shut down cleanly, and it has to expose the mains state either as a power supply class device or as a GPIO pin. Fit it below the panel so its own heat does not sit under the SoC. The mains sensor is what turns a power cut into a proposal on the sheet rather than a mystery.
- **Speaker for read aloud**: a small amplified speaker on the 3.5 mm jack, or a USB or I2S class-compliant device (a MAX98357A breakout on I2S is the tidiest inside a printed case). Piper (`SOS_PIPER_DIR`, `SOS_PIPER_VOICE`, default `en_GB-alba-medium`) writes a WAV and the browser plays it, so anything ALSA can see will do; check the volume is usable at arm's length with the case shut, because the kiosk has no volume knob.

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

Maps CI (plan 04): sos build-maps --fixture passed with pmtiles verify on every output on 2026-09-05, commit 3a7e5ec, fixture base 4935818 bytes
