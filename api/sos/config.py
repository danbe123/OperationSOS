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

    @property
    def db_path(self) -> Path:
        return self.state / "sos.db"

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
