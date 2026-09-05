# Read aloud and the sensors

Two optional pieces of the box, both safe to leave out: without them the app hides the speaker button and the
sensor list stays empty. Versions and checksums are pinned in `install/versions.env`.

## Piper (read aloud)

`POST /api/speak` runs Piper with a British voice and returns a WAV the kiosk plays. Two manifest items in the
`ai` category: `piper` (the binaries) and `piper-voice-en_GB` (the voice).

    . install/versions.env
    ARCH=$(uname -m)                      # aarch64 on the Pi, x86_64 on a development PC
    case "$ARCH" in
      aarch64) URL=$PIPER_AARCH64_URL; SUM=$PIPER_AARCH64_SHA256 ;;
      x86_64)  URL=$PIPER_X86_64_URL;  SUM=$PIPER_X86_64_SHA256 ;;
    esac
    curl -fsSL -o /tmp/piper.tar.gz "$URL"
    echo "$SUM  /tmp/piper.tar.gz" | sha256sum -c -
    mkdir -p "$SOS_CORE/bin"
    tar xzf /tmp/piper.tar.gz -C "$SOS_CORE/bin"   # unpacks the directory core/bin/piper

    mkdir -p "$SOS_CORE/models/piper"
    curl -fsSL -o "$SOS_CORE/models/piper/$PIPER_VOICE.onnx"      "$PIPER_VOICE_ONNX_URL"
    curl -fsSL -o "$SOS_CORE/models/piper/$PIPER_VOICE.onnx.json" "$PIPER_VOICE_JSON_URL"
    echo "$PIPER_VOICE_ONNX_SHA256  $SOS_CORE/models/piper/$PIPER_VOICE.onnx" | sha256sum -c -
    echo "$PIPER_VOICE_JSON_SHA256  $SOS_CORE/models/piper/$PIPER_VOICE.onnx.json" | sha256sum -c -

Check it by hand:

    echo "Mains power is off. Fill the bath now." | \
      "$SOS_CORE/bin/piper/piper" --model "$SOS_CORE/models/piper/$PIPER_VOICE.onnx" --output_file /tmp/test.wav

The tarball ships its own `libonnxruntime`, `libespeak-ng` and `espeak-ng-data`, so nothing else is installed on
the box; the API adds the directory to `LD_LIBRARY_PATH` when it runs the binary. Roughly 115 MB unpacked, and one
short sentence takes well under a second on a Pi 5.

Settings, all optional:

| Variable | Default | Meaning |
|---|---|---|
| `SOS_PIPER_DIR` | `$SOS_CORE/bin/piper` | the directory holding the `piper` executable |
| `SOS_PIPER_VOICE` | `en_GB-alba-medium` | the file stem of the `.onnx` in `$SOS_CORE/models/piper` |
| `SOS_SPEAK_TIMEOUT_S` | `30` | how long one request may take before it is killed |

Any other en_GB medium voice from `rhasspy/piper-voices` works: drop its two files in and set `SOS_PIPER_VOICE`.

## The radio dongle (sensing and bulletins)

`sudo apt install rtl-sdr` puts `rtl_power` and `rtl_fm` on the PATH. Plug an RTL-SDR into a USB socket; nothing
else is needed and nothing breaks when it is absent. With it:

- `rtl_power` sweeps FM (87.5 to 108 MHz), DAB (174 to 240 MHz) and the 800 and 900 MHz mobile downlinks every ten
  minutes and records the band energy in dB. When both mobile bands go quiet after having been busy, the box
  proposes "mobile degraded" on the situation sheet — it never sets it for you.
- `rtl_fm` records the FM bulletins listed in `playbooks/rules/bulletins.yaml` into `$SOS_STATE/recordings/`, one
  WAV per slot, listed by `GET /api/recordings`. Long wave and medium wave (BBC Radio 4 on 198 kHz) are far below
  the dongle's 24 MHz floor: those entries carry `recordable: false` and are only ever listed, never recorded.
- Where a station's frequency changes from town to town, put your own `record_hz` (in hertz) in the bulletins file.

## The other sensors

| Sensor | What it needs on the Pi |
|---|---|
| `internet` | nothing; a DNS lookup and a short HTTP GET of `SOS_SENSOR_PROBE_URL` on a 3 s timeout |
| `mains` | a UPS HAT that publishes `/sys/class/power_supply/*/online`, or a GPIO pin exported to sysfs and named in `SOS_SENSOR_MAINS_GPIO` (add `SOS_SENSOR_MAINS_GPIO_ACTIVE_LOW=1` if the pin is pulled low while on mains) |
| `hotspot_clients`, `cpu_temp` | nothing beyond what the box already reads |
| `file` | a script of your own writing one number to each path in `SOS_SENSOR_FILES`, for example `SOS_SENSOR_FILES='{"temp_in":"/run/sos/temp_in","co_ppm":"/run/sos/co"}'`. The name fixes the unit: `temp_in`, `temp_out`, `humidity`, `pressure_hpa`, `co_ppm`, `radiation_usvh`, `leak`. |

`SOS_SENSORS=0` turns the whole background poll off. Readings land in the `sensor_readings` table and are pruned
after a fortnight; `GET /api/sensors` shows the latest of each and what the box concludes from them.

## Nearest facilities

`GET /api/nearby?lat=&lon=` reads the map overlays on the box. Two of them (`health`, `water`) are shipped as
PMTiles, which cannot be searched by point: set `SOS_MAPS_SRC` to the map build workspace (the directory holding
`overlays-work/`) so the API can read the GeoJSON the build kept. Without it those facilities answer with the
reason rather than a guess.

The first call parses the three overlays and keeps the points in memory: about a second and a 130 MB spike while
parsing, settling to roughly 25 MB held for the life of the process. Every later call, and the home's answer in
the situation View, is a cache read. Nothing carries fire stations or rest centres yet; the endpoint says so
rather than pointing you at the wrong building.
