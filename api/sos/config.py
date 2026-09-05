"""Environment-driven settings. Every path and URL the package uses comes from here."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SOS_", extra="ignore")

    core: Path = Path("/srv/sos/core")
    ext: Path = Path("/srv/sos/extended")
    state: Path = Path("/srv/sos/state")
    web: Path = Path("/srv/sos/web")
    manifest_dir: Path | None = None
    playbooks_dir: Path | None = None
    kiwix_url: str = "http://127.0.0.1:8090/kiwix"
    llama_url: str = "http://127.0.0.1:8081"
    model: str = "gemma-4-E2B-it-Q4_K_M.gguf"
    dev: bool = False
    port: int = 8000

    # The map build workspace, when it is still on the machine: overlays the build turned into PMTiles
    # (health, water) have no GeoJSON on the box, and `sos.nearby` reads the source files from here.
    maps_src: Path | None = None

    # Read aloud (spec section 6): Piper and its British voice, both manifest items in the `ai` category.
    piper_dir: Path | None = None
    piper_voice: str = "en_GB-alba-medium"
    speak_timeout_s: float = 30.0

    # Sensors (spec section 2). Every driver is optional; a missing path or binary simply records nothing.
    sensors: bool = True
    sensor_probe_host: str = "one.one.one.one"
    sensor_probe_url: str = "http://one.one.one.one/"
    sensor_probe_timeout_s: float = 3.0
    sensor_mains_glob: str = "/sys/class/power_supply/*/online"
    sensor_mains_gpio: str = ""                       # e.g. /sys/class/gpio/gpio17/value on a UPS HAT
    sensor_mains_gpio_active_low: bool = False
    sensor_files: dict[str, str] = {}                 # SOS_SENSOR_FILES='{"temp_in": "/run/sos/temp_in"}'
    sensor_interval_s: float = 60.0
    rtl_interval_s: float = 600.0
    rtl_power_bin: str = "rtl_power"
    rtl_fm_bin: str = "rtl_fm"
    rtl_power_dwell_s: int = 8
    bulletin_window_s: int = 300                      # how long a recorded bulletin runs

    @property
    def db_path(self) -> Path:
        return self.state / "sos.db"

    @property
    def recordings(self) -> Path:
        return self.state / "recordings"

    @property
    def piper_bin(self) -> Path:
        return (self.piper_dir or self.core / "bin" / "piper") / "piper"

    @property
    def piper_voice_path(self) -> Path:
        return self.core / "models" / "piper" / f"{self.piper_voice}.onnx"

    @property
    def library_xml(self) -> Path:
        return self.state / "library.xml"

    @property
    def manifests(self) -> Path:
        return self.manifest_dir or self.state / "manifest"

    @property
    def playbooks(self) -> Path:
        return self.playbooks_dir or self.state / "playbooks"

    @property
    def config_dir(self) -> Path:
        return self.state / "config"

    def tier_root(self, tier: str) -> Path:
        return self.ext if tier == "extended" else self.core


@lru_cache
def get_settings() -> Settings:
    return Settings()
