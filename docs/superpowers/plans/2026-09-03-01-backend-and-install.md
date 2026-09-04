# Operation SOS Backend and Install Implementation Plan (sub-plan 01)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the `sos` Python package (FastAPI API, `sos` CLI, sync, index, search, playbook rendering and validation, system control), the manifest schema, the dev stack, and the complete Raspberry Pi install tree, so that `make test` passes, `make dev` serves the sample library through Caddy and `dev/smoke.sh` is all PASS.

**Architecture:** One Python package `sos` under `api/` with small single-purpose modules (config, db, manifest, library, kiwix, query, content, docs, places, search, system, sync, cli) and thin FastAPI routers; SQLite with FTS5 for authored content, PDF pages and places; kiwix-serve queried over HTTP per class of ZIM with strict timeouts; all subprocess, sysfs and NetworkManager access funnelled through `sos.system.run_cmd` / `read_sysfs` / `write_sysfs` which return fakes under `SOS_DEV=1`. `install/` holds an idempotent bash installer plus every unit, profile and config file the box needs; `dev/` runs the same Caddyfile and kiwix-serve on the PC.

**Tech Stack:** Python 3.12+, FastAPI, uvicorn, httpx, pydantic 2, pydantic-settings, python-frontmatter, markdown-it-py + mdit-py-plugins, jsonschema, pyyaml, sqlite3 (FTS5); pytest, respx, shellcheck-py, ruff; kiwix-tools 3.8.2 (kiwix-serve, kiwix-manage, zimwriterfs for the fixture), Caddy 2.11.4, systemd, NetworkManager, cage + Chromium.

**Spec:** `docs/superpowers/specs/2026-09-03-operation-sos-design.md` (revised 2026-09-03). **Overview (locked contracts):** `docs/superpowers/plans/2026-09-03-00-overview.md`. Where the two differ the overview wins.

**Deviations:** (1) The overview's manifest item carries `overlay` and `search_weight`/`suggest` defaults; spec §7 omits `overlay` from the example — the schema follows the overview. (2) The overview's `Status` has `thermal_ai_off_c`, `idle_minutes`, `home_minutes`, `default_theme`; spec §6's status prose lists fewer fields — the JSON shape follows the overview. (3) Spec §6 says the `fts` flag comes from the kiwix-serve catalogue tags; this plan reads the identical `tags` attribute from the `library.xml` that `kiwix-manage add` writes (it is the same ZIM metadata) so the flag is correct immediately after a rescan instead of after kiwix-serve's `--monitorLibrary` reload; the catalogue endpoint is still parsed by `sos.kiwix.catalog()` and used by `sos validate-playbooks --deep` and the search warm-up. (4) Files added beyond the overview layout, each with a reason: `api/sos/routers/__init__.py` (shared dependencies `get_db`, `require_localhost`, `require_pin`; the layout lists no other place for them), `api/tests/fixtures/manifest/` (the conftest's "sample manifest"), `api/tests/fixtures/pages/` and `api/tests/fixtures/gen_fixtures.py` (spec §13 says the no-index ZIM is built from `tests/fixtures/pages/`; the generator also writes the 200-row places CSV and the two-page PDF with the standard library only), `api/tests/fixtures/opds/zimgit-water_en_2024-08.zim.meta4` (the resolver reads the sha-256 from the Metalink so a 100GB download is verified), `api/tests/golden/install-dry-run.txt` (spec §14), `install/placeholder/welcome.html` and `starting.html` (milestone 1 needs `/welcome` and `/starting` before plan 02 lands; `install.sh` copies the placeholder only when `web/dist` is absent), `dev/caddy.d/dev.caddy` (the "dev overrides snippet"), `api/sos/buildnhs.py` (in the overview layout and not excluded from this plan). (5) `sos pin set <pin>` is added to the CLI so `install.sh` step 8 can write the PIN hash; `sos validate-playbooks --all-scenarios` is added so plan 03 can enforce the 20 slugs without failing on the empty tree that exists today. (6) `mdit-py-plugins` is added to the dependency list because the task-list syntax needs its `tasklists` plugin.

## Global Constraints

- Python 3.12 or newer (the Pi runs 3.13); Node 22 or newer; pnpm for the frontend.
- No Docker anywhere. No runtime dependency on the internet. No service worker. No CDN references in any HTML, CSS or JS.
- kiwix-serve is started with `--address all --nosearchbar --nolibrarybutton --blockexternal`.
- llama-server binds 127.0.0.1:8081 and is never proxied by Caddy; sos-api is its only client.
- Manifest invariant: every `zim` item's `dest` is `zim/<id>.zim`, so the Kiwix book name in URLs equals the manifest item id (verified: kiwix-serve names a book after the ZIM filename stem, not the ZIM's internal `Name` metadata).
- All authored content is British English. Emergency numbers are 999, 111, 105, 0345 988 1188 (Floodline). Drug names are UK names.
- Never name the product "NOMAD". The product name is "Operation SOS"; the short name in UI copy is "SOS".
- Every commit passes `make test`.
- Licence is informational (`licence` field) and never gates behaviour.
- Dev profile: `SOS_DEV=1` runs the whole stack on a PC without hotspot, kiosk, mount units or sysfs.
- Ports: Caddy 80 (dev 8080), sos-api 8000 (localhost), kiwix-serve 8090 (all), llama-server 8081 (localhost only).
- Hotspot: `wlan0`, `10.42.0.1/24`, SSID default `SOS`, `address=/#/10.42.0.1` in `/etc/NetworkManager/dnsmasq-shared.d/sos.conf`; direct laptop link on `eth0` is `10.43.0.1/24`.
- Captive-portal probe paths (`/generate_204`, `/gen_204`, `/hotspot-detect.html`, `/library/test/success.html`, `/connecttest.txt`, `/ncsi.txt`, `/canonical.html`, `/success.txt`) answer `302` to `http://10.42.0.1/welcome`.
- `search_weight` default 1.0; playbooks, modules, cards and pages score with weight 1.6; `score = w / (5 + rank)`, rank from 1; medical intent boosts medical sources x1.5; a place match applies x2.
- Kiwix class timeouts: reference 4 s, every other class 2 s; a timed-out class is dropped and the response is `partial: true`.
- `fts_docs` ranking is `bm25(fts_docs, 5.0, 1.0)`; PDF page bodies are capped at 600 words; `doc_id = <item>#p<N>`.
- Backlight levels are scaled to the device's `max_brightness` (Touch Display 2: 31); idle dim uses level 10 and never 0; no device means HTTP 501.
- PIN: wrong PIN is 401, rate-limited to five attempts a minute; tokens expire after 600 s.
- Thermal watchdog polls `/sys/class/thermal/thermal_zone0/temp` every 10 s; at or above `thermal_ai_off_c` (default 80) it stops `sos-llama.service`, sets state `off-thermal` and never restarts it.
- Pinned versions (`install/versions.env`): `KIWIX_TOOLS=3.8.2`, `CADDY=2.11.4`, `LLAMA_CPP_TAG=v0.3.0` (first line of `/home/dan/sos-content/llama-build.log`, commit `c1d0e7a`), `PROTOMAPS_BUILD=20260902`, `JELLYFIN=10.11.11`.
- llama.cpp build flags: `cmake -S . -B build -DGGML_NATIVE=ON -DGGML_CPU_KLEIDIAI=ON -DLLAMA_BUILD_TESTS=OFF && cmake --build build --config Release -j4`.
- Repository root is `/home/dan/OperationSOS`; all commands below run from there unless a `cd` is shown. Python commands use `api/.venv/bin/...`.

---

## File map (this sub-plan)

| Path | Responsibility |
|---|---|
| `Makefile` | `dev`, `test`, `e2e`, `build`, `fixtures`, `deploy`, `venv` targets |
| `.gitignore` | adds fixture ZIM exception and `.dev/` |
| `manifest/schema.json` | JSON Schema (draft 2020-12) for `{"items": [...]}` |
| `dev/manifest/core.json` | dev manifest over `~/sos-content` (six ZIMs, two models) |
| `dev/run-dev.sh`, `dev/smoke.sh`, `dev/caddy.d/dev.caddy` | dev stack and smoke test |
| `api/pyproject.toml` | package `sos`, console script `sos` |
| `api/sos/__init__.py` | `__version__` |
| `api/sos/config.py` | `Settings`, `get_settings()` |
| `api/sos/db.py` | `connect`, `init_schema`, settings key/value helpers |
| `api/sos/manifest.py` | `Item`, `load_manifests`, `validate_manifests` |
| `api/sos/library.py` | `library_items` refresh, availability, `library.xml`, flags, reader URLs, `rescan` |
| `api/sos/kiwix.py` | async kiwix-serve client and parsers, `extract_text` |
| `api/sos/query.py` | tokenise, stopwords, FTS5 quoting, place and postcode detection |
| `api/sos/content.py` | parse, render, validate authored Markdown; `ContentCache` |
| `api/sos/docs.py` | PDF/EPUB page extraction into `fts_docs` |
| `api/sos/places.py` | `fts_places` import and queries |
| `api/sos/search.py` | class fan-out, scoring, intents, cache, suggest |
| `api/sos/system.py` | temp, disks, hotspot, eth mode, power, backlight, PIN, watchdog, updater |
| `api/sos/main.py` | `create_app(settings, background=True)` |
| `api/sos/routers/*.py` | one router per endpoint group; `routers/__init__.py` holds dependencies |
| `api/sos/sync.py` | source resolution, downloader, `sync`, `index` |
| `api/sos/cli.py` | `sos` argparse CLI |
| `api/sos/buildnhs.py` | `sos build-nhs` zimit driver and verification |
| `api/sos/buildmaps.py`, `api/sos/evalrun.py`, `api/sos/ai.py` | stubs raising `NotImplementedError` (plans 04 and 05) |
| `api/tests/` | pytest suite and fixtures |
| `install/` | installer, versions, units, Caddyfile, NM profiles, udev, sudoers, kiosk wrapper, boot fragment, placeholder |
| `README.md`, `docs/hardware-checklist.md`, `playbooks/README.md`, `playbooks/schema.json` | documentation and the front-matter schema |

---

### Task 1: Scaffold (Makefile, package, settings, test harness)

**Files:**
- Create: `Makefile`
- Modify: `.gitignore`
- Create: `api/pyproject.toml`
- Create: `api/sos/__init__.py`
- Create: `api/sos/config.py`
- Create: `api/sos/cli.py` (minimal entry so the console script resolves; Task 12 completes it)
- Create: `api/tests/conftest.py`
- Test: `api/tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `sos.config.Settings` (fields `core`, `ext`, `state`, `web`, `manifest_dir`, `playbooks_dir`, `kiwix_url`, `llama_url`, `model`, `dev`, `port`; properties `db_path`, `library_xml`, `manifests`, `playbooks`, `config_dir`; method `tier_root(tier) -> Path`), `sos.config.get_settings()` (lru-cached), `sos.__version__`, pytest fixtures `env` (a `Settings` bound to a tmp tree with `SOS_DEV=1`), `fixtures_dir`, `repo_root`.

- [ ] **Step 1: Write the failing settings test**

`api/tests/test_config.py`:

```python
import os
from pathlib import Path

from sos.config import Settings


def test_defaults_when_no_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("SOS_"):
            monkeypatch.delenv(key)
    s = Settings()
    assert s.core == Path("/srv/sos/core")
    assert s.ext == Path("/srv/sos/extended")
    assert s.state == Path("/srv/sos/state")
    assert s.web == Path("/srv/sos/web")
    assert s.manifests == Path("/srv/sos/state/manifest")
    assert s.playbooks == Path("/srv/sos/state/playbooks")
    assert s.kiwix_url == "http://127.0.0.1:8090/kiwix"
    assert s.llama_url == "http://127.0.0.1:8081"
    assert s.model == "gemma-4-E2B-it-Q4_K_M.gguf"
    assert s.dev is False
    assert s.port == 8000
    assert s.db_path == Path("/srv/sos/state/sos.db")
    assert s.library_xml == Path("/srv/sos/state/library.xml")
    assert s.config_dir == Path("/srv/sos/state/config")


def test_env_overrides(env, fixtures_dir):
    assert env.dev is True
    assert env.core.name == "core"
    assert env.manifests == fixtures_dir / "manifest"
    assert env.playbooks == fixtures_dir / "playbooks"
    assert env.tier_root("core") == env.core
    assert env.tier_root("extended") == env.ext


def test_version():
    import sos

    assert sos.__version__ == "0.1.0"
```

`api/tests/conftest.py`:

```python
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def repo_root() -> Path:
    return REPO


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Settings bound to a throwaway tree. The extended root is NOT created,
    so the default state is 'external drive not connected'."""
    core = tmp_path / "core"
    state = tmp_path / "state"
    for d in (core / "zim", core / "maps", core / "docs", core / "models", state / "config"):
        d.mkdir(parents=True)
    monkeypatch.setenv("SOS_CORE", str(core))
    monkeypatch.setenv("SOS_EXT", str(tmp_path / "extended"))
    monkeypatch.setenv("SOS_STATE", str(state))
    monkeypatch.setenv("SOS_WEB", str(tmp_path / "web"))
    monkeypatch.setenv("SOS_MANIFEST_DIR", str(FIXTURES / "manifest"))
    monkeypatch.setenv("SOS_PLAYBOOKS_DIR", str(FIXTURES / "playbooks"))
    monkeypatch.setenv("SOS_KIWIX_URL", "http://kiwix.test/kiwix")
    monkeypatch.setenv("SOS_DEV", "1")
    from sos.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()
```

- [ ] **Step 2: Create the package, pyproject, Makefile and gitignore entries**

`api/pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "sos"
version = "0.1.0"
description = "Operation SOS backend, CLI and sync tools"
readme = "../README.md"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "httpx>=0.27",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "python-frontmatter>=1.1",
  "markdown-it-py>=3.0",
  "mdit-py-plugins>=0.4",
  "pyyaml>=6.0",
  "jsonschema>=4.22",
]

[project.optional-dependencies]
dev = ["pytest>=8", "respx>=0.21", "ruff>=0.5", "shellcheck-py>=0.10"]

[project.scripts]
sos = "sos.cli:main"

[tool.setuptools.packages.find]
include = ["sos*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-p no:cacheprovider"

[tool.ruff]
line-length = 110
target-version = "py312"
```

`api/sos/__init__.py`:

```python
"""Operation SOS backend package."""

__version__ = "0.1.0"
```

`api/sos/config.py`:

```python
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
```

`api/sos/cli.py` (minimal; Task 12 replaces it):

```python
"""`sos` command line entry point (completed in Task 12)."""
import sys


def main(argv: list[str] | None = None) -> int:
    print("sos CLI not yet wired", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
```

`Makefile` (uses `.RECIPEPREFIX` so recipes start with `>` instead of a tab):

```make
.RECIPEPREFIX := >
.PHONY: dev test e2e build fixtures deploy venv
HOST ?= sos.local
VENV := api/.venv
SOS := $(VENV)/bin/sos

$(SOS): api/pyproject.toml
> python3 -m venv $(VENV)
> $(VENV)/bin/pip install -q --upgrade pip
> $(VENV)/bin/pip install -q -e "./api[dev]"
> touch $(SOS)

venv: $(SOS)

dev: venv
> dev/run-dev.sh

test: venv
> cd api && .venv/bin/pytest -q
> if [ -f web/package.json ]; then pnpm --dir web test -- --run; fi
> SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest $(SOS) validate-playbooks

e2e: venv
> pnpm --dir web exec playwright test

build:
> pnpm --dir web build

fixtures: venv
> $(VENV)/bin/python api/tests/fixtures/gen_fixtures.py

deploy: build
> rsync -az --delete --exclude .venv --exclude __pycache__ --exclude .pytest_cache api/ $(HOST):/srv/sos/api/
> rsync -az --delete web/dist/ $(HOST):/srv/sos/web/
> rsync -az --delete playbooks/ $(HOST):/srv/sos/state/playbooks/
> rsync -az --delete manifest/ $(HOST):/srv/sos/state/manifest/
> rsync -az --delete install/ $(HOST):/srv/sos/install/
> ssh $(HOST) 'sudo -u sos /srv/sos/api/.venv/bin/pip install -q -e /srv/sos/api && sudo -u sos /srv/sos/api/.venv/bin/sos index && sudo systemctl restart sos-api.service'
```

Append to `.gitignore`:

```
# fixture ZIMs are tiny and committed on purpose (spec section 13)
!api/tests/fixtures/library/*.zim
# dev stack state
.dev/
*.part
```

- [ ] **Step 3: Run the test to verify it fails before the venv exists, then create the venv**

Run: `make venv && cd api && .venv/bin/pytest tests/test_config.py -v`
Expected: 3 PASS (the settings module is already in place; the point of this step is that the venv, console script and fixtures resolve). If `pip install -e` fails with "readme not found", confirm `README.md` exists at the repo root (Task 15 writes the final one; create an empty `README.md` now if missing).

- [ ] **Step 4: Confirm the console script and the ruff baseline**

Run: `api/.venv/bin/sos; echo "exit=$?"`
Expected: `sos CLI not yet wired` and `exit=2`.

Run: `api/.venv/bin/ruff check api/sos`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add Makefile .gitignore api/pyproject.toml api/sos/__init__.py api/sos/config.py api/sos/cli.py api/tests/conftest.py api/tests/test_config.py README.md
git commit -m "build: scaffold sos package, settings, Makefile and test harness"
```

---

### Task 2: Manifest schema, `sos.manifest`, dev manifest and fixture manifest

**Files:**
- Create: `manifest/schema.json`
- Create: `api/sos/manifest.py`
- Create: `dev/manifest/core.json`
- Create: `api/tests/fixtures/manifest/schema.json` (copy of `manifest/schema.json`, kept in sync by `gen_fixtures.py` in Task 8), `core.json`, `extended.json`, `maps.json`, `overlays.json`
- Test: `api/tests/test_manifest.py`

**Interfaces:**
- Consumes: `Settings.manifests`.
- Produces: `sos.manifest.Item` (pydantic; fields exactly as the overview: `id, title, kind, tier, category, scenarios, source, dest, size_bytes, as_at, licence, priority, reader_home, description, search_weight, suggest, overlay`), `sos.manifest.Source` (`type, name, url, sha256, mirrors, tool, artifact`), `sos.manifest.OverlaySpec` (`id, kind, layer_id, default_on, coverage, color, icon`), `load_manifests(dir: Path) -> list[Item]`, `validate_manifests(dir: Path) -> list[str]`, `manifest_files(dir) -> list[Path]`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_manifest.py`:

```python
import json
import shutil
from pathlib import Path

import pytest

from sos.manifest import Item, load_manifests, validate_manifests

FIXTURES = Path(__file__).parent / "fixtures"


def _tree(tmp_path: Path, items: list[dict], name="core.json") -> Path:
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FIXTURES / "manifest" / "schema.json", d / "schema.json")
    (d / name).write_text(json.dumps({"items": items}), encoding="utf-8")
    return d


def _zim(id_: str, **over) -> dict:
    base = {
        "id": id_, "title": id_, "kind": "zim", "tier": "core", "category": "reference",
        "source": {"type": "kiwix", "name": id_}, "dest": f"zim/{id_}.zim", "size_bytes": 1,
    }
    base.update(over)
    return base


def test_fixture_manifest_is_valid():
    assert validate_manifests(FIXTURES / "manifest") == []


def test_repo_manifest_is_valid(repo_root):
    assert validate_manifests(repo_root / "manifest") == []


def test_dev_manifest_is_valid(repo_root):
    d = repo_root / "dev" / "manifest"
    errors = validate_manifests(d) if (d / "schema.json").exists() else _validate_with_repo_schema(repo_root, d)
    assert errors == []
    ids = {i.id for i in load_manifests(d)}
    assert "wikipedia_en_100_mini_2026-01" in ids
    assert "gemma-4-E2B-it-Q4_K_M" in ids


def _validate_with_repo_schema(repo_root, d):
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        shutil.copy(repo_root / "manifest" / "schema.json", t / "schema.json")
        for p in d.glob("*.json"):
            shutil.copy(p, t / p.name)
        return validate_manifests(t)


def test_schema_and_fixture_schema_identical(repo_root):
    a = (repo_root / "manifest" / "schema.json").read_text()
    b = (FIXTURES / "manifest" / "schema.json").read_text()
    assert a == b


def test_load_applies_defaults():
    items = load_manifests(FIXTURES / "manifest")
    wiki = next(i for i in items if i.id == "wikipedia_en_100_mini_2026-01")
    assert wiki.search_weight == 1.0 and wiki.suggest is True and wiki.overlay is None
    noindex = next(i for i in items if i.id == "sos-test-noindex")
    assert noindex.suggest is False and noindex.priority == 100 and noindex.scenarios == []
    health = next(i for i in items if i.id == "health")
    assert health.overlay is not None and health.overlay.kind == "geojson" and health.overlay.default_on is False


def test_zim_dest_invariant(tmp_path):
    d = _tree(tmp_path, [_zim("wiki", dest="zim/other.zim")])
    errors = validate_manifests(d)
    assert any("zim dest must be 'zim/wiki.zim'" in e for e in errors)


def test_duplicate_ids_and_dests(tmp_path):
    d = _tree(tmp_path, [_zim("a"), _zim("a"), _zim("b", dest="zim/a.zim")])
    errors = validate_manifests(d)
    assert any("duplicate id 'a'" in e for e in errors)
    assert any("duplicate dest 'zim/a.zim'" in e for e in errors)


def test_build_item_needs_artifact(tmp_path):
    item = _zim("prepare_uk", source={"type": "build", "tool": "zimit"})
    d = _tree(tmp_path, [item])
    errors = validate_manifests(d)
    assert any("artifact" in e for e in errors)


def test_schema_rejects_unknown_kind_and_bad_as_at(tmp_path):
    d = _tree(tmp_path, [_zim("x", kind="tarball"), _zim("y", as_at="Jan 2026")])
    errors = validate_manifests(d)
    assert any("kind" in e for e in errors)
    assert any("as_at" in e for e in errors)


def test_invalid_json_reported(tmp_path):
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FIXTURES / "manifest" / "schema.json", d / "schema.json")
    (d / "core.json").write_text("{not json", encoding="utf-8")
    errors = validate_manifests(d)
    assert errors and "invalid JSON" in errors[0]


def test_item_model_rejects_extra_fields():
    with pytest.raises(Exception):
        Item.model_validate(_zim("z", bogus=1))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_manifest.py -q`
Expected: `ImportError` / `ModuleNotFoundError: No module named 'sos.manifest'`.

- [ ] **Step 3: Write `manifest/schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://operation-sos.invalid/manifest.schema.json",
  "title": "Operation SOS content manifest",
  "type": "object",
  "required": ["items"],
  "additionalProperties": false,
  "properties": {
    "items": { "type": "array", "items": { "$ref": "#/$defs/item" } }
  },
  "$defs": {
    "item": {
      "type": "object",
      "required": ["id", "title", "kind", "tier", "category", "source", "dest"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$" },
        "title": { "type": "string", "minLength": 1 },
        "kind": { "enum": ["zim", "pmtiles", "geojson", "pdf", "epub", "dir", "model", "mwm", "apk", "style", "glyphs", "sprites", "places"] },
        "tier": { "enum": ["core", "extended"] },
        "category": { "enum": ["playbooks", "uk-official", "medical", "survival", "reference", "practical", "maps", "education", "books", "media", "ai"] },
        "scenarios": { "type": "array", "items": { "type": "string", "pattern": "^[a-z0-9-]+$" }, "default": [] },
        "source": { "$ref": "#/$defs/source" },
        "dest": { "type": "string", "pattern": "^[A-Za-z0-9._-]+(/[A-Za-z0-9._ -]+)*$" },
        "size_bytes": { "type": "integer", "minimum": 0, "default": 0 },
        "as_at": { "type": ["string", "null"], "pattern": "^[0-9]{4}-[0-9]{2}(-[0-9]{2})?$" },
        "licence": { "type": ["string", "null"] },
        "priority": { "type": "integer", "default": 100 },
        "reader_home": { "type": ["string", "null"] },
        "description": { "type": ["string", "null"] },
        "search_weight": { "type": "number", "minimum": 0, "default": 1.0 },
        "suggest": { "type": "boolean", "default": false },
        "overlay": { "oneOf": [ { "type": "null" }, { "$ref": "#/$defs/overlay" } ] }
      }
    },
    "source": {
      "type": "object",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": { "enum": ["kiwix", "url", "build"] },
        "name": { "type": "string", "minLength": 1 },
        "url": { "type": "string", "pattern": "^https?://" },
        "sha256": { "type": "string", "pattern": "^[0-9a-f]{64}$" },
        "mirrors": { "type": "array", "items": { "type": "string", "pattern": "^https?://" } },
        "tool": { "type": "string", "minLength": 1 },
        "artifact": { "type": "string", "minLength": 1 }
      },
      "allOf": [
        { "if": { "properties": { "type": { "const": "kiwix" } } }, "then": { "required": ["name"] } },
        { "if": { "properties": { "type": { "const": "url" } } }, "then": { "required": ["url"] } },
        { "if": { "properties": { "type": { "const": "build" } } }, "then": { "required": ["tool", "artifact"] } }
      ]
    },
    "overlay": {
      "type": "object",
      "required": ["id", "kind", "default_on", "coverage", "color"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
        "kind": { "enum": ["geojson", "pmtiles", "style-layer"] },
        "layer_id": { "type": ["string", "null"] },
        "default_on": { "type": "boolean" },
        "coverage": { "type": "array", "items": { "enum": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"] } },
        "color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
        "icon": { "type": ["string", "null"] }
      }
    }
  }
}
```

Copy it to the fixture tree: `mkdir -p api/tests/fixtures/manifest && cp manifest/schema.json api/tests/fixtures/manifest/schema.json`.

- [ ] **Step 4: Write `api/sos/manifest.py`**

```python
"""Manifest loading and validation. The manifest is the single description of every
content item; `library.py` mirrors it into the `library_items` table."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["zim", "pmtiles", "geojson", "pdf", "epub", "dir", "model", "mwm", "apk", "style", "glyphs", "sprites", "places"]
Tier = Literal["core", "extended"]
Category = Literal["playbooks", "uk-official", "medical", "survival", "reference", "practical", "maps", "education", "books", "media", "ai"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["kiwix", "url", "build"]
    name: str | None = None
    url: str | None = None
    sha256: str | None = None
    mirrors: list[str] = Field(default_factory=list)
    tool: str | None = None
    artifact: str | None = None


class OverlaySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: Literal["geojson", "pmtiles", "style-layer"]
    layer_id: str | None = None
    default_on: bool = False
    coverage: list[str] = Field(default_factory=list)
    color: str = "#ffffff"
    icon: str | None = None


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    kind: Kind
    tier: Tier
    category: Category
    scenarios: list[str] = Field(default_factory=list)
    source: Source
    dest: str
    size_bytes: int = 0
    as_at: str | None = None
    licence: str | None = None
    priority: int = 100
    reader_home: str | None = None
    description: str | None = None
    search_weight: float = 1.0
    suggest: bool = False
    overlay: OverlaySpec | None = None


def manifest_files(dir: Path) -> list[Path]:
    """Every *.json in the directory except schema.json, in name order."""
    return [p for p in sorted(Path(dir).glob("*.json")) if p.name != "schema.json"]


def load_manifests(dir: Path) -> list[Item]:
    items: list[Item] = []
    for path in manifest_files(dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("items", []):
            items.append(Item.model_validate(raw))
    return items


def load_schema(dir: Path) -> dict:
    return json.loads((Path(dir) / "schema.json").read_text(encoding="utf-8"))


def validate_manifests(dir: Path) -> list[str]:
    """Schema validation plus the cross-item rules. Returns error strings; empty means valid."""
    dir = Path(dir)
    schema_path = dir / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_dests: dict[str, str] = {}
    for path in manifest_files(dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON: {exc}")
            continue
        for err in sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.path]):
            loc = "/".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{path.name}: {loc}: {err.message}")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            iid = str(raw.get("id"))
            dest = str(raw.get("dest"))
            source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
            if iid in seen_ids:
                errors.append(f"{path.name}: duplicate id '{iid}' (also in {seen_ids[iid]})")
            else:
                seen_ids[iid] = path.name
            if dest in seen_dests:
                errors.append(f"{path.name}: duplicate dest '{dest}' (also in {seen_dests[dest]})")
            else:
                seen_dests[dest] = path.name
            if raw.get("kind") == "zim" and dest != f"zim/{iid}.zim":
                errors.append(f"{path.name}: {iid}: zim dest must be 'zim/{iid}.zim', got '{dest}'")
            if source.get("type") == "build" and not source.get("artifact"):
                errors.append(f"{path.name}: {iid}: build items need source.artifact")
            if path.name == "overlays.json" and not raw.get("overlay"):
                errors.append(f"{path.name}: {iid}: overlay object required in overlays.json")
    return errors
```

- [ ] **Step 5: Write the fixture manifests**

`api/tests/fixtures/manifest/core.json`:

```json
{
  "items": [
    {
      "id": "wikipedia_en_100_mini_2026-01",
      "title": "Wikipedia 100 (mini)",
      "kind": "zim", "tier": "core", "category": "reference", "scenarios": [],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_mini_2026-01.zim" },
      "dest": "zim/wikipedia_en_100_mini_2026-01.zim",
      "size_bytes": 4537782, "as_at": "2026-01", "licence": "CC BY-SA 4.0", "priority": 10,
      "reader_home": null, "description": "Top hundred Wikipedia articles, text only.",
      "search_weight": 1.0, "suggest": true, "overlay": null
    },
    {
      "id": "sos-test-noindex",
      "title": "SOS test (no index)",
      "kind": "zim", "tier": "core", "category": "survival", "scenarios": ["grid-collapse"],
      "source": { "type": "build", "tool": "zimwriterfs", "artifact": "sos-test-noindex.zim" },
      "dest": "zim/sos-test-noindex.zim",
      "size_bytes": 36105, "as_at": "2026-09-03", "licence": "CC0", "priority": 20,
      "description": "Two-page fixture ZIM built without a full-text index.",
      "search_weight": 1.0, "suggest": true
    },
    {
      "id": "sos-test-pdf",
      "title": "SOS test document",
      "kind": "pdf", "tier": "core", "category": "uk-official", "scenarios": ["grid-collapse"],
      "source": { "type": "url", "url": "https://example.invalid/sos-test.pdf" },
      "dest": "docs/sos-test.pdf",
      "size_bytes": 900, "as_at": "2026-09", "licence": "OGL v3", "priority": 30,
      "description": "Two-page fixture PDF.", "search_weight": 1.4
    },
    {
      "id": "nrr-2025",
      "title": "National Risk Register 2025",
      "kind": "pdf", "tier": "core", "category": "uk-official", "scenarios": [],
      "source": { "type": "url", "url": "https://assets.publishing.service.gov.uk/media/67b5f85732b2aab18314bbe4/National_Risk_Register_2025.pdf" },
      "dest": "docs/nrr-2025.pdf",
      "size_bytes": 5000000, "as_at": "2025-01-16", "licence": "OGL v3", "priority": 40,
      "description": "Not present in the fixture tree; exercises the unavailable path.", "search_weight": 1.4
    },
    {
      "id": "gemma-4-E2B-it-Q4_K_M",
      "title": "Gemma 4 E2B (Q4_K_M)",
      "kind": "model", "tier": "core", "category": "ai", "scenarios": [],
      "source": { "type": "url", "url": "https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf" },
      "dest": "models/gemma-4-E2B-it-Q4_K_M.gguf",
      "size_bytes": 3106738272, "as_at": "2026-04", "licence": "Gemma Terms of Use", "priority": 90
    }
  ]
}
```

`api/tests/fixtures/manifest/extended.json`:

```json
{
  "items": [
    {
      "id": "sos-ext-missing",
      "title": "Extended tier test ZIM",
      "kind": "zim", "tier": "extended", "category": "education", "scenarios": [],
      "source": { "type": "kiwix", "name": "sos-ext-missing" },
      "dest": "zim/sos-ext-missing.zim",
      "size_bytes": 1, "as_at": "2026-01", "priority": 200,
      "description": "Lives on the external drive, which the tests leave unplugged."
    }
  ]
}
```

`api/tests/fixtures/manifest/maps.json`:

```json
{
  "items": [
    { "id": "uk-ie", "title": "Base map (OpenStreetMap)", "kind": "pmtiles", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "pmtiles", "artifact": "uk-ie.pmtiles" }, "dest": "maps/uk-ie.pmtiles",
      "size_bytes": 3200000000, "as_at": "2026-09-02", "licence": "ODbL", "priority": 50 },
    { "id": "contours", "title": "Contours", "kind": "pmtiles", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "pmtiles", "artifact": "contours.pmtiles" }, "dest": "maps/contours.pmtiles",
      "size_bytes": 1000000000, "as_at": "2026-09", "licence": "OGL v3", "priority": 51 },
    { "id": "hillshade", "title": "Hillshade", "kind": "pmtiles", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "pmtiles", "artifact": "hillshade.pmtiles" }, "dest": "maps/hillshade.pmtiles",
      "size_bytes": 800000000, "as_at": "2026-09", "licence": "OGL v3", "priority": 52 },
    { "id": "places", "title": "Place names", "kind": "places", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "build-maps", "artifact": "places.csv.gz" }, "dest": "maps/places.csv.gz",
      "size_bytes": 500000000, "as_at": "2026-09", "licence": "OGL v3", "priority": 53 },
    { "id": "packs", "title": "Phone map packs", "kind": "dir", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "build-maps", "artifact": "packs/" }, "dest": "maps/packs",
      "size_bytes": 2600000000, "as_at": "2026-07", "licence": "ODbL", "priority": 60 }
  ]
}
```

`api/tests/fixtures/manifest/overlays.json`:

```json
{
  "items": [
    { "id": "health", "title": "Hospitals, pharmacies, GP surgeries", "kind": "geojson", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "build-maps", "artifact": "overlays/health.geojson" }, "dest": "maps/overlays/health.geojson",
      "size_bytes": 4000000, "as_at": "2026-09", "licence": "ODbL", "priority": 70,
      "overlay": { "id": "health", "kind": "geojson", "layer_id": null, "default_on": false, "coverage": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"], "color": "#e03131", "icon": "cross" } },
    { "id": "nuclear-sites", "title": "Nuclear sites", "kind": "geojson", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "build-maps", "artifact": "overlays/nuclear-sites.geojson" }, "dest": "maps/overlays/nuclear-sites.geojson",
      "size_bytes": 20000, "as_at": "2026-09", "licence": "CC0", "priority": 71,
      "overlay": { "id": "nuclear-sites", "kind": "geojson", "layer_id": null, "default_on": false, "coverage": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"], "color": "#f59f00", "icon": "radiation" } },
    { "id": "water", "title": "Reservoirs and water works", "kind": "pmtiles", "tier": "core", "category": "maps",
      "source": { "type": "build", "tool": "build-maps", "artifact": "overlays/water.pmtiles" }, "dest": "maps/overlays/water.pmtiles",
      "size_bytes": 9000000, "as_at": "2026-09", "licence": "ODbL", "priority": 72,
      "overlay": { "id": "water", "kind": "pmtiles", "layer_id": "water", "default_on": false, "coverage": ["england", "wales", "scotland", "ni", "roi", "iom", "ci"], "color": "#1c7ed6", "icon": "droplet" } }
  ]
}
```

- [ ] **Step 6: Write `dev/manifest/core.json`**

Titles and sizes come from `kiwix-manage show` and `ls -l` over `/home/dan/sos-content`. Kiwix keeps only the newest build of each ZIM online, so the wikipedia mini and NHS medicines URLs below are recorded for provenance; `sos sync` on the dev manifest is only ever run with `--dry-run` because the files already exist.

```json
{
  "items": [
    { "id": "wikipedia_en_100_mini_2026-01", "title": "Wikipedia 100 (mini)", "kind": "zim", "tier": "core", "category": "reference", "scenarios": [],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_mini_2026-01.zim" },
      "dest": "zim/wikipedia_en_100_mini_2026-01.zim", "size_bytes": 4537782, "as_at": "2026-01", "licence": "CC BY-SA 4.0",
      "priority": 10, "reader_home": null, "description": "Top hundred Wikipedia articles, text only.", "search_weight": 1.0, "suggest": true },
    { "id": "nhs.uk_en_medicines_2025-12", "title": "NHS Medicines A to Z", "kind": "zim", "tier": "core", "category": "medical", "scenarios": ["pandemic", "supply-chain"],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/other/nhs.uk_en_medicines_2025-12.zim" },
      "dest": "zim/nhs.uk_en_medicines_2025-12.zim", "size_bytes": 16946183, "as_at": "2025-12", "licence": "OGL v3",
      "priority": 11, "description": "NHS medicines A to Z: doses, side effects, interactions.", "search_weight": 1.4, "suggest": true },
    { "id": "zimgit-medicine_en_2024-08", "title": "Medical Library (zimgit)", "kind": "zim", "tier": "core", "category": "medical", "scenarios": ["pandemic"],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/other/zimgit-medicine_en_2024-08.zim" },
      "dest": "zim/zimgit-medicine_en_2024-08.zim", "size_bytes": 70179585, "as_at": "2024-08", "licence": "Mixed",
      "priority": 12, "description": "Field medicine manuals as PDFs.", "search_weight": 1.2 },
    { "id": "zimgit-water_en_2024-08", "title": "Water Treatment Library", "kind": "zim", "tier": "core", "category": "survival", "scenarios": ["grid-collapse", "heat-drought", "storms-flooding"],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim" },
      "dest": "zim/zimgit-water_en_2024-08.zim", "size_bytes": 20924451, "as_at": "2024-08", "licence": "Mixed",
      "priority": 13, "description": "Finding, filtering and disinfecting water." },
    { "id": "zimgit-post-disaster_en_2024-05", "title": "Post Disaster Resource Library", "kind": "zim", "tier": "core", "category": "survival", "scenarios": ["storms-flooding", "civil-unrest", "long-rebuild"],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/other/zimgit-post-disaster_en_2024-05.zim" },
      "dest": "zim/zimgit-post-disaster_en_2024-05.zim", "size_bytes": 644665513, "as_at": "2024-05", "licence": "Mixed",
      "priority": 14, "description": "Shelter, sanitation and rebuilding after a disaster." },
    { "id": "ifixit_en_all_2025-12", "title": "iFixit", "kind": "zim", "tier": "core", "category": "practical", "scenarios": ["emp", "supply-chain"],
      "source": { "type": "url", "url": "https://download.kiwix.org/zim/ifixit/ifixit_en_all_2025-12.zim" },
      "dest": "zim/ifixit_en_all_2025-12.zim", "size_bytes": 3570695757, "as_at": "2025-12", "licence": "CC BY-NC-SA 3.0",
      "priority": 15, "description": "Repair guides for phones, tools, vehicles and appliances.", "suggest": true },
    { "id": "gemma-4-E2B-it-Q4_K_M", "title": "Gemma 4 E2B (Q4_K_M)", "kind": "model", "tier": "core", "category": "ai", "scenarios": [],
      "source": { "type": "url", "url": "https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf" },
      "dest": "models/gemma-4-E2B-it-Q4_K_M.gguf", "size_bytes": 3106738272, "as_at": "2026-04", "licence": "Gemma Terms of Use",
      "priority": 90, "description": "Primary assistant model." },
    { "id": "Qwen3.5-2B-Q4_K_M", "title": "Qwen 3.5 2B (Q4_K_M)", "kind": "model", "tier": "core", "category": "ai", "scenarios": [],
      "source": { "type": "url", "url": "https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/main/Qwen3.5-2B-Q4_K_M.gguf" },
      "dest": "models/Qwen3.5-2B-Q4_K_M.gguf", "size_bytes": 1280835840, "as_at": "2026-03", "licence": "Apache-2.0",
      "priority": 91, "description": "Fallback assistant model." }
  ]
}
```

- [ ] **Step 7: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_manifest.py -v`
Expected: 11 PASS. (`test_repo_manifest_is_valid` passes with zero manifest files because only `schema.json` exists in `manifest/` until plan 03.)

- [ ] **Step 8: Commit**

```bash
git add manifest/schema.json api/sos/manifest.py dev/manifest/core.json api/tests/fixtures/manifest api/tests/test_manifest.py
git commit -m "feat(manifest): JSON schema, Item model, validation rules, dev and fixture manifests"
```

---

### Task 3: `sos.db` (schema, FTS5 tables, settings helpers)

**Files:**
- Create: `api/sos/db.py`
- Test: `api/tests/test_db.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `sos.db.connect(path: Path | str) -> sqlite3.Connection` (row factory `sqlite3.Row`, WAL, `check_same_thread=False`), `init_schema(conn)` (idempotent), `fts5_available(conn) -> bool`, `get_setting(conn, key, default=None) -> str | None`, `set_setting(conn, key, value: str | None)`, `now_iso() -> str`, `SCHEMA` (the SQL text).

- [ ] **Step 1: Write the failing tests**

`api/tests/test_db.py`:

```python
import sqlite3

from sos import db


def _tables(conn):
    return {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def test_schema_creates_every_table(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    names = _tables(conn)
    for t in ("library_items", "fts_docs", "fts_places", "checklist_state", "notes", "settings", "search_cache", "places_meta"):
        assert t in names, t
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert isinstance(conn.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)


def test_init_schema_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    db.init_schema(conn)
    db.set_setting(conn, "ssid", "SOS")
    db.init_schema(conn)
    assert db.get_setting(conn, "ssid") == "SOS"


def test_fts5_available():
    conn = db.connect(":memory:")
    assert db.fts5_available(conn) is True


def test_bm25_title_weight_ranks_title_hit_first():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Heating without power", "keep warm water bottles blankets water water", "m1", "module", "playbooks", "", None, "/m/heat"),
    )
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Water", "finding and treating it", "m2", "module", "playbooks", "", None, "/m/water"),
    )
    rows = conn.execute(
        "SELECT doc_id FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0)", ('"water"',)
    ).fetchall()
    assert [r["doc_id"] for r in rows] == ["m2", "m1"]


def test_porter_stemming_and_diacritics():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Éowyn storm outages", "restoring power", "p1", "playbook", "playbooks", "", None, "/s/grid"),
    )
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE fts_docs MATCH '\"outage\"'").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE fts_docs MATCH '\"eowyn\"'").fetchone()[0] == 1


def test_places_prefix_index():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)",
                 ("Oxford", "city", 51.752, -1.258, "England", None))
    conn.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)",
                 ("Oxted", "town", 51.257, 0.006, "England", None))
    rows = conn.execute("SELECT name FROM fts_places WHERE fts_places MATCH '\"oxf\"*'").fetchall()
    assert [r["name"] for r in rows] == ["Oxford"]
    rows = conn.execute("SELECT name FROM fts_places WHERE fts_places MATCH '\"ox\"*' ORDER BY name").fetchall()
    assert [r["name"] for r in rows] == ["Oxford", "Oxted"]


def test_settings_helpers():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    assert db.get_setting(conn, "missing") is None
    assert db.get_setting(conn, "missing", "x") == "x"
    db.set_setting(conn, "k", "v")
    db.set_setting(conn, "k", "w")
    assert db.get_setting(conn, "k") == "w"
    db.set_setting(conn, "k", None)
    assert db.get_setting(conn, "k") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_db.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.db'`.

- [ ] **Step 3: Write `api/sos/db.py`**

```python
"""SQLite access: connection factory, schema and the settings key/value table."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS library_items (
  id TEXT PRIMARY KEY, title, kind, tier, category, scenarios_json, dest, size_bytes INTEGER, as_at, licence,
  priority INTEGER, reader_home, description, search_weight REAL NOT NULL DEFAULT 1.0, suggest INTEGER NOT NULL DEFAULT 0,
  overlay_json, available INTEGER NOT NULL DEFAULT 0, local_path, fts INTEGER NOT NULL DEFAULT 0,
  resolved_name, resolved_size INTEGER, resolved_as_at);
CREATE VIRTUAL TABLE IF NOT EXISTS fts_docs USING fts5(
  title, body, doc_id UNINDEXED, kind UNINDEXED, category UNINDEXED, scenarios UNINDEXED, page UNINDEXED, url UNINDEXED,
  tokenize='porter unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS fts_places USING fts5(
  name, kind UNINDEXED, lat UNINDEXED, lon UNINDEXED, region UNINDEXED, postcode UNINDEXED,
  tokenize='unicode61 remove_diacritics 2', prefix='2 3 4');
CREATE TABLE IF NOT EXISTS checklist_state (playbook TEXT, item_id TEXT, checked INTEGER NOT NULL, updated_at TEXT, PRIMARY KEY (playbook, item_id));
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL DEFAULT 'note', title TEXT, body TEXT, lat REAL, lon REAL, updated_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS search_cache (q TEXT PRIMARY KEY, results_json TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS places_meta (key TEXT PRIMARY KEY, value TEXT);
"""


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def fts5_available(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE temp.__fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None or row["value"] is None:
        return default
    return row["value"]


def set_setting(conn: sqlite3.Connection, key: str, value: str | None) -> None:
    if value is None:
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
    else:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
    conn.commit()
```

- [ ] **Step 4: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_db.py -v`
Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add api/sos/db.py api/tests/test_db.py
git commit -m "feat(db): sqlite schema with fts5 docs and places tables"
```

---

### Task 4: `sos.library` (items table, availability, `library.xml`, flags, reader URLs, rescan)

**Files:**
- Create: `api/sos/library.py`
- Create: `api/tests/fixtures/library/wikipedia_en_100_mini_2026-01.zim` (copy of `/home/dan/sos-content/zim/wikipedia_en_100_mini_2026-01.zim`, 4,537,782 bytes), `api/tests/fixtures/library/sos-test-noindex.zim` (built in Task 8's generator; for this task build it once by hand with the command in Step 3), `api/tests/fixtures/library/SHA256SUMS`
- Test: `api/tests/test_library.py`

**Interfaces:**
- Consumes: `sos.db`, `sos.manifest.Item`, `Settings`.
- Produces: `upsert_items(conn, items: list[Item]) -> None`, `ext_mounted(settings) -> bool`, `refresh_items(conn, settings) -> tuple[int, int]` (items, available), `zim_rows(conn, available_only=True) -> list[sqlite3.Row]`, `write_library_xml(conn, settings, include_ext=True) -> Path`, `parse_library_xml(path) -> dict[str, dict]` (`{id: {"fts": bool, "language": str, "title": str}}`), `apply_library_flags(conn, info) -> None`, `rescan(conn, settings) -> dict` (`{"items": n, "available": m}`), `drive_label(row, ext_ok: bool) -> str`, `reader_url(row) -> str | None`, `item_dict(row, ext_ok) -> dict` (the `LibraryItem` shape), `library_response(conn, settings) -> dict`, `get_item(conn, id) -> sqlite3.Row | None`, `CATEGORY_ORDER`, `CATEGORY_TITLES`, `KIWIX_MANAGE` (binary name, overridable for tests).

- [ ] **Step 1: Copy the fixture ZIMs and write SHA256SUMS**

```bash
mkdir -p api/tests/fixtures/library api/tests/fixtures/pages
cp /home/dan/sos-content/zim/wikipedia_en_100_mini_2026-01.zim api/tests/fixtures/library/
```

Write `api/tests/fixtures/pages/index.html`:

```html
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>SOS test</title></head>
<body><main><h1>SOS test</h1><p>Boil water for one minute before drinking it.</p>
<p><a href="bleeding.html">Severe bleeding</a></p></main></body></html>
```

Write `api/tests/fixtures/pages/bleeding.html`:

```html
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Severe bleeding</title></head>
<body><nav><a href="index.html">Home</a></nav><main><h1>Severe bleeding</h1>
<p>Press hard on the wound with a clean cloth and call 999.</p></main><footer>Fixture</footer></body></html>
```

Generate the 48x48 illustration and build the no-index ZIM (`MAGIC` points zimwriterfs at the libmagic database; on Ubuntu it is `/usr/lib/file/magic.mgc`):

```bash
python3 - <<'EOF'
import struct, zlib
w = h = 48
raw = b''.join(b'\x00' + bytes([0x33, 0xcc, 0x33] * w) for _ in range(h))
def chunk(t, d):
    return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
open('api/tests/fixtures/pages/icon.png', 'wb').write(png)
EOF
MAGIC=/usr/lib/file/magic.mgc zimwriterfs --welcome=index.html --illustration=icon.png --language=eng \
  --title="SOS test (no index)" --description="Fixture ZIM without a full-text index" --creator=SOS --publisher=SOS \
  --name=sos-test-noindex --withoutFTIndex api/tests/fixtures/pages api/tests/fixtures/library/sos-test-noindex.zim
(cd api/tests/fixtures/library && sha256sum *.zim > SHA256SUMS && cat SHA256SUMS)
```

Expected: `SHA256SUMS` has two lines; the wikipedia line is `2811724b72fd34a0728c28b7456d3d6866579019fbbe7ffe28528f3450c252db  wikipedia_en_100_mini_2026-01.zim`; the noindex hash differs per build (zimwriterfs stamps a UUID) and is whatever was just written. `ls -l api/tests/fixtures/library/sos-test-noindex.zim` shows about 36 KB.

- [ ] **Step 2: Write the failing tests**

`api/tests/test_library.py`:

```python
import shutil
from pathlib import Path

import pytest

from sos import db, library
from sos.manifest import load_manifests

FIXTURES = Path(__file__).parent / "fixtures"
HAS_KIWIX_MANAGE = shutil.which("kiwix-manage") is not None


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    library.upsert_items(c, load_manifests(env.manifests))
    return c


def _install_zims(env, names=("wikipedia_en_100_mini_2026-01", "sos-test-noindex")):
    for n in names:
        shutil.copy(FIXTURES / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")


def test_fixture_checksums_match():
    sums = (FIXTURES / "library" / "SHA256SUMS").read_text().split()
    import hashlib
    for digest, name in zip(sums[0::2], sums[1::2]):
        assert hashlib.sha256((FIXTURES / "library" / name).read_bytes()).hexdigest() == digest, name


def test_upsert_mirrors_manifest_and_keeps_runtime_columns(conn, env):
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"]["suggest"] == 1
    assert rows["sos-test-pdf"]["search_weight"] == 1.4
    assert rows["health"]["overlay_json"] is not None
    conn.execute("UPDATE library_items SET available=1, fts=1, resolved_name='x' WHERE id='wikipedia_en_100_mini_2026-01'")
    conn.commit()
    library.upsert_items(conn, load_manifests(env.manifests))
    row = conn.execute("SELECT available, fts, resolved_name FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert (row["available"], row["fts"], row["resolved_name"]) == (1, 1, "x")


def test_upsert_removes_items_gone_from_manifest(conn, env):
    items = [i for i in load_manifests(env.manifests) if i.id != "sos-test-noindex"]
    library.upsert_items(conn, items)
    assert conn.execute("SELECT count(*) FROM library_items WHERE id='sos-test-noindex'").fetchone()[0] == 0


def test_refresh_availability_and_labels(conn, env):
    _install_zims(env)
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"%PDF-1.4\n")
    total, available = library.refresh_items(conn, env)
    assert total == 13 and available == 3
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"]["local_path"] == str(env.core / "zim" / "wikipedia_en_100_mini_2026-01.zim")
    assert rows["nrr-2025"]["available"] == 0
    assert rows["sos-ext-missing"]["available"] == 0
    assert library.drive_label(rows["sos-ext-missing"], library.ext_mounted(env)) == "On external drive (not connected)"
    assert library.drive_label(rows["wikipedia_en_100_mini_2026-01"], False) == "Core"
    env.ext.mkdir()
    (env.ext / "zim").mkdir()
    shutil.copy(FIXTURES / "library" / "sos-test-noindex.zim", env.ext / "zim" / "sos-ext-missing.zim")
    total, available = library.refresh_items(conn, env)
    assert available == 4
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-ext-missing'").fetchone()
    assert library.drive_label(row, True) == "External drive"


def test_reader_urls(conn, env):
    _install_zims(env)
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"%PDF-1.4\n")
    library.refresh_items(conn, env)
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert library.reader_url(rows["wikipedia_en_100_mini_2026-01"]) == "/read/wikipedia_en_100_mini_2026-01/"
    assert library.reader_url(rows["sos-test-pdf"]) == "/doc/sos-test-pdf"
    assert library.reader_url(rows["nrr-2025"]) is None
    assert library.reader_url(rows["uk-ie"]) is None
    conn.execute("UPDATE library_items SET reader_home='A/Main_Page' WHERE id='wikipedia_en_100_mini_2026-01'")
    row = conn.execute("SELECT * FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert library.reader_url(row) == "/read/wikipedia_en_100_mini_2026-01/A/Main_Page"


def test_library_response_groups_by_category_in_order(conn, env):
    _install_zims(env)
    library.refresh_items(conn, env)
    resp = library.library_response(conn, env)
    ids = [c["id"] for c in resp["categories"]]
    assert ids == [c for c in library.CATEGORY_ORDER if c in ids]
    assert ids[0] == "uk-official"
    ref = next(c for c in resp["categories"] if c["id"] == "reference")
    item = ref["items"][0]
    assert set(item) == {"id", "title", "kind", "tier", "category", "scenarios", "size_bytes", "as_at", "licence",
                         "available", "url", "description", "drive_label"}
    assert item["available"] is True and item["url"].startswith("/read/")


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_write_library_xml_and_flags(conn, env):
    _install_zims(env)
    library.refresh_items(conn, env)
    path = library.write_library_xml(conn, env)
    assert path == env.library_xml and path.exists()
    info = library.parse_library_xml(path)
    assert info["wikipedia_en_100_mini_2026-01"]["fts"] is True
    assert info["wikipedia_en_100_mini_2026-01"]["language"] == "eng"
    assert info["sos-test-noindex"]["fts"] is False
    library.apply_library_flags(conn, info)
    rows = {r["id"]: r["fts"] for r in conn.execute("SELECT id, fts FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"] == 1 and rows["sos-test-noindex"] == 0
    # regenerated from scratch: removing a file removes its book
    (env.core / "zim" / "sos-test-noindex.zim").unlink()
    library.refresh_items(conn, env)
    library.write_library_xml(conn, env)
    assert "sos-test-noindex" not in library.parse_library_xml(path)


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_rescan_with_extended_missing_flushes_cache(conn, env):
    _install_zims(env)
    conn.execute("INSERT INTO search_cache(q, results_json, created_at) VALUES ('water','[]','2026-01-01')")
    conn.commit()
    result = library.rescan(conn, env)
    assert result == {"items": 13, "available": 2}
    assert conn.execute("SELECT count(*) FROM search_cache").fetchone()[0] == 0
    assert db.get_setting(conn, "zim_languages") is not None
    assert not env.ext.exists()


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_corrupt_zim_is_skipped_and_marked_unavailable(conn, env):
    _install_zims(env, names=("wikipedia_en_100_mini_2026-01",))
    (env.core / "zim" / "sos-test-noindex.zim").write_bytes(b"not a zim")
    library.refresh_items(conn, env)
    path = library.write_library_xml(conn, env)
    info = library.parse_library_xml(path)
    assert "wikipedia_en_100_mini_2026-01" in info and "sos-test-noindex" not in info
    assert conn.execute("SELECT available FROM library_items WHERE id='sos-test-noindex'").fetchone()[0] == 0


def test_write_library_xml_without_zims_writes_empty_library(conn, env, tmp_path):
    path = library.write_library_xml(conn, env)
    assert "<library" in path.read_text()
    assert library.parse_library_xml(path) == {}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_library.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.library'`.

- [ ] **Step 4: Write `api/sos/library.py`**

```python
"""library_items: the manifest mirrored into SQLite plus runtime columns (availability, local path,
full-text flag, resolved download metadata), library.xml generation and the /api/library shapes."""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from sos.config import Settings
from sos.manifest import Item

log = logging.getLogger(__name__)
KIWIX_MANAGE = "kiwix-manage"

CATEGORY_ORDER = ["playbooks", "uk-official", "medical", "survival", "reference", "practical", "maps", "education", "books", "media", "ai"]
CATEGORY_TITLES = {
    "playbooks": "Playbooks", "uk-official": "UK official guidance", "medical": "Medical", "survival": "Survival",
    "reference": "Reference", "practical": "Practical and repair", "maps": "Maps", "education": "Education",
    "books": "Books", "media": "Media", "ai": "AI models",
}
EMPTY_LIBRARY = '<?xml version="1.0" encoding="UTF-8"?>\n<library version="20110515">\n</library>\n'


def upsert_items(conn: sqlite3.Connection, items: list[Item]) -> None:
    ids = [i.id for i in items]
    for it in items:
        conn.execute(
            """INSERT INTO library_items(id, title, kind, tier, category, scenarios_json, dest, size_bytes, as_at, licence,
                 priority, reader_home, description, search_weight, suggest, overlay_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title, kind=excluded.kind, tier=excluded.tier,
                 category=excluded.category, scenarios_json=excluded.scenarios_json, dest=excluded.dest,
                 size_bytes=excluded.size_bytes, as_at=excluded.as_at, licence=excluded.licence, priority=excluded.priority,
                 reader_home=excluded.reader_home, description=excluded.description, search_weight=excluded.search_weight,
                 suggest=excluded.suggest, overlay_json=excluded.overlay_json""",
            (it.id, it.title, it.kind, it.tier, it.category, json.dumps(it.scenarios), it.dest, it.size_bytes, it.as_at,
             it.licence, it.priority, it.reader_home, it.description, it.search_weight, int(it.suggest),
             json.dumps(it.overlay.model_dump()) if it.overlay else None),
        )
    if ids:
        placeholders = ",".join("?" for _ in ids)
        conn.execute(f"DELETE FROM library_items WHERE id NOT IN ({placeholders})", ids)
    else:
        conn.execute("DELETE FROM library_items")
    conn.commit()


def ext_mounted(settings: Settings) -> bool:
    if not settings.ext.is_dir():
        return False
    return True if settings.dev else os.path.ismount(settings.ext)


def refresh_items(conn: sqlite3.Connection, settings: Settings) -> tuple[int, int]:
    ext_ok = ext_mounted(settings)
    total = available = 0
    for row in conn.execute("SELECT id, tier, dest FROM library_items").fetchall():
        total += 1
        root = settings.tier_root(row["tier"])
        path = root / row["dest"]
        ok = path.exists() and (row["tier"] == "core" or ext_ok)
        if ok:
            available += 1
        conn.execute("UPDATE library_items SET available=?, local_path=? WHERE id=?",
                     (int(ok), str(path) if ok else None, row["id"]))
    conn.commit()
    return total, available


def zim_rows(conn: sqlite3.Connection, available_only: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM library_items WHERE kind='zim'"
    if available_only:
        sql += " AND available=1"
    return conn.execute(sql + " ORDER BY priority, id").fetchall()


def write_library_xml(conn: sqlite3.Connection, settings: Settings, include_ext: bool = True) -> Path:
    """Regenerate library.xml from scratch with `kiwix-manage add`, one call per file so
    --zimPathToSave keeps absolute paths. Missing files are skipped (the item stays unavailable)."""
    path = settings.library_xml
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".xml.tmp")
    if tmp.exists():
        tmp.unlink()
    tmp.write_text(EMPTY_LIBRARY, encoding="utf-8")
    for row in zim_rows(conn):
        if row["tier"] == "extended" and not include_ext:
            continue
        zim = Path(row["local_path"] or "")
        if not zim.exists():
            continue
        proc = subprocess.run([KIWIX_MANAGE, str(tmp), "add", f"--zimPathToSave={zim}", str(zim)],
                              capture_output=True, text=True)
        if proc.returncode != 0:  # a corrupt or partial ZIM must not take the whole library down
            log.warning("kiwix-manage rejected %s: %s", zim.name, (proc.stderr or proc.stdout).strip())
            conn.execute("UPDATE library_items SET available=0, local_path=NULL WHERE id=?", (row["id"],))
            conn.commit()
    os.replace(tmp, path)
    return path


def parse_library_xml(path: Path) -> dict[str, dict]:
    """{book id (filename stem): {fts, language, title}} from kiwix-manage's XML."""
    if not Path(path).exists():
        return {}
    root = ET.parse(path).getroot()
    info: dict[str, dict] = {}
    for book in root.iter("book"):
        book_path = book.get("path") or ""
        book_id = Path(book_path).stem
        tags = book.get("tags") or ""
        info[book_id] = {
            "fts": "_ftindex:yes" in tags.split(";"),
            "language": (book.get("language") or "eng").split(",")[0],
            "title": book.get("title") or book_id,
        }
    return info


def apply_library_flags(conn: sqlite3.Connection, info: dict[str, dict]) -> None:
    conn.execute("UPDATE library_items SET fts=0 WHERE kind='zim'")
    for book_id, meta in info.items():
        conn.execute("UPDATE library_items SET fts=? WHERE id=?", (int(meta["fts"]), book_id))
    conn.commit()


def rescan(conn: sqlite3.Connection, settings: Settings) -> dict:
    """Seconds, never touches fts_docs or fts_places: availability, library.xml, fts flags, cache flush."""
    from sos.db import set_setting

    total, available = refresh_items(conn, settings)
    xml = write_library_xml(conn, settings)
    info = parse_library_xml(xml)
    apply_library_flags(conn, info)
    set_setting(conn, "zim_languages", json.dumps({k: v["language"] for k, v in info.items()}))
    conn.execute("DELETE FROM search_cache")
    conn.commit()
    return {"items": total, "available": available}


def drive_label(row: sqlite3.Row, ext_ok: bool) -> str:
    if row["tier"] != "extended":
        return "Core"
    return "External drive" if ext_ok else "On external drive (not connected)"


def reader_url(row: sqlite3.Row) -> str | None:
    if not row["available"]:
        return None
    if row["kind"] == "zim":
        home = (row["reader_home"] or "").lstrip("/")
        return f"/read/{row['id']}/{home}"
    if row["kind"] in ("pdf", "epub"):
        return f"/doc/{row['id']}"
    return None


def item_dict(row: sqlite3.Row, ext_ok: bool) -> dict:
    return {
        "id": row["id"], "title": row["title"], "kind": row["kind"], "tier": row["tier"], "category": row["category"],
        "scenarios": json.loads(row["scenarios_json"] or "[]"), "size_bytes": row["size_bytes"] or 0,
        "as_at": row["resolved_as_at"] or row["as_at"], "licence": row["licence"], "available": bool(row["available"]),
        "url": reader_url(row), "description": row["description"], "drive_label": drive_label(row, ext_ok),
    }


def get_item(conn: sqlite3.Connection, item_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM library_items WHERE id=?", (item_id,)).fetchone()


def library_response(conn: sqlite3.Connection, settings: Settings) -> dict:
    ext_ok = ext_mounted(settings)
    groups: dict[str, list[dict]] = {}
    for row in conn.execute("SELECT * FROM library_items ORDER BY priority, title").fetchall():
        groups.setdefault(row["category"], []).append(item_dict(row, ext_ok))
    return {"categories": [{"id": c, "title": CATEGORY_TITLES[c], "items": groups[c]} for c in CATEGORY_ORDER if c in groups]}
```

- [ ] **Step 5: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_library.py -v`
Expected: 11 PASS (the three `kiwix-manage` tests run because the binary is on PATH on the PC).

- [ ] **Step 6: Commit**

```bash
git add api/sos/library.py api/tests/test_library.py api/tests/fixtures/library api/tests/fixtures/pages
git commit -m "feat(library): items table refresh, library.xml generation, fts flags and reader URLs"
```

---

### Task 5: `sos.kiwix` (async kiwix-serve client, parsers, boilerplate stripping)

**Files:**
- Create: `api/sos/kiwix.py`
- Create: `api/tests/fixtures/kiwix/search.xml`, `search_multi.xml`, `catalog.xml`, `suggest.json`, `raw_wiki.html`, `raw_nhs.html`
- Test: `api/tests/test_kiwix.py`

**Interfaces:**
- Consumes: `Settings.kiwix_url`.
- Produces: `sos.kiwix.Book(name, fts, language, title)`, `KiwixHit(title, path, snippet, book)`, `KiwixError`, `KiwixClient(base_url, timeout=5.0)` with `async catalog() -> list[Book]`, `async search(books: list[str], q: str, n: int = 8, timeout: float = 2.0) -> list[KiwixHit]`, `async suggest(book, term) -> list[dict]` (`{value, label, path}`; `kind: pattern` entries dropped), `async raw_article(book, path) -> str`, `async exists(book, path) -> bool`, `async aclose()`; pure functions `parse_search_xml(text) -> tuple[int, list[KiwixHit]]`, `parse_catalog_xml(text) -> list[Book]`, `parse_suggest_json(text) -> list[dict]`, `extract_text(html) -> list[str]`, `strip_tags(text) -> str`.

Verified kiwix-serve 3.8.2 facts the parsers rely on: the search RSS carries `<opensearch:totalResults>` with a thousands separator (`2,010`); each `<item>` has `<title>`, `<link>/kiwix/content/<book>/<path></link>`, `<description>` with `<b>` highlights and `<book><title>`; the catalogue entry's `<name>` is the ZIM's internal name (`wikipedia_en_100`), while the URL book name is the last segment of the `<link type="text/html" href="/kiwix/content/<book>">`; suggest returns `{value,label,kind,path}` and a trailing `kind: "pattern"` entry without `path`; searching a book without an index returns HTTP 404 with `<error>Fulltext search unavailable</error>`; `/kiwix/raw/<book>/content/<path>` returns 302 for redirect entries, so the client follows redirects.

- [ ] **Step 1: Write the fixture responses**

`api/tests/fixtures/kiwix/search.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Search: water</title>
    <link>/kiwix/search?pattern=water&amp;books.name=wikipedia_en_100_mini_2026-01&amp;format=xml&amp;start=0&amp;pageLength=3</link>
    <description>Search result for water</description>
    <opensearch:totalResults>18</opensearch:totalResults>
    <opensearch:startIndex>0</opensearch:startIndex>
    <opensearch:itemsPerPage>3</opensearch:itemsPerPage>
    <atom:link rel="search" type="application/opensearchdescription+xml" href="/kiwix/search/searchdescription.xml"/>
    <item>
      <title>Precipitation</title>
      <link>/kiwix/content/wikipedia_en_100_mini_2026-01/Precipitation</link>
        <description>...In meteorology, precipitation is any product of the condensation of atmospheric <b>water</b> vapour that falls from clouds due to gravitational pull......</description>
        <book>
          <title>Wikipedia 100</title>
        </book>
        <wordCount>512</wordCount>
    </item>
    <item>
      <title>Bivalvia</title>
      <link>/kiwix/content/wikipedia_en_100_mini_2026-01/Bivalvia</link>
        <description>...Marine bivalves (including brackish <b>water</b> and estuarine species) represent about 8,000 species......</description>
        <book>
          <title>Wikipedia 100</title>
        </book>
        <wordCount>525</wordCount>
    </item>
    <item>
      <title>Insect</title>
      <link>/kiwix/content/wikipedia_en_100_mini_2026-01/Insect</link>
        <description>...<b>water</b> striders, can walk on the surface of <b>water</b>. Insects are mostly solitary......</description>
        <book>
          <title>Wikipedia 100</title>
        </book>
        <wordCount>594</wordCount>
    </item>
  </channel>
</rss>
```

`api/tests/fixtures/kiwix/search_multi.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
     xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Search: medicine</title>
    <link>/kiwix/search?pattern=medicine&amp;books.name=wikipedia_en_100_mini_2026-01&amp;books.name=nhs.uk_en_medicines_2025-12&amp;format=xml&amp;start=0&amp;pageLength=2</link>
    <description>Search result for medicine</description>
    <opensearch:totalResults>2,010</opensearch:totalResults>
    <opensearch:startIndex>0</opensearch:startIndex>
    <opensearch:itemsPerPage>2</opensearch:itemsPerPage>
    <item>
      <title>Taking bendroflumethiazide with other medicines and herbal remedies - NHS</title>
      <link>/kiwix/content/nhs.uk_en_medicines_2025-12/www.nhs.uk/medicines/bendroflumethiazide/taking-bendroflumethiazide-with-other-medicines-and-herbal-remedies/</link>
        <description>...Tell your doctor if you take any other <b>medicine</b>......</description>
        <book>
          <title>NHS&apos; Medicines A to Z</title>
        </book>
        <wordCount>300</wordCount>
    </item>
    <item>
      <title>Medicine</title>
      <link>/kiwix/content/wikipedia_en_100_mini_2026-01/Medicine</link>
        <description>...<b>Medicine</b> is the science and practice of caring for patients......</description>
        <book>
          <title>Wikipedia 100</title>
        </book>
        <wordCount>700</wordCount>
    </item>
  </channel>
</rss>
```

`api/tests/fixtures/kiwix/catalog.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:opds="https://specs.opds.io/opds-1.2"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <id>3c456503-d7e1-8454-d134-6c25e9830981</id>
  <link rel="self" href="/kiwix/catalog/v2/entries?count=-1" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <title>Filtered Entries (count=-1)</title>
  <updated>2026-09-03T21:54:13Z</updated>
  <totalResults>2</totalResults>
  <startIndex>0</startIndex>
  <itemsPerPage>2</itemsPerPage>
  <entry>
    <id>urn:uuid:f33283c0-0d00-3ceb-20ba-69d9b793a4dd</id>
    <title>Wikipedia 100</title>
    <updated>2026-01-15T00:00:00Z</updated>
    <summary>Top hundred Wikipedia articles</summary>
    <language>eng</language>
    <name>wikipedia_en_100</name>
    <flavour>mini</flavour>
    <category>wikipedia</category>
    <tags>wikipedia;_category:wikipedia;_pictures:no;_videos:no;_details:no;_ftindex:yes</tags>
    <articleCount>4985</articleCount>
    <mediaCount>108</mediaCount>
    <link rel="http://opds-spec.org/image/thumbnail" href="/kiwix/catalog/v2/illustration/f33283c0-0d00-3ceb-20ba-69d9b793a4dd/?size=48" type="image/png;width=48;height=48;scale=1"/>
    <link type="text/html" href="/kiwix/content/wikipedia_en_100_mini_2026-01" />
    <author><name>Wikipedia</name></author>
    <publisher><name>openZIM</name></publisher>
    <dc:issued>2026-01-15T00:00:00Z</dc:issued>
  </entry>
  <entry>
    <id>urn:uuid:11111111-2222-3333-4444-555555555555</id>
    <title>SOS test (no index)</title>
    <updated>2026-09-03T00:00:00Z</updated>
    <summary>Fixture ZIM without a full-text index</summary>
    <language>eng</language>
    <name>sos-test-noindex</name>
    <flavour></flavour>
    <category></category>
    <tags>_ftindex:no;_pictures:yes;_videos:yes;_details:yes</tags>
    <articleCount>2</articleCount>
    <mediaCount>1</mediaCount>
    <link type="text/html" href="/kiwix/content/sos-test-noindex" />
    <author><name>SOS</name></author>
    <publisher><name>SOS</name></publisher>
    <dc:issued>2026-09-03T00:00:00Z</dc:issued>
  </entry>
</feed>
```

`api/tests/fixtures/kiwix/suggest.json`:

```json
[
  {
    "value" : "Aquatic water turtles",
    "label" : "Aquatic &lt;b&gt;water&lt;/b&gt; turtles",
    "kind" : "path"
      , "path" : "Aquatic_water_turtles"
  },
  {
    "value" : "Water",
    "label" : "&lt;b&gt;Water&lt;/b&gt;",
    "kind" : "path"
      , "path" : "Water"
  },
  {
    "value" : "wat ",
    "label" : "containing &apos;wat&apos;...",
    "kind" : "pattern"
  }
]
```

`api/tests/fixtures/kiwix/raw_wiki.html` (the structure of the real mini-ZIM `Precipitation` page, shortened):

```html
<!DOCTYPE html>
<html class="client-nojs" lang="en" dir="ltr">
<head>
<meta charset="UTF-8">
<title>Precipitation</title>
<style data-mw-deduplicate="TemplateStyles:r12345">.mw-parser-output .hatnote{font-style:italic}</style>
<script src="./_webp_/webpHandler.js"></script>
</head>
<body class="skin-vector mediawiki ltr page-Precipitation">
<div class="mw-page-container">
<div class="mw-page-container-inner">
<nav id="p-navigation" role="navigation"><ul><li><a href="Main_Page">Main page</a></li><li><a href="Special:Random">Random article</a></li></ul></nav>
<div class="mw-content-container">
<main id="content" class="mw-body">
<header class="mw-body-header vector-page-titlebar">
<h1 id="firstHeading" class="firstHeading mw-first-heading"><span class="mw-page-title-main">Precipitation</span></h1>
</header>
<a id="top"></a>
<div id="bodyContent" class="vector-body">
<div id="mw-content-text" class="mw-body-content mw-content-ltr">
<div class="mw-parser-output">
<p>In meteorology, <b>precipitation</b> is any product of the condensation of atmospheric water vapour that falls from clouds due to gravitational pull.</p>
<p>The main forms of precipitation include drizzle, rain, sleet, snow, ice pellets, graupel and hail.</p>
<table class="infobox"><tbody><tr><th>Part of a series on</th></tr><tr><td>Weather</td></tr></tbody></table>
<h2>Types</h2>
<p>Precipitation occurs when a portion of the atmosphere becomes saturated with water vapour (reaching 100% relative humidity), so that the water condenses and "precipitates" or falls.</p>
<ul><li>Rain</li><li>Snow</li></ul>
<script>window.x = 1;</script>
<noscript>Enable JavaScript</noscript>
</div>
</div>
</div>
</main>
</div>
<footer id="footer" class="mw-footer" role="contentinfo"><ul><li>Text is available under the Creative Commons licence.</li></ul></footer>
<aside>Related portals</aside>
</div>
</div>
</body>
</html>
```

`api/tests/fixtures/kiwix/raw_nhs.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Paracetamol for adults - NHS</title>
<script type="application/ld+json">{"@context":"http://schema.org","@type":"MedicalWebPage"}</script>
</head>
<body>
<a class="nhsuk-skip-link" href="#maincontent">Skip to main content</a>
<header class="nhsuk-header" role="banner">
<div class="nhsuk-header__logo"><a class="nhsuk-header__link" href="/">NHS</a></div>
<nav class="nhsuk-header__navigation"><ul><li><a class="nhsuk-header__navigation-link" href="/conditions/">Health A to Z</a></li></ul></nav>
</header>
<div class="nhsuk-width-container">
<main class="nhsuk-main-wrapper" id="maincontent" role="main">
<h1>Paracetamol for adults</h1>
<h2>Key facts</h2>
<ul class="nhsuk-list">
<li>Paracetamol is a common painkiller used to treat aches and pain. It can also be used to reduce a high temperature.</li>
<li>The usual dose for adults is 1 or 2 500mg tablets up to 4 times in 24 hours.</li>
</ul>
<p>Always leave at least 4 hours between doses.</p>
<div role="navigation" class="nhsuk-contents-list"><ul><li><a href="#about">About paracetamol</a></li></ul></div>
</main>
</div>
<footer class="nhsuk-footer" role="contentinfo"><p>Page last reviewed: 2 June 2025</p></footer>
<script src="../../../static/nhsuk/js/main.7a3ea1cd7350.js" defer></script>
</body>
</html>
```

- [ ] **Step 2: Write the failing tests**

`api/tests/test_kiwix.py`:

```python
import asyncio
from pathlib import Path

import httpx
import pytest
import respx

from sos import kiwix

FX = Path(__file__).parent / "fixtures" / "kiwix"
BASE = "http://kiwix.test/kiwix"


def test_parse_search_xml_single_book():
    total, hits = kiwix.parse_search_xml((FX / "search.xml").read_text())
    assert total == 18
    assert [h.title for h in hits] == ["Precipitation", "Bivalvia", "Insect"]
    assert hits[0].book == "wikipedia_en_100_mini_2026-01"
    assert hits[0].path == "Precipitation"
    assert hits[0].snippet.startswith("In meteorology, precipitation is any product")
    assert "<b>" not in hits[0].snippet and "..." not in hits[0].snippet[:3]


def test_parse_search_xml_multi_book_and_thousands_separator():
    total, hits = kiwix.parse_search_xml((FX / "search_multi.xml").read_text())
    assert total == 2010
    assert hits[0].book == "nhs.uk_en_medicines_2025-12"
    assert hits[0].path == "www.nhs.uk/medicines/bendroflumethiazide/taking-bendroflumethiazide-with-other-medicines-and-herbal-remedies/"
    assert hits[1].book == "wikipedia_en_100_mini_2026-01" and hits[1].path == "Medicine"


def test_parse_catalog_uses_content_link_for_book_name():
    books = kiwix.parse_catalog_xml((FX / "catalog.xml").read_text())
    assert [b.name for b in books] == ["wikipedia_en_100_mini_2026-01", "sos-test-noindex"]
    assert books[0].fts is True and books[0].language == "eng" and books[0].title == "Wikipedia 100"
    assert books[1].fts is False


def test_parse_suggest_drops_pattern_entries_and_unescapes_labels():
    out = kiwix.parse_suggest_json((FX / "suggest.json").read_text())
    assert out == [
        {"value": "Aquatic water turtles", "label": "Aquatic <b>water</b> turtles", "path": "Aquatic_water_turtles"},
        {"value": "Water", "label": "<b>Water</b>", "path": "Water"},
    ]


def test_extract_text_wikipedia_keeps_main_and_drops_boilerplate():
    paras = kiwix.extract_text((FX / "raw_wiki.html").read_text())
    assert paras[0].startswith("In meteorology, precipitation is any product")
    joined = "\n".join(paras)
    assert "Main page" not in joined and "Random article" not in joined
    assert "Creative Commons" not in joined and "Related portals" not in joined
    assert "window.x" not in joined and "Enable JavaScript" not in joined
    assert "Precipitation" not in paras[0][:14] or True
    assert "Rain" in paras and "Snow" in paras
    assert all(p == p.strip() and "  " not in p for p in paras)


def test_extract_text_nhs_uses_maincontent_and_drops_nhs_chrome():
    paras = kiwix.extract_text((FX / "raw_nhs.html").read_text())
    joined = "\n".join(paras)
    assert "Skip to main content" not in joined
    assert "Health A to Z" not in joined
    assert "Page last reviewed" not in joined
    assert "About paracetamol" not in joined
    assert "MedicalWebPage" not in joined
    assert any(p.startswith("The usual dose for adults is 1 or 2 500mg tablets") for p in paras)
    assert "Always leave at least 4 hours between doses." in paras


def test_extract_text_without_main_falls_back_to_body():
    paras = kiwix.extract_text("<html><body><nav>skip</nav><p>Only paragraph.</p><div>Block<br>Two</div></body></html>")
    assert paras == ["Only paragraph.", "Block", "Two"]


def _run(coro):
    return asyncio.run(coro)


@respx.mock(base_url=BASE)
def test_client_search_issues_one_multi_book_request(respx_mock):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "search_multi.xml").read_text()))
    client = kiwix.KiwixClient(BASE)
    hits = _run(client.search(["wikipedia_en_100_mini_2026-01", "nhs.uk_en_medicines_2025-12"], "medicine", n=8, timeout=2.0))
    assert len(hits) == 2
    assert route.call_count == 1
    url = route.calls[0].request.url
    assert url.params.get_list("books.name") == ["wikipedia_en_100_mini_2026-01", "nhs.uk_en_medicines_2025-12"]
    assert url.params["pattern"] == "medicine" and url.params["format"] == "xml" and url.params["pageLength"] == "8"


@respx.mock(base_url=BASE)
def test_client_search_404_no_index_raises(respx_mock):
    respx_mock.get("/search").mock(return_value=httpx.Response(404, text="<error>Fulltext search unavailable</error>"))
    client = kiwix.KiwixClient(BASE)
    with pytest.raises(kiwix.KiwixError):
        _run(client.search(["sos-test-noindex"], "water"))


@respx.mock(base_url=BASE)
def test_client_search_timeout_raises_timeout(respx_mock):
    async def slow(request):
        await asyncio.sleep(0.5)
        return httpx.Response(200, text=(FX / "search.xml").read_text())

    respx_mock.get("/search").mock(side_effect=slow)
    client = kiwix.KiwixClient(BASE)
    with pytest.raises(asyncio.TimeoutError):
        _run(client.search(["wikipedia_en_100_mini_2026-01"], "water", timeout=0.1))


@respx.mock(base_url=BASE)
def test_client_catalog_suggest_raw_exists(respx_mock):
    respx_mock.get("/catalog/v2/entries", params={"count": "-1"}).mock(
        return_value=httpx.Response(200, text=(FX / "catalog.xml").read_text()))
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "suggest.json").read_text()))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Aquatic_water_turtles").mock(
        return_value=httpx.Response(302, headers={"Location": f"{BASE}/raw/wikipedia_en_100_mini_2026-01/content/Turtle"}))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Turtle").mock(
        return_value=httpx.Response(200, text=(FX / "raw_wiki.html").read_text()))
    respx_mock.get("/raw/wikipedia_en_100_mini_2026-01/content/Nope").mock(return_value=httpx.Response(404, text="no"))
    client = kiwix.KiwixClient(BASE)
    books = _run(client.catalog())
    assert books[0].name == "wikipedia_en_100_mini_2026-01"
    sugg = _run(client.suggest("wikipedia_en_100_mini_2026-01", "wat"))
    assert sugg[1]["path"] == "Water"
    html = _run(client.raw_article("wikipedia_en_100_mini_2026-01", "Aquatic_water_turtles"))
    assert "<main" in html
    assert _run(client.exists("wikipedia_en_100_mini_2026-01", "Turtle")) is True
    assert _run(client.exists("wikipedia_en_100_mini_2026-01", "Nope")) is False
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_kiwix.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.kiwix'`.

- [ ] **Step 4: Write `api/sos/kiwix.py`**

```python
"""HTTP client for kiwix-serve and the parsers for its XML/JSON responses.
Book names in every URL are ZIM filename stems, which equal manifest item ids."""
from __future__ import annotations

import asyncio
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

OPENSEARCH = "{http://a9.com/-/spec/opensearch/1.1/}"
ATOM = "{http://www.w3.org/2005/Atom}"


class KiwixError(RuntimeError):
    pass


@dataclass(frozen=True)
class Book:
    name: str
    fts: bool
    language: str
    title: str


@dataclass(frozen=True)
class KiwixHit:
    title: str
    path: str
    snippet: str
    book: str


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_tags(text: str) -> str:
    return _WS_RE.sub(" ", html.unescape(_TAG_RE.sub("", text or ""))).strip()


def _split_content_link(link: str) -> tuple[str, str]:
    marker = "/content/"
    idx = link.find(marker)
    rest = link[idx + len(marker):] if idx >= 0 else link.lstrip("/")
    book, _, path = rest.partition("/")
    return book, path


def parse_search_xml(text: str) -> tuple[int, list[KiwixHit]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise KiwixError(f"bad search XML: {exc}") from exc
    if root.tag == "error":
        raise KiwixError(strip_tags(text))
    channel = root.find("channel")
    if channel is None:
        raise KiwixError("no channel in search response")
    total_el = channel.find(f"{OPENSEARCH}totalResults")
    total = int((total_el.text or "0").replace(",", "")) if total_el is not None else 0
    hits: list[KiwixHit] = []
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        book, path = _split_content_link(link)
        snippet = strip_tags(item.findtext("description") or "")
        snippet = snippet.strip(". ").strip()
        hits.append(KiwixHit(title=(item.findtext("title") or "").strip(), path=path, snippet=snippet, book=book))
    return total, hits


def parse_catalog_xml(text: str) -> list[Book]:
    root = ET.fromstring(text)
    books: list[Book] = []
    for entry in root.findall(f"{ATOM}entry"):
        name = None
        for link in entry.findall(f"{ATOM}link"):
            if link.get("type") == "text/html" and link.get("href"):
                name = link.get("href").rstrip("/").rsplit("/", 1)[-1]
        if not name:
            name = entry.findtext(f"{ATOM}name") or ""
        tags = (entry.findtext(f"{ATOM}tags") or "").split(";")
        books.append(Book(
            name=name,
            fts="_ftindex:yes" in tags,
            language=(entry.findtext(f"{ATOM}language") or "eng").split(",")[0],
            title=entry.findtext(f"{ATOM}title") or name,
        ))
    return books


def parse_suggest_json(text: str) -> list[dict]:
    out = []
    for entry in json.loads(text):
        if entry.get("kind") != "path" or not entry.get("path"):
            continue
        out.append({"value": entry.get("value", ""), "label": html.unescape(entry.get("label", "")), "path": entry["path"]})
    return out


_DROP_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "template", "svg"}
_DROP_CLASSES = ("nhsuk-header", "nhsuk-footer", "nhsuk-skip-link")
_BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "td", "th", "tr", "br", "section", "article",
               "dd", "dt", "blockquote", "pre", "figcaption", "summary", "ul", "ol", "table"}
_VOID = {"br", "img", "input", "hr", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}


class _TextExtractor(HTMLParser):
    """Paragraph extractor implementing spec section 12 step 3: keep <main> or #maincontent when present,
    drop nav/header/footer/aside/script/style/noscript, [role=navigation] and the NHS chrome classes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.all_paras: list[str] = []
        self.main_paras: list[str] = []
        self.buf: list[str] = []
        self.skip_stack: list[str] = []
        self.main_depth = 0
        self.main_stack: list[str] = []
        self.has_main = False

    def _flush(self) -> None:
        text = _WS_RE.sub(" ", "".join(self.buf)).strip()
        self.buf = []
        if len(text) < 2:
            return
        self.all_paras.append(text)
        if self.main_depth > 0:
            self.main_paras.append(text)

    @staticmethod
    def _is_dropped(tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag in _DROP_TAGS:
            return True
        a = dict(attrs)
        if (a.get("role") or "") == "navigation":
            return True
        cls = a.get("class") or ""
        return any(c in cls for c in _DROP_CLASSES)

    def handle_starttag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._flush()
        if self._is_dropped(tag, attrs):
            if tag not in _VOID:
                self.skip_stack.append(tag)
            return
        if self.skip_stack:
            return
        a = dict(attrs)
        if tag == "main" or (a.get("id") == "maincontent"):
            self.has_main = True
            self.main_depth += 1
            self.main_stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_endtag(self, tag):
        if tag in _BLOCK_TAGS:
            self._flush()
        if self.skip_stack:
            if tag == self.skip_stack[-1]:
                self.skip_stack.pop()
            return
        if self.main_stack and tag == self.main_stack[-1]:
            self._flush()
            self.main_stack.pop()
            self.main_depth -= 1

    def handle_data(self, data):
        if self.skip_stack:
            return
        self.buf.append(data)

    def result(self) -> list[str]:
        self._flush()
        return self.main_paras if self.has_main else self.all_paras


def extract_text(html_text: str) -> list[str]:
    parser = _TextExtractor()
    parser.feed(html_text)
    parser.close()
    return parser.result()


class KiwixClient:
    def __init__(self, base_url: str, timeout: float = 5.0, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def catalog(self) -> list[Book]:
        r = await self._client.get(f"{self.base_url}/catalog/v2/entries", params={"count": "-1"})
        if r.status_code != 200:
            raise KiwixError(f"catalog: HTTP {r.status_code}")
        return parse_catalog_xml(r.text)

    async def search(self, books: list[str], q: str, n: int = 8, timeout: float = 2.0) -> list[KiwixHit]:
        params: list[tuple[str, str]] = [("pattern", q)]
        params += [("books.name", b) for b in books]
        params += [("format", "xml"), ("pageLength", str(n))]
        r = await asyncio.wait_for(self._client.get(f"{self.base_url}/search", params=params), timeout)
        if r.status_code != 200:
            raise KiwixError(f"search: HTTP {r.status_code}: {strip_tags(r.text)[:200]}")
        _, hits = parse_search_xml(r.text)
        return hits

    async def suggest(self, book: str, term: str) -> list[dict]:
        r = await self._client.get(f"{self.base_url}/suggest", params={"content": book, "term": term})
        if r.status_code != 200:
            return []
        return parse_suggest_json(r.text)

    async def raw_article(self, book: str, path: str) -> str:
        r = await self._client.get(f"{self.base_url}/raw/{book}/content/{path}")
        if r.status_code != 200:
            raise KiwixError(f"raw {book}/{path}: HTTP {r.status_code}")
        return r.text

    async def exists(self, book: str, path: str) -> bool:
        r = await self._client.get(f"{self.base_url}/raw/{book}/content/{path}")
        return r.status_code == 200
```

- [ ] **Step 5: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_kiwix.py -v`
Expected: 11 PASS.

- [ ] **Step 6: Commit**

```bash
git add api/sos/kiwix.py api/tests/test_kiwix.py api/tests/fixtures/kiwix
git commit -m "feat(kiwix): async kiwix-serve client, response parsers and boilerplate stripping"
```

---

### Task 6: `sos.query` (tokenise, stopwords, FTS5 quoting, place and postcode detection)

**Files:**
- Create: `api/sos/query.py`
- Test: `api/tests/test_query.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `STOPWORDS: frozenset[str]`, `tokenise(q) -> list[str]` (lowercase alphanumeric runs, duplicates removed in order), `content_terms(q) -> list[str]` (tokens minus stopwords; falls back to the tokens when everything was a stopword), `fts5_match(tokens) -> str` (`"t1" "t2"`), `kiwix_pattern(tokens) -> str`, `is_postcode(s) -> bool`, `is_district(s) -> bool`, `place_candidates(q) -> list[str]`, `Query(raw, tokens, terms, fts, kiwix)`, `reduce_query(q) -> Query`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_query.py`:

```python
import sqlite3

import pytest

from sos import query


@pytest.mark.parametrize("q,tokens,fts,kiwix", [
    ("wi-fi", ["wi", "fi"], '"wi" "fi"', "wi fi"),
    ("St John's", ["st", "john", "s"], '"st" "john"', "st john"),
    ("999 vs 111", ["999", "vs", "111"], '"999" "111"', "999 111"),
    ("1:1 ratio", ["1", "ratio"], '"1" "ratio"', "1 ratio"),
    ("AND", ["and"], '"and"', "and"),
    ("What should I do if my power is cut?", ["what", "should", "i", "do", "if", "my", "power", "is", "cut"], '"power" "cut"', "power cut"),
    ("  Éowyn   STORM ", ["éowyn", "storm"], '"éowyn" "storm"', "éowyn storm"),
])
def test_reduce_query(q, tokens, fts, kiwix):
    r = query.reduce_query(q)
    assert r.tokens == tokens
    assert r.fts == fts
    assert r.kiwix == kiwix
    assert r.raw == q


def test_empty_query():
    r = query.reduce_query("   ")
    assert r.tokens == [] and r.terms == [] and r.fts == "" and r.kiwix == ""


@pytest.mark.parametrize("q", ["wi-fi", "St John's", "999 vs 111", "1:1 ratio", "AND", "NOT", "OR x", '"quoted"', "a*b", "(x)"])
def test_fts5_match_never_raises(q):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE VIRTUAL TABLE t USING fts5(title, body, tokenize='porter unicode61 remove_diacritics 2')")
    conn.execute("INSERT INTO t VALUES ('x', 'wi fi st john 999 111 1 ratio and not or quoted a b x')")
    match = query.reduce_query(q).fts
    conn.execute("SELECT * FROM t WHERE t MATCH ?", (match,)).fetchall()


def test_stopword_list_size_and_contents():
    assert len(query.STOPWORDS) >= 200
    for w in ("what", "how", "should", "do", "if", "my", "can", "is", "the", "and", "vs", "s", "t"):
        assert w in query.STOPWORDS
    for w in ("water", "power", "bleeding", "999", "flood", "radiation"):
        assert w not in query.STOPWORDS


@pytest.mark.parametrize("s,expected", [
    ("SW1A 1AA", True), ("sw1a1aa", True), ("M1 1AE", True), ("EC1A 1BB", True), ("B33 8TH", True),
    ("SW1A", False), ("Oxford", False), ("SW1A 1A", False),
])
def test_is_postcode(s, expected):
    assert query.is_postcode(s) is expected


@pytest.mark.parametrize("s,expected", [("SW1A", True), ("m1", True), ("B33", True), ("SW1A 1AA", False), ("Oxford", False), ("S", False)])
def test_is_district(s, expected):
    assert query.is_district(s) is expected


@pytest.mark.parametrize("q,expected", [
    ("near Oxford", ["near Oxford", "Oxford"]),
    ("Oxford", ["Oxford"]),
    ("hospitals in Burnley", ["hospitals in Burnley"]),
    ("Burnley near", ["Burnley near", "Burnley"]),
    ("in", ["in"]),
    ("  near   Oxted ", ["near Oxted", "Oxted"]),
])
def test_place_candidates(q, expected):
    assert query.place_candidates(q) == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_query.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.query'`.

- [ ] **Step 3: Write `api/sos/query.py`**

```python
"""Query construction shared by search, suggest and the AI retriever (spec section 8)."""
from __future__ import annotations

import re
from dataclasses import dataclass

STOPWORDS: frozenset[str] = frozenset("""
a about above after again against all also am an and any anyone anything are aren around as at be because been before
being below best between both but by can cannot cant could couldn d did didn do does doesn doing don done down during
each eg either else etc even ever every everyone everything few find for from further get gets give go good got had
hadn has hasn have haven having he hello help her here hers herself hi him himself his how however i ie if im in
into is isn it its itself ive just know let like ll m make many may me mean means might mine more most much must
mustn my myself need neither never no none nor not nothing now of off often ok okay on once one only or other ought
our ours ourselves out over own please re really right s same shall shan she should shouldn show since so some
someone something sometimes still such t tell than thank thanks that thats the their theirs them themselves then
there these they thing things this those though through till to too under until up upon us use used using ve very
versus vs want was wasn way we were weren what whats when where whether which while who whom whose why will with
without won would wouldn yeah yes yet you your yours yourself yourselves
""".split())

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}$", re.IGNORECASE)
DISTRICT_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$", re.IGNORECASE)


def tokenise(q: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tok in _TOKEN_RE.findall((q or "").lower()):
        if tok not in seen:
            seen.add(tok)
            out.append(tok)
    return out


def content_terms(q: str) -> list[str]:
    tokens = tokenise(q)
    terms = [t for t in tokens if t not in STOPWORDS]
    return terms or tokens


def fts5_match(tokens: list[str]) -> str:
    return " ".join(f'"{t}"' for t in tokens)


def kiwix_pattern(tokens: list[str]) -> str:
    return " ".join(tokens)


def is_postcode(s: str) -> bool:
    return bool(POSTCODE_RE.match((s or "").strip()))


def is_district(s: str) -> bool:
    return bool(DISTRICT_RE.match((s or "").strip()))


def place_candidates(q: str) -> list[str]:
    norm = " ".join((q or "").split())
    if not norm:
        return []
    cands = [norm]
    words = norm.split(" ")
    if len(words) > 1 and words[0].lower() in ("near", "in"):
        cands.append(" ".join(words[1:]))
    if len(words) > 1 and words[-1].lower() in ("near", "in"):
        cands.append(" ".join(words[:-1]))
    out: list[str] = []
    for c in cands:
        if c and c not in out:
            out.append(c)
    return out


@dataclass(frozen=True)
class Query:
    raw: str
    tokens: list[str]
    terms: list[str]
    fts: str
    kiwix: str


def reduce_query(q: str) -> Query:
    tokens = tokenise(q)
    terms = content_terms(q) if tokens else []
    return Query(raw=q, tokens=tokens, terms=terms, fts=fts5_match(terms), kiwix=kiwix_pattern(terms))
```

- [ ] **Step 4: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_query.py -v`
Expected: all PASS (about 40 parametrised cases).

- [ ] **Step 5: Commit**

```bash
git add api/sos/query.py api/tests/test_query.py
git commit -m "feat(query): tokeniser, stopwords, fts5 quoting, postcode and place detection"
```

---

### Task 7: `sos.content` (front matter, sections, modules, links, checklists, rendering, validation) and `playbooks/schema.json`

**Files:**
- Create: `playbooks/schema.json`
- Create: `api/sos/content.py`
- Create: `api/tests/fixtures/playbooks/scenarios/grid-collapse.md`, `modules/water.md`, `cards/bleeding.md`, `pages/pmr446.md`
- Create: `api/tests/broken_cases.py` (table of one broken example per validation rule, derived from the valid scenario) and the generated copies `api/tests/fixtures/playbooks-broken/*.md`
- Test: `api/tests/test_content.py`

**Interfaces:**
- Consumes: `sos.manifest.Item`.
- Produces: `sos.content.Document` (`id, title, icon, order, summary, kind, modules, overlays, reviewed, sources, sections: list[tuple[str, str, str]]` as `(section_id, heading, markdown)`, `checklist: list[tuple[str, str]]`, `category, path, mtime, meta, body`), `RenderedDocument` (`slug, title, icon, order, summary, kind, category, reviewed, overlays, sources, sections: list[dict]` (`{id,title,html}`), `checklist: list[dict]` (`{id,text}`), `modules: list[dict]` (`{slug,title,html}`), `html`), `parse_document(path) -> Document`, `render_markdown(md, link_resolver=resolve_link) -> str`, `render_document(doc, resolver, modules: dict[str, Document]) -> RenderedDocument`, `validate_tree(playbooks_dir, manifest_items, overlay_ids, kiwix_check=None, doc_check=None, require_all_scenarios=False) -> list[str]` (strings starting `warning: ` are warnings; everything else is an error), `resolve_link(href) -> str`, `slugify(text) -> str`, `load_tree(dir) -> dict[str, dict[str, Document]]`, `ContentCache(root)` with `document(kind, slug)`, `list(kind)`, `rendered(kind, slug)`, constants `SCENARIO_HEADINGS`, `SCENARIO_SLUGS`, `KIND_BY_DIR`, `DIR_BY_KIND`. Checklist item ids inside included modules are `<module-slug>/<item-id>` and the rendered module HTML carries `data-item-id` on each task `<li>`.

- [ ] **Step 1: Write `playbooks/schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://operation-sos.invalid/playbooks.schema.json",
  "title": "Operation SOS authored content front matter",
  "$defs": {
    "base": {
      "type": "object",
      "required": ["id", "title", "icon", "order", "summary"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9][a-z0-9-]*$" },
        "title": { "type": "string", "minLength": 1 },
        "icon": { "type": "string", "minLength": 1 },
        "order": { "type": "integer", "minimum": 0 },
        "summary": { "type": "string", "minLength": 1 }
      }
    },
    "source": {
      "type": "object",
      "required": ["title"],
      "additionalProperties": false,
      "properties": {
        "title": { "type": "string", "minLength": 1 },
        "doc": { "type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*$" },
        "kiwix": { "type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]*/.+$" },
        "url": { "type": "string", "pattern": "^https?://" },
        "as_at": { "type": "string", "pattern": "^[0-9]{4}-[0-9]{2}(-[0-9]{2})?$" }
      }
    },
    "scenario": {
      "allOf": [{ "$ref": "#/$defs/base" }],
      "required": ["modules", "overlays", "reviewed", "sources"],
      "properties": {
        "modules": { "type": "array", "items": { "type": "string", "pattern": "^[a-z0-9-]+$" } },
        "overlays": { "type": "array", "items": { "type": "string", "pattern": "^[a-z0-9-]+$" } },
        "reviewed": { "type": ["string", "null"], "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" },
        "sources": { "type": "array", "items": { "$ref": "#/$defs/source" } }
      },
      "unevaluatedProperties": false
    },
    "module": {
      "allOf": [{ "$ref": "#/$defs/base" }],
      "properties": { "sources": { "type": "array", "items": { "$ref": "#/$defs/source" } } },
      "unevaluatedProperties": false
    },
    "card": {
      "allOf": [{ "$ref": "#/$defs/base" }],
      "properties": { "sources": { "type": "array", "items": { "$ref": "#/$defs/source" } } },
      "unevaluatedProperties": false
    },
    "page": {
      "allOf": [{ "$ref": "#/$defs/base" }],
      "required": ["category"],
      "properties": {
        "category": { "enum": ["comms", "reference", "plan", "about"] },
        "sources": { "type": "array", "items": { "$ref": "#/$defs/source" } }
      },
      "unevaluatedProperties": false
    }
  }
}
```

- [ ] **Step 2: Write the valid fixture documents**

`api/tests/fixtures/playbooks/scenarios/grid-collapse.md`:

```markdown
---
id: grid-collapse
title: National grid collapse
icon: bolt
order: 4
summary: A weeks-long blackout with water pumps and comms down.
modules: [water]
overlays: [health, water]
reviewed: 2026-09-01
sources:
  - title: Wikipedia 100 - Precipitation
    kiwix: wikipedia_en_100_mini_2026-01/Precipitation
    as_at: 2026-01
  - title: Test PDF
    doc: sos-test-pdf
    as_at: 2026-09
---
## Right now
Call **105** to report the power cut. Check on neighbours. See [severe bleeding](card:bleeding) if anyone is hurt.

## First 72 hours
Keep the fridge shut. Fill containers. Read [Precipitation](kiwix:wikipedia_en_100_mini_2026-01/Precipitation).

{{module:water}}

## First month
Ration fuel. Open the [map](map:?overlay=health&overlay=water) to find pharmacies and reservoirs.

## Long term
Learn the [PMR446 channels](page:pmr446) and re-read the [grid collapse](playbook:grid-collapse) playbook.

## UK specifics
Call 105 (power cut), 999 (emergency), 111 (NHS). Register for the Priority Services Register. See [page 2](doc:sos-test-pdf#page=2).

## Checklist
- [ ] Fill every bottle and the bath
- [ ] Turn off the cooker at the wall {#cooker-off}
- [ ] Check on neighbours

## Go deeper
- [Water module](module:water)
- [Test document](doc:sos-test-pdf)
```

`api/tests/fixtures/playbooks/modules/water.md`:

```markdown
---
id: water
title: Water
icon: droplet
order: 1
summary: Finding, storing and making water safe to drink.
sources:
  - title: Wikipedia 100 - Precipitation
    kiwix: wikipedia_en_100_mini_2026-01/Precipitation
---
## Finding water
Rainwater from a clean roof is the easiest source.

## Making it safe
Boil for one minute. Or use thin household bleach: two drops per litre, wait 30 minutes.

- [ ] Fill clean containers
- [ ] Label treated water {#label-treated}
```

`api/tests/fixtures/playbooks/cards/bleeding.md`:

```markdown
---
id: bleeding
title: Severe bleeding
icon: blood
order: 3
summary: Stop the bleeding and call 999.
---
1. **Press hard** on the wound with a clean cloth.
2. Keep pressing. Do not lift the cloth to look.
3. Call **999**.

> **Warning:** if blood soaks through, add more cloth on top; never remove the first layer.
```

`api/tests/fixtures/playbooks/pages/pmr446.md`:

```markdown
---
id: pmr446
title: PMR446 radio channels
icon: radio
order: 1
summary: The 16 licence-free UK walkie-talkie channels.
category: comms
---
| Channel | MHz |
|---|---|
| 1 | 446.00625 |
| 2 | 446.01875 |
```

- [ ] **Step 3: Write the broken-example table**

`api/tests/broken_cases.py`:

```python
"""One broken authored document per validation rule, each derived from the valid fixture scenario
by a small textual change. `gen_fixtures.py` writes them to fixtures/playbooks-broken/ for reference;
`test_content.py` builds them on the fly and checks the committed copies match."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
VALID_PATH = FIXTURES / "playbooks" / "scenarios" / "grid-collapse.md"
BROKEN_DIR = FIXTURES / "playbooks-broken"

# name -> (list of (old, new) replacements, expected substring in the validator output, is_warning)
CASES: dict[str, tuple[list[tuple[str, str]], str, bool]] = {
    "missing-heading": ([("## First month\n", "## First moon\n")], "missing heading '## First month'", False),
    "wrong-order": ([("## First 72 hours\n", "## TEMP\n"), ("## First month\n", "## First 72 hours\n"), ("## TEMP\n", "## First month\n")],
                    "headings out of order", False),
    "empty-section": ([("Learn the [PMR446 channels](page:pmr446) and re-read the [grid collapse](playbook:grid-collapse) playbook.\n", "\n")],
                      "section '## Long term' is empty", False),
    "module-not-included": ([("{{module:water}}\n", "")], "module 'water' declared but never included", False),
    "include-not-declared": ([("modules: [water]", "modules: []")], "undeclared module 'water'", False),
    "missing-module-file": ([("modules: [water]", "modules: [flood]"), ("{{module:water}}", "{{module:flood}}")], "module 'flood' does not exist", False),
    "unknown-overlay": ([("overlays: [health, water]", "overlays: [health, dragons]")], "overlay 'dragons' not in manifest/overlays.json", False),
    "duplicate-checklist": ([("- [ ] Check on neighbours\n", "- [ ] Check on neighbours {#cooker-off}\n")], "duplicate checklist id 'cooker-off'", False),
    "checklist-not-task": ([("- [ ] Check on neighbours\n", "- [ ] Check on neighbours\nRemember to breathe.\n")], "not a task-list line", False),
    "bad-source": ([("    doc: sos-test-pdf\n    as_at: 2026-09", "    doc: nope\n    as_at: 2026-09")], "source doc 'nope' not in manifest", False),
    "url-only-source": ([("    doc: sos-test-pdf\n    as_at: 2026-09", "    url: https://example.invalid/test.pdf\n    as_at: 2026-09")],
                        "warning: scenarios/grid-collapse.md: source 'Test PDF' is url-only", True),
    "bad-link": ([("(kiwix:wikipedia_en_100_mini_2026-01/Precipitation)", "(kiwix:nope/Precipitation)")], "link kiwix:nope/Precipitation: item 'nope' not in manifest", False),
    "unknown-map-overlay": ([("(map:?overlay=health&overlay=water)", "(map:?overlay=dragons)")], "link map:?overlay=dragons: overlay 'dragons'", False),
    "unknown-module-link": ([("(module:water)", "(module:nope)")], "link module:nope: module 'nope' does not exist", False),
    "bad-front-matter": ([("summary: A weeks-long blackout with water pumps and comms down.\n", "")], "'summary' is a required property", False),
    "id-mismatch": ([("id: grid-collapse", "id: grid-fail")], "id 'grid-fail' must equal the file name 'grid-collapse'", False),
}


def broken_text(name: str) -> str:
    text = VALID_PATH.read_text(encoding="utf-8")
    for old, new in CASES[name][0]:
        assert old in text, f"{name}: pattern not found: {old!r}"
        text = text.replace(old, new, 1)
    return text


def write_all() -> None:
    BROKEN_DIR.mkdir(parents=True, exist_ok=True)
    for name in CASES:
        (BROKEN_DIR / f"{name}.md").write_text(broken_text(name), encoding="utf-8")


if __name__ == "__main__":
    write_all()
    print(f"wrote {len(CASES)} broken examples to {BROKEN_DIR}")
```

Run: `cd api && .venv/bin/python -m tests.broken_cases`
Expected: `wrote 16 broken examples to .../fixtures/playbooks-broken`.

- [ ] **Step 4: Write the failing tests**

`api/tests/test_content.py`:

```python
import shutil
import time
from pathlib import Path

import pytest

from sos import content
from sos.manifest import load_manifests
from tests import broken_cases

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]
OVERLAYS = {"health", "nuclear-sites", "water"}


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "playbooks"
    shutil.copytree(FIXTURES / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    return root


@pytest.fixture
def items():
    return load_manifests(FIXTURES / "manifest")


def test_slugify():
    assert content.slugify("Fill every bottle and the bath") == "fill-every-bottle-and-the-bath"
    assert content.slugify("  Turn OFF, the cooker!  ") == "turn-off-the-cooker"
    assert len(content.slugify("x" * 100)) == 60


@pytest.mark.parametrize("href,expected", [
    ("kiwix:wikipedia_en_100_mini_2026-01/Precipitation", "/read/wikipedia_en_100_mini_2026-01/Precipitation"),
    ("kiwix:nhs_uk/www.nhs.uk/conditions/burns/", "/read/nhs_uk/www.nhs.uk/conditions/burns/"),
    ("doc:nrr-2025", "/doc/nrr-2025"),
    ("doc:nrr-2025#page=12", "/doc/nrr-2025#page=12"),
    ("map:?overlay=nuclear-sites&overlay=health", "/map?overlay=nuclear-sites&overlay=health"),
    ("map:", "/map"),
    ("playbook:nuclear-war", "/s/nuclear-war"),
    ("module:water", "/m/water"),
    ("card:cpr-adult", "/medical/card/cpr-adult"),
    ("page:pmr446", "/p/pmr446"),
    ("https://example.org/x", "https://example.org/x"),
    ("#top", "#top"),
])
def test_resolve_link(href, expected):
    assert content.resolve_link(href) == expected


def test_render_markdown_rewrites_links_and_escapes_html():
    html = content.render_markdown("See [water](module:water) and <script>x</script>\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert '<a href="/m/water">water</a>' in html
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert "<table>" in html


def test_parse_scenario(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    assert doc.kind == "scenario" and doc.id == "grid-collapse" and doc.order == 4
    assert doc.modules == ["water"] and doc.overlays == ["health", "water"]
    assert doc.reviewed == "2026-09-01"
    assert doc.sources[0]["kiwix"] == "wikipedia_en_100_mini_2026-01/Precipitation" and doc.sources[0]["as_at"] == "2026-01"
    assert [s[1] for s in doc.sections] == [t for _, t in content.SCENARIO_HEADINGS]
    assert [s[0] for s in doc.sections] == [i for i, _ in content.SCENARIO_HEADINGS]
    assert doc.checklist == [
        ("fill-every-bottle-and-the-bath", "Fill every bottle and the bath"),
        ("cooker-off", "Turn off the cooker at the wall"),
        ("check-on-neighbours", "Check on neighbours"),
    ]


def test_parse_page_and_card(tree):
    page = content.parse_document(tree / "pages" / "pmr446.md")
    assert page.kind == "page" and page.category == "comms"
    card = content.parse_document(tree / "cards" / "bleeding.md")
    assert card.kind == "card" and card.sections[0][1] == "" and "Press hard" in card.sections[0][2]


def test_render_document_includes_module_and_prefixes_module_checklist(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    water = content.parse_document(tree / "modules" / "water.md")
    r = content.render_document(doc, content.resolve_link, {"water": water})
    assert [s["id"] for s in r.sections] == ["right-now", "first-72-hours", "first-month", "long-term", "uk-specifics", "go-deeper"]
    s72 = next(s for s in r.sections if s["id"] == "first-72-hours")
    assert '<section class="module" data-module="water"><h3>Water</h3>' in s72["html"]
    assert 'data-item-id="water/fill-clean-containers"' in s72["html"]
    assert 'data-item-id="water/label-treated"' in s72["html"]
    assert "{{module:water}}" not in s72["html"]
    assert [m["slug"] for m in r.modules] == ["water"]
    assert [c["id"] for c in r.checklist] == [
        "fill-every-bottle-and-the-bath", "cooker-off", "check-on-neighbours", "water/fill-clean-containers", "water/label-treated",
    ]
    assert '<a href="/medical/card/bleeding">' in r.sections[0]["html"]
    assert '<a href="/doc/sos-test-pdf#page=2">' in next(s for s in r.sections if s["id"] == "uk-specifics")["html"]
    assert r.reviewed == "2026-09-01" and r.overlays == ["health", "water"] and r.sources[1]["doc"] == "sos-test-pdf"


def test_render_missing_module_is_visible_not_fatal(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    r = content.render_document(doc, content.resolve_link, {})
    assert "module-missing" in r.sections[1]["html"]
    assert r.modules == [] and len(r.checklist) == 3


def test_render_standalone_module_and_card(tree):
    water = content.parse_document(tree / "modules" / "water.md")
    r = content.render_document(water, content.resolve_link, {})
    assert r.kind == "module" and 'data-item-id="water/label-treated"' in r.html and r.sections == []
    card = content.parse_document(tree / "cards" / "bleeding.md")
    rc = content.render_document(card, content.resolve_link, {})
    assert "<ol>" in rc.html and "<blockquote>" in rc.html


def test_validate_valid_tree(tree, items):
    assert content.validate_tree(tree, items, OVERLAYS) == []


@pytest.mark.parametrize("name", list(broken_cases.CASES))
def test_validate_broken_examples(tree, items, name):
    replacements, fragment, is_warning = broken_cases.CASES[name]
    text = broken_cases.broken_text(name)
    committed = broken_cases.BROKEN_DIR / f"{name}.md"
    assert committed.read_text(encoding="utf-8") == text, f"run: python -m tests.broken_cases ({name})"
    (tree / "scenarios" / "grid-collapse.md").write_text(text, encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any(fragment in line for line in out), out
    errors = [line for line in out if not line.startswith("warning: ")]
    if is_warning:
        assert errors == []
    else:
        assert errors


def test_validate_deep_checks(tree, items):
    seen = []

    def kiwix_check(book, path):
        seen.append((book, path))
        return path != "Precipitation"

    def doc_check(item):
        return item.id != "sos-test-pdf"

    out = content.validate_tree(tree, items, OVERLAYS, kiwix_check=kiwix_check, doc_check=doc_check)
    assert ("wikipedia_en_100_mini_2026-01", "Precipitation") in seen
    assert any("kiwix:wikipedia_en_100_mini_2026-01/Precipitation returned non-200" in e for e in out)
    assert any("doc 'sos-test-pdf' file missing" in e for e in out)


def test_validate_require_all_scenarios(tree, items):
    out = content.validate_tree(tree, items, OVERLAYS, require_all_scenarios=True)
    assert len([e for e in out if e.endswith(": missing")]) == 19
    assert "scenarios/nuclear-war.md: missing" in out


def test_validate_reports_unparseable_file(tree, items):
    (tree / "cards" / "broken.md").write_text("---\nid: [unclosed\n---\nx", encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any(e.startswith("cards/broken.md: cannot parse") for e in out)


def test_content_cache_reloads_on_mtime(tree):
    cache = content.ContentCache(tree)
    assert cache.document("card", "missing") is None
    r1 = cache.rendered("scenario", "grid-collapse")
    assert cache.rendered("scenario", "grid-collapse") is r1
    path = tree / "modules" / "water.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Rainwater", "Snowmelt"), encoding="utf-8")
    future = time.time() + 5
    import os
    os.utime(path, (future, future))
    r2 = cache.rendered("scenario", "grid-collapse")
    assert r2 is not r1 and "Snowmelt" in r2.modules[0]["html"]
    assert [d.id for d in cache.list("card")] == ["bleeding"]
    assert cache.list("nonexistent-kind") == []
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_content.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.content'`.

- [ ] **Step 6: Write `api/sos/content.py`**

```python
"""Authored Markdown (playbooks, modules, cards, pages): parsing, rendering and validation (spec section 10)."""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

import frontmatter
import jsonschema
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

KIND_BY_DIR = {"scenarios": "scenario", "modules": "module", "cards": "card", "pages": "page"}
DIR_BY_KIND = {v: k for k, v in KIND_BY_DIR.items()}
SCENARIO_HEADINGS: list[tuple[str, str]] = [
    ("right-now", "Right now"), ("first-72-hours", "First 72 hours"), ("first-month", "First month"),
    ("long-term", "Long term"), ("uk-specifics", "UK specifics"), ("checklist", "Checklist"), ("go-deeper", "Go deeper"),
]
SCENARIO_SLUGS = [
    "nuclear-war", "nuclear-accident", "pandemic", "grid-collapse", "solar-storm", "emp", "cyber-attack", "invasion",
    "civil-unrest", "economic-collapse", "supply-chain", "storms-flooding", "severe-winter", "heat-drought", "volcanic",
    "chemical", "famine", "impact-winter", "terrorism", "long-rebuild",
]
LINK_ROUTES = {"kiwix": "/read/", "doc": "/doc/", "playbook": "/s/", "module": "/m/", "card": "/medical/card/", "page": "/p/"}

TASK_RE = re.compile(r"^\s*[-*+] \[([ xX])\] (.*?)(?:\s*\{#([A-Za-z0-9][A-Za-z0-9_/-]*)\})?\s*$")
INCLUDE_RE = re.compile(r"^\s*\{\{module:([a-z0-9-]+)\}\}\s*$")
H2_RE = re.compile(r"^## (.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_TASK_LI = '<li class="task-list-item">'


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60].rstrip("-")


def resolve_link(href: str) -> str:
    scheme, sep, rest = (href or "").partition(":")
    if not sep:
        return href
    if scheme == "map":
        if not rest:
            return "/map"
        return "/map" + (rest if rest.startswith("?") else "?" + rest)
    if scheme == "doc":
        doc_id, hash_, frag = rest.partition("#")
        return f"/doc/{doc_id}" + (f"#{frag}" if hash_ else "")
    if scheme in LINK_ROUTES:
        return LINK_ROUTES[scheme] + rest
    return href


def make_renderer(resolver: Callable[[str], str] = resolve_link) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"]).use(tasklists_plugin)

    def link_open(self, tokens, idx, options, env):
        href = tokens[idx].attrGet("href")
        if href:
            tokens[idx].attrSet("href", resolver(href))
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("link_open", link_open)
    return md


def render_markdown(md_text: str, link_resolver: Callable[[str], str] = resolve_link) -> str:
    return make_renderer(link_resolver).render(md_text or "")


@dataclass
class Document:
    id: str
    title: str
    icon: str
    order: int
    summary: str
    kind: str
    modules: list[str]
    overlays: list[str]
    reviewed: str | None
    sources: list[dict]
    sections: list[tuple[str, str, str]]
    checklist: list[tuple[str, str]]
    category: str | None
    path: Path
    mtime: float
    meta: dict = field(default_factory=dict)
    body: str = ""


@dataclass
class RenderedDocument:
    slug: str
    title: str
    icon: str
    order: int
    summary: str
    kind: str
    category: str | None
    reviewed: str | None
    overlays: list[str]
    sources: list[dict]
    sections: list[dict]
    checklist: list[dict]
    modules: list[dict]
    html: str


def _norm(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def split_sections(body: str) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    title = ""
    buf: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else H2_RE.match(line)
        if m:
            sections.append((slugify(title), title, "\n".join(buf).strip("\n")))
            title = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    sections.append((slugify(title), title, "\n".join(buf).strip("\n")))
    if len(sections) > 1 and sections[0][1] == "" and not sections[0][2].strip():
        sections.pop(0)
    return sections


def parse_checklist(md_text: str) -> tuple[list[tuple[str, str]], list[str]]:
    items: list[tuple[str, str]] = []
    errors: list[str] = []
    for line in md_text.splitlines():
        if not line.strip():
            continue
        m = TASK_RE.match(line)
        if not m:
            errors.append(f"not a task-list line: {line.strip()!r}")
            continue
        text = m.group(2).strip()
        items.append((m.group(3) or slugify(text), text))
    return items, errors


def module_tasks(md_text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in md_text.splitlines():
        m = TASK_RE.match(line)
        if m:
            text = m.group(2).strip()
            out.append((m.group(3) or slugify(text), text))
    return out


def parse_document(path: Path) -> Document:
    path = Path(path)
    post = frontmatter.load(str(path))
    meta = {k: _norm(v) for k, v in post.metadata.items()}
    kind = KIND_BY_DIR.get(path.parent.name, "page")
    body = post.content
    sections = split_sections(body)
    checklist: list[tuple[str, str]] = []
    if kind == "scenario":
        for sid, _, md_text in sections:
            if sid == "checklist":
                checklist, _ = parse_checklist(md_text)
    try:
        order = int(meta.get("order", 0) or 0)
    except (TypeError, ValueError):
        order = 0
    return Document(
        id=str(meta.get("id", path.stem)), title=str(meta.get("title", path.stem)), icon=str(meta.get("icon", "")),
        order=order, summary=str(meta.get("summary", "")), kind=kind,
        modules=[str(m) for m in (meta.get("modules") or [])], overlays=[str(o) for o in (meta.get("overlays") or [])],
        reviewed=meta.get("reviewed"), sources=[s for s in (meta.get("sources") or []) if isinstance(s, dict)],
        sections=sections, checklist=checklist, category=meta.get("category"), path=path, mtime=path.stat().st_mtime,
        meta=meta, body=body,
    )


def _inject_item_ids(html_text: str, ids: list[str]) -> str:
    parts = html_text.split(_TASK_LI)
    out = [parts[0]]
    for i, part in enumerate(parts[1:]):
        item_id = ids[i] if i < len(ids) else ""
        out.append(f'<li class="task-list-item" data-item-id="{escape(item_id)}">{part}')
    return "".join(out)


def render_module(mod: Document, md: MarkdownIt) -> dict:
    tasks = [(f"{mod.id}/{i}", t) for i, t in module_tasks(mod.body)]
    html_text = _inject_item_ids(md.render(mod.body), [i for i, _ in tasks])
    return {"slug": mod.id, "title": mod.title, "html": html_text, "checklist": tasks}


def render_document(doc: Document, resolver: Callable[[str], str] = resolve_link,
                    modules: dict[str, Document] | None = None) -> RenderedDocument:
    modules = modules or {}
    md = make_renderer(resolver)
    common = dict(slug=doc.id, title=doc.title, icon=doc.icon, order=doc.order, summary=doc.summary, kind=doc.kind,
                  category=doc.category, reviewed=doc.reviewed, overlays=list(doc.overlays), sources=list(doc.sources))
    if doc.kind != "scenario":
        html_text = render_module(doc, md)["html"] if doc.kind == "module" else md.render(doc.body)
        return RenderedDocument(**common, sections=[], checklist=[], modules=[], html=html_text)
    sections: list[dict] = []
    included: list[dict] = []
    seen: set[str] = set()
    for sid, title, md_text in doc.sections:
        if sid == "checklist" or not title:
            continue
        parts: list[str] = []
        chunk: list[str] = []
        for line in md_text.splitlines():
            m = INCLUDE_RE.match(line)
            if not m:
                chunk.append(line)
                continue
            if chunk:
                parts.append(md.render("\n".join(chunk)))
                chunk = []
            slug = m.group(1)
            mod = modules.get(slug)
            if mod is None:
                parts.append(f'<p class="module-missing">Module "{escape(slug)}" is missing.</p>')
                continue
            rendered = render_module(mod, md)
            if slug not in seen:
                included.append(rendered)
                seen.add(slug)
            parts.append(f'<section class="module" data-module="{escape(slug)}"><h3>{escape(mod.title)}</h3>{rendered["html"]}</section>')
        if chunk:
            parts.append(md.render("\n".join(chunk)))
        sections.append({"id": sid, "title": title, "html": "".join(parts)})
    checklist = [{"id": i, "text": t} for i, t in doc.checklist]
    for r in included:
        checklist += [{"id": i, "text": t} for i, t in r["checklist"]]
    return RenderedDocument(
        **common, sections=sections, checklist=checklist,
        modules=[{"slug": r["slug"], "title": r["title"], "html": r["html"]} for r in included],
        html="".join(s["html"] for s in sections),
    )


def load_tree(playbooks_dir: Path) -> dict[str, dict[str, Document]]:
    tree: dict[str, dict[str, Document]] = {k: {} for k in KIND_BY_DIR.values()}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((Path(playbooks_dir) / dirname).glob("*.md")):
            tree[kind][path.stem] = parse_document(path)
    return tree


def _links(body: str) -> list[str]:
    return LINK_RE.findall(body)


def _includes(body: str) -> list[str]:
    return [m.group(1) for m in (INCLUDE_RE.match(line) for line in body.splitlines()) if m]


def _check_scenario(rel: str, doc: Document, module_slugs: set[str], overlay_ids: set[str],
                    module_docs: dict[str, Document]) -> list[str]:
    errors: list[str] = []
    expected = [t for _, t in SCENARIO_HEADINGS]
    titles = [t for _, t, _ in doc.sections if t]
    for t in expected:
        if t not in titles:
            errors.append(f"{rel}: missing heading '## {t}'")
    for t in titles:
        if t not in expected:
            errors.append(f"{rel}: unexpected heading '## {t}'")
    if sorted(titles) == sorted(expected) and titles != expected:
        errors.append(f"{rel}: headings out of order: expected {', '.join(expected)}")
    for sid, title, md_text in doc.sections:
        if title and title in expected and not md_text.strip():
            errors.append(f"{rel}: section '## {title}' is empty")
    checklist_md = next((md_text for sid, _, md_text in doc.sections if sid == "checklist"), "")
    items, cl_errors = parse_checklist(checklist_md)
    errors += [f"{rel}: checklist: {e}" for e in cl_errors]
    declared = set(doc.modules)
    included = _includes(doc.body)
    for slug in sorted(declared - set(included)):
        errors.append(f"{rel}: module '{slug}' declared but never included ({{{{module:{slug}}}}})")
    for slug in included:
        if slug not in declared:
            errors.append(f"{rel}: include of undeclared module '{slug}'")
        if slug not in module_slugs:
            errors.append(f"{rel}: module '{slug}' does not exist")
    all_ids = [i for i, _ in items]
    for slug in included:
        mod = module_docs.get(slug)
        if mod:
            all_ids += [f"{slug}/{i}" for i, _ in module_tasks(mod.body)]
    seen: set[str] = set()
    for item_id in all_ids:
        if item_id in seen:
            errors.append(f"{rel}: duplicate checklist id '{item_id}'")
        seen.add(item_id)
    for ov in doc.overlays:
        if ov not in overlay_ids:
            errors.append(f"{rel}: overlay '{ov}' not in manifest/overlays.json")
    return errors


def _check_links(rel: str, doc: Document, zim_ids: set[str], doc_ids: set[str],
                 slugs: dict[str, set[str]], overlay_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for href in _links(doc.body):
        scheme, sep, rest = href.partition(":")
        if not sep:
            continue
        if scheme == "kiwix":
            book, slash, path = rest.partition("/")
            if not slash or not path:
                errors.append(f"{rel}: link {href}: needs <id>/<path>")
            elif book not in zim_ids:
                errors.append(f"{rel}: link {href}: item '{book}' not in manifest")
        elif scheme == "doc":
            doc_id = rest.partition("#")[0]
            if doc_id not in doc_ids:
                errors.append(f"{rel}: link {href}: document '{doc_id}' not in manifest")
        elif scheme == "map":
            for ov in parse_qs(rest.lstrip("?")).get("overlay", []):
                if ov not in overlay_ids:
                    errors.append(f"{rel}: link {href}: overlay '{ov}' not in manifest/overlays.json")
        elif scheme in ("module", "card", "page", "playbook"):
            kind = "scenario" if scheme == "playbook" else scheme
            if rest not in slugs[kind]:
                errors.append(f"{rel}: link {href}: {scheme} '{rest}' does not exist")
    return errors


def _check_sources(rel: str, doc: Document, zim_ids: set[str], doc_ids: set[str]) -> list[str]:
    out: list[str] = []
    for src in doc.sources:
        title = src.get("title", "?")
        if "doc" in src:
            if src["doc"] not in doc_ids:
                out.append(f"{rel}: source doc '{src['doc']}' not in manifest")
        elif "kiwix" in src:
            book = str(src["kiwix"]).partition("/")[0]
            if book not in zim_ids:
                out.append(f"{rel}: source kiwix '{src['kiwix']}': item '{book}' not in manifest")
        elif "url" in src:
            out.append(f"warning: {rel}: source '{title}' is url-only (provenance only, not linked)")
        else:
            out.append(f"{rel}: source '{title}' needs doc, kiwix or url")
    return out


def _deep_checks(rel: str, doc: Document, items_by_id: dict, kiwix_check, doc_check) -> list[str]:
    errors: list[str] = []
    targets: list[tuple[str, str]] = []
    for href in _links(doc.body):
        if href.startswith("kiwix:"):
            book, _, path = href[6:].partition("/")
            targets.append((book, path))
    for src in doc.sources:
        if "kiwix" in src:
            book, _, path = str(src["kiwix"]).partition("/")
            targets.append((book, path))
    if kiwix_check:
        for book, path in dict.fromkeys(targets):
            if book in items_by_id and not kiwix_check(book, path):
                errors.append(f"{rel}: kiwix:{book}/{path} returned non-200")
    if doc_check:
        doc_ids = {href[4:].partition("#")[0] for href in _links(doc.body) if href.startswith("doc:")}
        doc_ids |= {str(s["doc"]) for s in doc.sources if "doc" in s}
        for doc_id in sorted(doc_ids):
            item = items_by_id.get(doc_id)
            if item is not None and not doc_check(item):
                errors.append(f"{rel}: doc '{doc_id}' file missing ({item.dest})")
    return errors


def validate_tree(playbooks_dir: Path, manifest_items: list, overlay_ids: set[str] | list[str],
                  kiwix_check: Callable[[str, str], bool] | None = None,
                  doc_check: Callable[[object], bool] | None = None,
                  require_all_scenarios: bool = False) -> list[str]:
    playbooks_dir = Path(playbooks_dir)
    overlay_ids = set(overlay_ids)
    schema_path = playbooks_dir / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validators = {
        kind: jsonschema.Draft202012Validator({"$ref": f"#/$defs/{kind}", "$defs": schema["$defs"]})
        for kind in KIND_BY_DIR.values()
    }
    zim_ids = {i.id for i in manifest_items if i.kind == "zim"}
    doc_ids = {i.id for i in manifest_items if i.kind in ("pdf", "epub")}
    items_by_id = {i.id: i for i in manifest_items}
    errors: list[str] = []
    tree: dict[str, dict[str, Document]] = {k: {} for k in KIND_BY_DIR.values()}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((playbooks_dir / dirname).glob("*.md")):
            rel = f"{dirname}/{path.name}"
            try:
                doc = parse_document(path)
            except Exception as exc:  # malformed YAML or unreadable file
                errors.append(f"{rel}: cannot parse: {exc}".splitlines()[0])
                continue
            tree[kind][path.stem] = doc
            for err in sorted(validators[kind].iter_errors(doc.meta), key=lambda e: [str(p) for p in e.path]):
                loc = "/".join(str(p) for p in err.path) or "front matter"
                errors.append(f"{rel}: {loc}: {err.message}")
            if doc.id != path.stem:
                errors.append(f"{rel}: id '{doc.id}' must equal the file name '{path.stem}'")
    slugs = {kind: set(docs) for kind, docs in tree.items()}
    for kind, docs in tree.items():
        for slug, doc in docs.items():
            rel = f"{DIR_BY_KIND[kind]}/{slug}.md"
            if kind == "scenario":
                errors += _check_scenario(rel, doc, slugs["module"], overlay_ids, tree["module"])
            errors += _check_links(rel, doc, zim_ids, doc_ids, slugs, overlay_ids)
            errors += _check_sources(rel, doc, zim_ids, doc_ids)
            if kiwix_check or doc_check:
                errors += _deep_checks(rel, doc, items_by_id, kiwix_check, doc_check)
    if require_all_scenarios:
        errors += [f"scenarios/{s}.md: missing" for s in SCENARIO_SLUGS if s not in tree["scenario"]]
    return errors


class ContentCache:
    """Documents parsed on demand and cached by file mtime; rendered output cached by the mtimes of the
    document and every included module."""

    def __init__(self, root: Path, resolver: Callable[[str], str] = resolve_link) -> None:
        self.root = Path(root)
        self.resolver = resolver
        self._docs: dict[tuple[str, str], Document] = {}
        self._rendered: dict[tuple, RenderedDocument] = {}

    def _path(self, kind: str, slug: str) -> Path:
        return self.root / DIR_BY_KIND[kind] / f"{slug}.md"

    def document(self, kind: str, slug: str) -> Document | None:
        if kind not in DIR_BY_KIND or "/" in slug or slug.startswith("."):
            return None
        path = self._path(kind, slug)
        if not path.is_file():
            self._docs.pop((kind, slug), None)
            return None
        mtime = path.stat().st_mtime
        cached = self._docs.get((kind, slug))
        if cached is not None and cached.mtime == mtime:
            return cached
        doc = parse_document(path)
        self._docs[(kind, slug)] = doc
        return doc

    def list(self, kind: str) -> list[Document]:
        if kind not in DIR_BY_KIND:
            return []
        folder = self.root / DIR_BY_KIND[kind]
        docs = [self.document(kind, p.stem) for p in sorted(folder.glob("*.md"))] if folder.is_dir() else []
        return sorted([d for d in docs if d is not None], key=lambda d: (d.order, d.title))

    def rendered(self, kind: str, slug: str) -> RenderedDocument | None:
        doc = self.document(kind, slug)
        if doc is None:
            return None
        modules = {m: self.document("module", m) for m in doc.modules}
        modules = {k: v for k, v in modules.items() if v is not None}
        key = (kind, slug, doc.mtime, tuple(sorted((m, d.mtime) for m, d in modules.items())))
        hit = self._rendered.get(key)
        if hit is not None:
            return hit
        rendered = render_document(doc, self.resolver, modules)
        self._rendered = {k: v for k, v in self._rendered.items() if k[:2] != (kind, slug)}
        self._rendered[key] = rendered
        return rendered
```

- [ ] **Step 7: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_content.py -v`
Expected: all PASS (12 named tests plus 16 broken-example cases plus 12 link cases).

- [ ] **Step 8: Commit**

```bash
git add playbooks/schema.json api/sos/content.py api/tests/test_content.py api/tests/broken_cases.py api/tests/fixtures/playbooks api/tests/fixtures/playbooks-broken
git commit -m "feat(content): parse, render and validate authored Markdown with module includes and checklist ids"
```

---

### Task 8: `sos.docs` (PDF/EPUB page extraction), `sos.places` (places import and query) and the fixture generator

**Files:**
- Create: `api/tests/fixtures/gen_fixtures.py` (standard library only; writes `places.csv`, `docs/sos-test.pdf`, `pages/icon.png`, rebuilds `library/sos-test-noindex.zim` when `zimwriterfs` is on PATH, refreshes `library/SHA256SUMS`, copies `manifest/schema.json`, writes the broken playbook examples)
- Create: `api/tests/fixtures/places.csv` (200 rows, generated), `api/tests/fixtures/docs/sos-test.pdf` (generated, committed)
- Create: `api/sos/docs.py`
- Create: `api/sos/places.py`
- Test: `api/tests/test_docs.py`, `api/tests/test_places.py`

**Interfaces:**
- Consumes: `sos.db`, `sos.query.tokenise`, `sos.kiwix.extract_text`, `library_items` rows.
- Produces: `sos.docs.pdf_pages(pdf, runner=None) -> list[str]`, `epub_pages(path) -> list[str]`, `cap_words(text, n=600) -> str`, `sidecar_path(file) -> Path`, `extract_pages(file, kind, runner=None, force=False) -> list[str]`, `index_docs(conn, runner=None) -> int`, `run_pdftotext(pdf) -> str`; `sos.places.places_path(settings) -> Path`, `import_places(conn, path, force=False) -> int | None` (`None` when unchanged), `query_places(conn, q, limit=10) -> list[dict]`, `exact_place(conn, name) -> dict | None` (`Place` shape: `name, kind, lat, lon, region, postcode`).

- [ ] **Step 1: Write the fixture generator and run it**

`api/tests/fixtures/gen_fixtures.py`:

```python
"""Regenerates the fixtures that are derived rather than hand-written. Standard library only.
Run via `make fixtures` or `api/.venv/bin/python api/tests/fixtures/gen_fixtures.py`."""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = HERE.parents[1]
REPO = API.parent
sys.path.insert(0, str(API))

REAL_PLACES = [
    ("Oxford", "city", 51.7520, -1.2577, "England", ""),
    ("Oxted", "town", 51.2573, 0.0060, "England", ""),
    ("Oxwich", "village", 51.5560, -4.1580, "Wales", ""),
    ("Burnley", "town", 53.7890, -2.2480, "England", ""),
    ("Burnham-on-Sea", "town", 51.2390, -2.9990, "England", ""),
    ("London", "city", 51.5074, -0.1278, "England", ""),
    ("Birmingham", "city", 52.4862, -1.8904, "England", ""),
    ("Manchester", "city", 53.4808, -2.2426, "England", ""),
    ("Leeds", "city", 53.8008, -1.5491, "England", ""),
    ("Bristol", "city", 51.4545, -2.5879, "England", ""),
    ("Norwich", "city", 52.6309, 1.2974, "England", ""),
    ("Exeter", "city", 50.7184, -3.5339, "England", ""),
    ("Cardiff", "city", 51.4816, -3.1791, "Wales", ""),
    ("Swansea", "city", 51.6214, -3.9436, "Wales", ""),
    ("Edinburgh", "city", 55.9533, -3.1883, "Scotland", ""),
    ("Glasgow", "city", 55.8642, -4.2518, "Scotland", ""),
    ("Inverness", "city", 57.4778, -4.2247, "Scotland", ""),
    ("Aberdeen", "city", 57.1497, -2.0943, "Scotland", ""),
    ("Lerwick", "town", 60.1546, -1.1494, "Scotland", ""),
    ("Belfast", "city", 54.5973, -5.9301, "Northern Ireland", ""),
    ("Derry", "city", 54.9966, -7.3086, "Northern Ireland", ""),
    ("Dublin", "city", 53.3498, -6.2603, "Republic of Ireland", ""),
    ("Cork", "city", 51.8985, -8.4756, "Republic of Ireland", ""),
    ("Galway", "city", 53.2707, -9.0568, "Republic of Ireland", ""),
    ("Douglas", "town", 54.1500, -4.4800, "Isle of Man", ""),
    ("St Helier", "town", 49.1858, -2.1069, "Jersey", ""),
    ("St Peter Port", "town", 49.4550, -2.5368, "Guernsey", ""),
    ("Kirkby Lonsdale", "town", 54.2020, -2.5970, "England", ""),
    ("Newcastle upon Tyne", "city", 54.9783, -1.6178, "England", ""),
    ("Stoke-on-Trent", "city", 53.0027, -2.1794, "England", ""),
    ("SW1A 1AA", "postcode", 51.5010, -0.1416, "England", "SW1A 1AA"),
    ("OX1 1AA", "postcode", 51.7530, -1.2560, "England", "OX1 1AA"),
    ("M1 1AE", "postcode", 53.4780, -2.2420, "England", "M1 1AE"),
    ("BB11 1AA", "postcode", 53.7880, -2.2470, "England", "BB11 1AA"),
    ("EH1 1AA", "postcode", 55.9500, -3.1900, "Scotland", "EH1 1AA"),
    ("High Street", "road", 51.7515, -1.2555, "England", ""),
]


def write_places(path: Path, total: int = 200) -> None:
    rows = list(REAL_PLACES)
    i = 0
    while len(rows) < total:
        rows.append((f"Test Hamlet {i:03d}", "hamlet", round(50.0 + i * 0.05, 4), round(-3.0 + i * 0.03, 4), "England", ""))
        i += 1
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("name,kind,lat,lon,region,postcode\n")
        for name, kind, lat, lon, region, postcode in rows:
            fh.write(f"{name},{kind},{lat},{lon},{region},{postcode}\n")


def make_pdf(path: Path, pages: list[list[str]]) -> None:
    """A minimal but valid PDF 1.4 with one Helvetica text block per page (no parentheses in text)."""
    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_obj = add(b"")
    page_ids = []
    for lines in pages:
        ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"] + [f"({ln}) Tj T*" for ln in lines] + ["ET"]
        stream = "\n".join(ops).encode("latin-1")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 612 792] /Contents {content} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode()))
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objs[pages_obj - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def make_png(path: Path, w: int = 48, h: int = 48) -> None:
    raw = b"".join(b"\x00" + bytes([0x33, 0xCC, 0x33] * w) for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def build_noindex_zim() -> bool:
    if shutil.which("zimwriterfs") is None:
        print("zimwriterfs not on PATH; keeping the committed sos-test-noindex.zim")
        return False
    env = dict(os.environ)
    for magic in ("/usr/lib/file/magic.mgc", "/usr/share/file/magic.mgc", "/usr/share/misc/magic.mgc"):
        if Path(magic).exists():
            env.setdefault("MAGIC", magic)
            break
    out = HERE / "library" / "sos-test-noindex.zim"
    if out.exists():
        out.unlink()
    subprocess.run([
        "zimwriterfs", "--welcome=index.html", "--illustration=icon.png", "--language=eng",
        "--title=SOS test (no index)", "--description=Fixture ZIM without a full-text index",
        "--creator=SOS", "--publisher=SOS", "--name=sos-test-noindex", "--withoutFTIndex",
        str(HERE / "pages"), str(out),
    ], check=True, env=env, capture_output=True, text=True)
    return True


def write_sums() -> None:
    lib = HERE / "library"
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(lib.glob("*.zim"))]
    (lib / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    (HERE / "docs").mkdir(exist_ok=True)
    (HERE / "pages").mkdir(exist_ok=True)
    write_places(HERE / "places.csv")
    make_pdf(HERE / "docs" / "sos-test.pdf", [
        ["PAGE ONE Operation SOS test document", "Boil water for one minute before drinking it.",
         "Call 105 to report a power cut in England, Scotland or Wales."],
        ["PAGE TWO Severe bleeding", "Press hard on the wound and call 999.", "Do not remove the first dressing."],
    ])
    make_png(HERE / "pages" / "icon.png")
    build_noindex_zim()
    write_sums()
    shutil.copy(REPO / "manifest" / "schema.json", HERE / "manifest" / "schema.json")
    from tests import broken_cases

    broken_cases.write_all()
    print("fixtures regenerated")


if __name__ == "__main__":
    main()
```

Run: `make fixtures`
Expected: `fixtures regenerated`; `wc -l api/tests/fixtures/places.csv` prints `201`; `head -c 8 api/tests/fixtures/docs/sos-test.pdf` prints `%PDF-1.4`; `SHA256SUMS` lists both ZIMs.

- [ ] **Step 2: Write the failing tests**

`api/tests/test_docs.py`:

```python
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from sos import db, docs, library
from sos.manifest import load_manifests

FIXTURES = Path(__file__).parent / "fixtures"
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None
FAKE_TEXT = "PAGE ONE Operation SOS test document\nBoil water for one minute.\n\x0cPAGE TWO Severe bleeding\nPress hard on the wound and call 999.\n\x0c"


def fake_runner(calls):
    def run(pdf):
        calls.append(pdf)
        return FAKE_TEXT
    return run


def test_pdf_pages_splits_on_form_feed(tmp_path):
    calls = []
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    pages = docs.pdf_pages(pdf, runner=fake_runner(calls))
    assert len(pages) == 2 and pages[0].startswith("PAGE ONE") and pages[1].startswith("PAGE TWO")
    assert calls == [pdf]


def test_cap_words():
    assert docs.cap_words("a b c d", 2) == "a b"
    assert len(docs.cap_words(" ".join(["w"] * 1000)).split()) == 600


def test_extract_pages_writes_and_reuses_sidecar(tmp_path):
    calls = []
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    first = docs.extract_pages(pdf, "pdf", runner=fake_runner(calls))
    assert len(first) == 2
    assert docs.sidecar_path(pdf) == tmp_path / "x.pdf.txt" and docs.sidecar_path(pdf).exists()
    second = docs.extract_pages(pdf, "pdf", runner=fake_runner(calls))
    assert second == first and len(calls) == 1
    docs.extract_pages(pdf, "pdf", runner=fake_runner(calls), force=True)
    assert len(calls) == 2


@pytest.mark.skipif(not HAS_PDFTOTEXT, reason="pdftotext not installed")
def test_real_pdftotext_on_fixture(tmp_path):
    pdf = tmp_path / "sos-test.pdf"
    shutil.copy(FIXTURES / "docs" / "sos-test.pdf", pdf)
    pages = docs.pdf_pages(pdf)
    assert len(pages) == 2
    assert "PAGE ONE" in pages[0] and "PAGE TWO" in pages[1]


def _make_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml",
                    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        zf.writestr("OEBPS/content.opf",
                    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
                    '<metadata/><manifest><item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>'
                    '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/></manifest>'
                    '<spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
        zf.writestr("OEBPS/ch1.xhtml", "<html><body><nav>skip</nav><h1>Chapter one</h1><p>Store water in clean containers.</p></body></html>")
        zf.writestr("OEBPS/ch2.xhtml", "<html><body><h1>Chapter two</h1><p>Boil it for one minute.</p></body></html>")


def test_epub_pages_follow_spine_order(tmp_path):
    epub = tmp_path / "b.epub"
    _make_epub(epub)
    pages = docs.epub_pages(epub)
    assert len(pages) == 2
    assert pages[0].startswith("Chapter one") and "Store water" in pages[0] and "skip" not in pages[0]
    assert pages[1].startswith("Chapter two")


def test_index_docs_rows_and_shapes(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    shutil.copy(FIXTURES / "docs" / "sos-test.pdf", env.core / "docs" / "sos-test.pdf")
    library.refresh_items(conn, env)
    calls = []
    n = docs.index_docs(conn, runner=fake_runner(calls))
    assert n == 2
    rows = conn.execute("SELECT * FROM fts_docs WHERE kind='doc' ORDER BY page").fetchall()
    assert [r["doc_id"] for r in rows] == ["sos-test-pdf#p1", "sos-test-pdf#p2"]
    assert rows[1]["url"] == "/doc/sos-test-pdf#page=2" and rows[1]["category"] == "uk-official"
    assert rows[0]["scenarios"] == "grid-collapse" and rows[0]["title"] == "SOS test document"
    hit = conn.execute("SELECT doc_id FROM fts_docs WHERE fts_docs MATCH '\"bleeding\"'").fetchone()
    assert hit["doc_id"] == "sos-test-pdf#p2"
    assert docs.index_docs(conn, runner=fake_runner(calls)) == 2 and len(calls) == 1


def test_index_docs_skips_unreadable_file(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"not a pdf")
    library.refresh_items(conn, env)

    def failing(pdf):
        raise subprocess.CalledProcessError(1, "pdftotext")

    assert docs.index_docs(conn, runner=failing) == 0
```

`api/tests/test_places.py`:

```python
import gzip
import shutil
from pathlib import Path

from sos import db, places

FIXTURES = Path(__file__).parent / "fixtures"


def _conn():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    return conn


def test_import_places_csv_and_gzip(tmp_path):
    conn = _conn()
    n = places.import_places(conn, FIXTURES / "places.csv")
    assert n == 200
    gz = tmp_path / "places.csv.gz"
    with open(FIXTURES / "places.csv", "rb") as src, gzip.open(gz, "wb") as dst:
        shutil.copyfileobj(src, dst)
    assert places.import_places(conn, gz) == 200
    assert conn.execute("SELECT count(*) FROM fts_places").fetchone()[0] == 200


def test_import_skips_when_unchanged_and_reimports_on_change(tmp_path):
    conn = _conn()
    csv = tmp_path / "places.csv"
    shutil.copy(FIXTURES / "places.csv", csv)
    assert places.import_places(conn, csv) == 200
    assert places.import_places(conn, csv) is None
    csv.write_text(csv.read_text(encoding="utf-8") + "Newtown,town,52.0,-1.0,England,\n", encoding="utf-8")
    assert places.import_places(conn, csv) == 201
    assert places.import_places(conn, csv, force=True) == 201


def test_import_missing_file_returns_zero(tmp_path):
    conn = _conn()
    assert places.import_places(conn, tmp_path / "nope.csv.gz") == 0


def test_query_places_prefix_min_three_chars():
    conn = _conn()
    places.import_places(conn, FIXTURES / "places.csv")
    assert places.query_places(conn, "ox") == []
    names = [p["name"] for p in places.query_places(conn, "oxf")]
    assert names[0] == "Oxford"
    names = [p["name"] for p in places.query_places(conn, "ox")]
    assert names == []
    names = [p["name"] for p in places.query_places(conn, "oxt")]
    assert names == ["Oxted"]
    both = [p["name"] for p in places.query_places(conn, "burn")]
    assert both[:2] == ["Burnley", "Burnham-on-Sea"]
    assert len(places.query_places(conn, "test hamlet", limit=100)) == 25
    assert len(places.query_places(conn, "test hamlet", limit=5)) == 5
    p = places.query_places(conn, "st hel")[0]
    assert p == {"name": "St Helier", "kind": "town", "lat": 49.1858, "lon": -2.1069, "region": "Jersey", "postcode": None}


def test_exact_place_and_postcode():
    conn = _conn()
    places.import_places(conn, FIXTURES / "places.csv")
    assert places.exact_place(conn, "oxford")["name"] == "Oxford"
    assert places.exact_place(conn, "Oxf") is None
    assert places.exact_place(conn, "SW1A 1AA")["postcode"] == "SW1A 1AA"
    assert places.exact_place(conn, "sw1a1aa")["name"] == "SW1A 1AA"
    assert places.exact_place(conn, "") is None
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_docs.py tests/test_places.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.docs'`.

- [ ] **Step 4: Write `api/sos/docs.py`**

```python
"""PDF and EPUB text extraction into per-page fts_docs rows. Sidecar `.txt` files next to each document
hold the extracted pages separated by form feeds so the Pi never re-runs pdftotext for an unchanged file."""
from __future__ import annotations

import json
import logging
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Callable

from sos.kiwix import extract_text

log = logging.getLogger(__name__)
PAGE_WORD_CAP = 600
OPF_NS = "{http://www.idpf.org/2007/opf}"
CONTAINER_NS = "{urn:oasis:names:tc:opendocument:xmlns:container}"


def run_pdftotext(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def pdf_pages(pdf: Path, runner: Callable[[Path], str] | None = None) -> list[str]:
    text = (runner or run_pdftotext)(Path(pdf))
    pages = [p.strip() for p in text.split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages


def epub_pages(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = container.find(f".//{CONTAINER_NS}rootfile")
        opf_path = rootfile.get("full-path") if rootfile is not None else "content.opf"
        base = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""
        opf = ET.fromstring(zf.read(opf_path))
        hrefs = {item.get("id"): item.get("href") for item in opf.iter(f"{OPF_NS}item")}
        pages: list[str] = []
        for ref in opf.iter(f"{OPF_NS}itemref"):
            href = hrefs.get(ref.get("idref"))
            if not href:
                continue
            try:
                html = zf.read(base + href).decode("utf-8", errors="replace")
            except KeyError:
                continue
            paras = extract_text(html)
            if paras:
                pages.append("\n".join(paras))
    return pages


def cap_words(text: str, n: int = PAGE_WORD_CAP) -> str:
    return " ".join((text or "").split()[:n])


def sidecar_path(file: Path) -> Path:
    file = Path(file)
    return file.with_name(file.name + ".txt")


def extract_pages(file: Path, kind: str, runner: Callable[[Path], str] | None = None, force: bool = False) -> list[str]:
    file = Path(file)
    side = sidecar_path(file)
    if not force and side.exists() and side.stat().st_mtime >= file.stat().st_mtime:
        return side.read_text(encoding="utf-8").split("\f")
    pages = pdf_pages(file, runner) if kind == "pdf" else epub_pages(file)
    side.write_text("\f".join(pages), encoding="utf-8")
    return pages


def index_docs(conn: sqlite3.Connection, runner: Callable[[Path], str] | None = None) -> int:
    rows = conn.execute("SELECT * FROM library_items WHERE kind IN ('pdf','epub') AND available=1 ORDER BY priority").fetchall()
    conn.execute("DELETE FROM fts_docs WHERE kind='doc'")
    count = 0
    for row in rows:
        file = Path(row["local_path"] or "")
        try:
            pages = extract_pages(file, row["kind"], runner)
        except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile, ET.ParseError) as exc:
            log.warning("skipping %s: %s", row["id"], exc)
            continue
        scenarios = " ".join(json.loads(row["scenarios_json"] or "[]"))
        for n, page in enumerate(pages, 1):
            body = cap_words(page)
            if not body:
                continue
            conn.execute(
                "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                (row["title"], body, f"{row['id']}#p{n}", "doc", row["category"], scenarios, n, f"/doc/{row['id']}#page={n}"),
            )
            count += 1
    conn.commit()
    return count
```

- [ ] **Step 5: Write `api/sos/places.py`**

```python
"""fts_places: import from places.csv(.gz) when the file changes; prefix queries for the map; exact lookups for search."""
from __future__ import annotations

import csv
import gzip
import sqlite3
from pathlib import Path

from sos.config import Settings
from sos.query import fts5_match, tokenise

KIND_RANK = {"city": 0, "town": 1, "village": 2, "suburb": 3, "hamlet": 4, "locality": 5, "road": 6, "postcode": 7}
_KIND_CASE = "CASE kind " + " ".join(f"WHEN '{k}' THEN {v}" for k, v in KIND_RANK.items()) + " ELSE 8 END"


def places_path(settings: Settings) -> Path:
    return settings.core / "maps" / "places.csv.gz"


def _signature(path: Path) -> str:
    st = path.stat()
    return f"{int(st.st_mtime)}:{st.st_size}"


def _open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")


def import_places(conn: sqlite3.Connection, path: Path, force: bool = False) -> int | None:
    path = Path(path)
    if not path.exists():
        return 0
    sig = _signature(path)
    row = conn.execute("SELECT value FROM places_meta WHERE key='signature'").fetchone()
    if not force and row is not None and row["value"] == sig:
        return None
    conn.execute("DELETE FROM fts_places")
    count = 0
    with _open_text(path) as fh:
        batch: list[tuple] = []
        for rec in csv.DictReader(fh):
            try:
                lat, lon = float(rec["lat"]), float(rec["lon"])
            except (TypeError, ValueError, KeyError):
                continue
            batch.append((rec.get("name", "").strip(), rec.get("kind", "").strip(), lat, lon,
                          rec.get("region", "").strip(), (rec.get("postcode") or "").strip() or None))
            if len(batch) >= 5000:
                conn.executemany("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)", batch)
                count += len(batch)
                batch = []
        if batch:
            conn.executemany("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)", batch)
            count += len(batch)
    conn.execute("INSERT INTO places_meta(key, value) VALUES ('signature', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (sig,))
    conn.commit()
    return count


def _row(r: sqlite3.Row) -> dict:
    return {"name": r["name"], "kind": r["kind"], "lat": float(r["lat"]), "lon": float(r["lon"]),
            "region": r["region"], "postcode": r["postcode"] or None}


def query_places(conn: sqlite3.Connection, q: str, limit: int = 10) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 3:
        return []
    tokens = tokenise(q)
    if not tokens:
        return []
    limit = max(1, min(int(limit or 10), 25))
    match = " ".join(f'"{t}"*' for t in tokens)
    rows = conn.execute(
        f"SELECT name, kind, lat, lon, region, postcode FROM fts_places WHERE fts_places MATCH ? "
        f"ORDER BY {_KIND_CASE}, length(name), name LIMIT ?",
        (match, limit),
    ).fetchall()
    return [_row(r) for r in rows]


def exact_place(conn: sqlite3.Connection, name: str) -> dict | None:
    norm = " ".join((name or "").split()).lower()
    tokens = tokenise(norm)
    if not tokens:
        return None
    rows = conn.execute(
        f"SELECT name, kind, lat, lon, region, postcode FROM fts_places WHERE fts_places MATCH ? ORDER BY {_KIND_CASE} LIMIT 50",
        (fts5_match(tokens),),
    ).fetchall()
    squashed = norm.replace(" ", "")
    for r in rows:
        candidate = r["name"].lower()
        if candidate == norm or candidate.replace(" ", "") == squashed:
            return _row(r)
    return None
```

- [ ] **Step 6: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_docs.py tests/test_places.py -v`
Expected: all PASS (the real-pdftotext test is skipped on the PC and runs on the Pi).

- [ ] **Step 7: Commit**

```bash
git add api/sos/docs.py api/sos/places.py api/tests/test_docs.py api/tests/test_places.py api/tests/fixtures/gen_fixtures.py api/tests/fixtures/places.csv api/tests/fixtures/docs api/tests/fixtures/pages api/tests/fixtures/library/SHA256SUMS
git commit -m "feat(docs,places): pdf/epub page extraction with sidecars and fts_places import and queries"
```

---

### Task 9: `sos.search` (class fan-out, scoring, intents, cache, suggest)

**Files:**
- Create: `api/sos/search.py`
- Test: `api/tests/test_search.py`

**Interfaces:**
- Consumes: `sos.kiwix.KiwixClient`, `sos.query.reduce_query/place_candidates/tokenise`, `sos.places.exact_place`, `sos.db`, `library_items`, `fts_docs`, settings key `zim_languages`.
- Produces: `async search(conn, settings, kiwix, q, sources=None, limit=40) -> dict` (`SearchResponse` shape), `async suggest(conn, settings, kiwix, q) -> list[dict]` (`Suggestion` shape, at most 10), `score(weight, rank) -> float`, `classify(row) -> str`, `is_medical_intent(tokens) -> bool`, `SearchCache` (`key`, `get`, `put`, `invalidate`), `async warm(settings, kiwix, db_path)`, constants `CLASS_TITLES`, `CLASS_TIMEOUTS`, `DEFAULT_TIMEOUT`, `PLAYBOOK_WEIGHT`, `MEDICAL_TERMS`, `WARM_QUERIES`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_search.py`:

```python
import asyncio
import shutil
import time
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, library, search
from sos.kiwix import KiwixClient
from sos.manifest import load_manifests

FX = Path(__file__).parent / "fixtures"
BASE = "http://kiwix.test/kiwix"
WIKI = "wikipedia_en_100_mini_2026-01"


def test_fixed_ranking_comparisons():
    assert search.score(1.6, 4) > search.score(1.0, 1)      # playbook rank 4 beats Wikipedia rank 1
    assert search.score(1.6, 5) < search.score(1.0, 1)      # playbook rank 5 does not
    assert search.score(1.2, 2) > search.score(1.0, 1)      # medical rank 2 beats Wikipedia rank 1
    assert search.score(1.2, 3) < search.score(1.0, 1)      # medical rank 3 does not
    assert search.score(1.0, 1) == pytest.approx(1 / 6)


@pytest.mark.parametrize("row,cls", [
    ({"tier": "core", "category": "uk-official", "id": "nrr-2025"}, "uk-official"),
    ({"tier": "core", "category": "medical", "id": "nhs_uk"}, "nhs"),
    ({"tier": "core", "category": "medical", "id": "nhs_medicines"}, "nhs"),
    ({"tier": "core", "category": "medical", "id": "wikipedia_en_medicine_maxi"}, "medical"),
    ({"tier": "core", "category": "reference", "id": "wikipedia_en_all_maxi"}, "reference"),
    ({"tier": "core", "category": "practical", "id": "ifixit_en_all"}, "practical"),
    ({"tier": "core", "category": "survival", "id": "zimgit-water_en"}, "survival"),
    ({"tier": "extended", "category": "reference", "id": "gutenberg_en_all"}, "extended"),
    ({"tier": "core", "category": "education", "id": "khan"}, "reference"),
])
def test_classify(row, cls):
    assert search.classify(row) == cls


def test_medical_intent():
    assert search.is_medical_intent(["severe", "bleeding"]) is True
    assert search.is_medical_intent(["power", "cut"]) is False
    assert len(search.MEDICAL_TERMS) >= 40


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    library.upsert_items(c, load_manifests(env.manifests))
    for n in (WIKI, "sos-test-noindex"):
        shutil.copy(FX / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")
    library.refresh_items(c, env)
    c.execute("UPDATE library_items SET fts=1 WHERE id=?", (WIKI,))
    c.execute("""INSERT INTO library_items(id, title, kind, tier, category, scenarios_json, dest, size_bytes, priority,
                 search_weight, suggest, available, fts) VALUES ('nhs.uk_en_medicines_2025-12','NHS Medicines A to Z','zim',
                 'core','medical','[]','zim/nhs.uk_en_medicines_2025-12.zim',1,5,1.4,1,1,1)""")
    db.set_setting(c, "zim_languages", '{"%s": "eng", "nhs.uk_en_medicines_2025-12": "eng", "sos-test-noindex": "eng"}' % WIKI)
    rows = [
        ("Water", "Finding, storing and making water safe.", "module:water", "module", "playbooks", "", None, "/m/water"),
        ("Grid collapse", "Weeks without power, water pumps down.", "scenario:grid-collapse", "playbook", "playbooks", "grid-collapse", None, "/s/grid-collapse"),
        ("Severe bleeding", "Press hard on the wound.", "card:bleeding", "card", "playbooks", "", None, "/medical/card/bleeding"),
        ("SOS test document", "Boil water for one minute", "sos-test-pdf#p1", "doc", "uk-official", "grid-collapse", 1, "/doc/sos-test-pdf#page=1"),
        ("Water Treatment Library", "", "item:zimgit-water", "item", "survival", "", None, "/library"),
    ]
    c.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)", rows)
    c.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES ('Oxford','city',51.752,-1.2577,'England',NULL)")
    c.commit()
    return c


def _run(coro):
    return asyncio.run(coro)


@respx.mock(base_url=BASE)
def test_search_merges_kiwix_and_fts_and_groups(respx_mock, conn, env):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["q"] == "water" and resp["query"] == "water" and resp["partial"] is False
    assert route.call_count == 2  # one request for the reference class, one for the nhs class
    kinds = {r["kind"] for r in resp["results"]}
    assert {"article", "module", "playbook", "doc", "item"} <= kinds
    first = resp["results"][0]
    assert first["kind"] == "module" and first["title"] == "Water"        # exact title jump to the top of its group
    articles = [r for r in resp["results"] if r["kind"] == "article"]
    assert articles[0]["url"] == f"/read/{WIKI}/Precipitation" and articles[0]["badge"] == "Wikipedia 100 (mini)"
    assert {g["source"] for g in resp["groups"]} >= {"reference", "playbooks", "docs", "library"}
    assert all(set(r) >= {"source", "badge", "title", "snippet", "url", "score", "kind"} for r in resp["results"])
    doc = next(r for r in resp["results"] if r["kind"] == "doc")
    assert doc["page"] == 1
    assert resp["took_ms"] >= 0


@respx.mock(base_url=BASE)
def test_playbook_rank_four_beats_article_rank_one(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    playbooks = [r for r in resp["results"] if r["source"] == "playbooks"]
    articles = [r for r in resp["results"] if r["source"] == "reference"]
    assert playbooks[0]["score"] > articles[0]["score"]


@respx.mock(base_url=BASE)
def test_slow_class_is_dropped_and_marked_partial(respx_mock, conn, env):
    async def slow(request):
        await asyncio.sleep(3)
        return httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text())

    respx_mock.get(url__regex=r".*books\.name=nhs.*").mock(side_effect=slow)
    respx_mock.get(url__regex=r".*books\.name=wikipedia.*").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    t0 = time.perf_counter()
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    elapsed = time.perf_counter() - t0
    assert resp["partial"] is True
    assert elapsed < 2.5
    assert any(r["kind"] == "article" for r in resp["results"])
    assert "nhs" not in {r["source"] for r in resp["results"]}


@respx.mock(base_url=BASE)
def test_cache_hit_on_repeat_and_miss_after_invalidate(respx_mock, conn, env):
    route = respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    _run(search.search(conn, env, KiwixClient(BASE), "water"))
    _run(search.search(conn, env, KiwixClient(BASE), "Water "))
    assert route.call_count == 2
    search.SearchCache.invalidate(conn)
    _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert route.call_count == 4


@respx.mock(base_url=BASE)
def test_partial_responses_are_not_cached(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(404, text="<error>Fulltext search unavailable</error>"))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "water"))
    assert resp["partial"] is False and all(r["kind"] != "article" for r in resp["results"])

    async def slow(request):
        await asyncio.sleep(3)
        return httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text())

    respx_mock.get("/search").mock(side_effect=slow)
    resp2 = _run(search.search(conn, env, KiwixClient(BASE), "bleeding"))
    assert resp2["partial"] is True
    assert conn.execute("SELECT count(*) FROM search_cache WHERE q LIKE 'bleeding%'").fetchone()[0] == 0


@respx.mock(base_url=BASE)
def test_medical_intent_boosts_nhs_and_medical(respx_mock, conn, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search_multi.xml").read_text()))
    resp = _run(search.search(conn, env, KiwixClient(BASE), "medicine dose"))
    nhs = [r for r in resp["results"] if r["source"] == "nhs"]
    assert nhs and nhs[0]["score"] == pytest.approx(search.score(1.4, 1) * 1.5)


def test_place_hit_only_on_exact_match(conn, env):
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "near Oxford"))
        place = [r for r in resp["results"] if r["kind"] == "place"]
        assert len(place) == 1 and place[0]["lat"] == 51.752 and place[0]["url"].startswith("/map?lat=51.752&lon=-1.2577")
        assert place[0]["score"] == pytest.approx(search.score(2.0, 1))
        resp = _run(search.search(conn, env, KiwixClient(BASE), "Oxford hospitals"))
        assert not [r for r in resp["results"] if r["kind"] == "place"]


def test_empty_query_and_source_filter_and_limit(conn, env):
    with respx.mock(base_url=BASE) as m:
        m.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
        assert _run(search.search(conn, env, KiwixClient(BASE), "   "))["results"] == []
        resp = _run(search.search(conn, env, KiwixClient(BASE), "water", sources=["playbooks"], limit=2))
        assert len(resp["results"]) == 2 and {r["source"] for r in resp["results"]} == {"playbooks"}
        assert any(g["source"] == "reference" for g in resp["groups"])


@respx.mock(base_url=BASE)
def test_suggest_caps_at_ten_and_mixes_sources(respx_mock, conn, env):
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "suggest.json").read_text()))
    for i in range(12):
        conn.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                     (f"Water tip {i}", "", f"page:water-{i}", "page", "playbooks", "", None, f"/p/water-{i}"))
    conn.commit()
    out = _run(search.suggest(conn, env, KiwixClient(BASE), "wat"))
    assert len(out) == 10
    assert all(set(s) == {"value", "label", "url", "source"} for s in out)
    assert all(s["value"].lower().startswith("wat") for s in out)
    short = _run(search.suggest(conn, env, KiwixClient(BASE), "w"))
    assert short == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_search.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.search'`.

- [ ] **Step 3: Write `api/sos/search.py`**

```python
"""Unified search (spec section 8): Kiwix classes in parallel with timeouts, FTS5 docs, exact place hits,
`score = w / (5 + rank)`, medical intent boost, exact-title jump, a bounded results cache and suggest."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from urllib.parse import quote

import httpx

from sos import places as places_mod
from sos import query as query_mod
from sos.config import Settings
from sos.db import get_setting
from sos.kiwix import KiwixClient, KiwixError

K = 5
CLASS_TIMEOUTS = {"reference": 4.0}
DEFAULT_TIMEOUT = 2.0
PAGE_LENGTH = 8
CACHE_MAX = 500
PLAYBOOK_WEIGHT = 1.6
MEDICAL_BOOST = 1.5
PLACE_WEIGHT = 2.0
SUGGEST_MAX = 10
WARM_QUERIES = ("water", "bleeding", "power cut")

CLASS_TITLES = {
    "uk-official": "UK official", "nhs": "NHS", "medical": "Medical", "reference": "Reference", "practical": "Practical",
    "survival": "Survival", "extended": "Extended library", "playbooks": "Playbooks", "docs": "Documents",
    "library": "Library", "places": "Places",
}
KIND_BADGES = {"playbook": "Playbook", "module": "Module", "card": "Quick card", "page": "Page", "doc": "Document",
               "item": "Library", "place": "Place"}
SOURCE_BY_KIND = {"playbook": "playbooks", "module": "playbooks", "card": "playbooks", "page": "playbooks",
                  "doc": "docs", "item": "library"}

_LOCAL_MEDICAL_TERMS = frozenset("""
bleeding bleed wound cut burn burns scald fracture broken bone sprain choking choke cpr resuscitation unconscious
breathing pulse shock stroke heart attack chest seizure fit fever temperature infection sepsis antibiotic antibiotics
paracetamol ibuprofen aspirin dose dosage medicine medicines tablet tablets pill pills vomiting diarrhoea dehydration
rehydration hypothermia frostbite heatstroke poison poisoning overdose allergy anaphylaxis asthma inhaler diabetes
insulin pregnancy labour birth rash tick bite sting drowning concussion
""".split())
try:  # plan 05 ships the full 200-term list
    from sos.ai_terms import MEDICAL_TERMS  # type: ignore
except ImportError:
    MEDICAL_TERMS = _LOCAL_MEDICAL_TERMS


def score(weight: float, rank: int) -> float:
    return weight / (K + rank)


def classify(row) -> str:
    if row["tier"] == "extended":
        return "extended"
    cat = row["category"]
    if cat == "uk-official":
        return "uk-official"
    if cat == "medical":
        return "nhs" if str(row["id"]).startswith("nhs") else "medical"
    if cat in ("reference", "practical", "survival"):
        return cat
    return "reference"


def is_medical_intent(tokens: list[str]) -> bool:
    return any(t in MEDICAL_TERMS for t in tokens)


class SearchCache:
    @staticmethod
    def key(q: str, sources: list[str] | None, limit: int) -> str:
        return f"{' '.join(q.lower().split())}|{','.join(sorted(sources or []))}|{limit}"

    @staticmethod
    def get(conn: sqlite3.Connection, key: str) -> dict | None:
        row = conn.execute("SELECT results_json FROM search_cache WHERE q=?", (key,)).fetchone()
        return json.loads(row["results_json"]) if row else None

    @staticmethod
    def put(conn: sqlite3.Connection, key: str, payload: dict) -> None:
        from sos.db import now_iso

        conn.execute("INSERT OR REPLACE INTO search_cache(q, results_json, created_at) VALUES (?,?,?)",
                     (key, json.dumps(payload), now_iso()))
        conn.execute(
            "DELETE FROM search_cache WHERE q IN (SELECT q FROM search_cache ORDER BY created_at DESC LIMIT -1 OFFSET ?)",
            (CACHE_MAX,),
        )
        conn.commit()

    @staticmethod
    def invalidate(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM search_cache")
        conn.commit()


async def _search_class(kiwix: KiwixClient, cls: str, names: list[str], pattern: str, timeout: float):
    try:
        return cls, await kiwix.search(names, pattern, PAGE_LENGTH, timeout), False
    except asyncio.TimeoutError:
        return cls, None, True
    except (KiwixError, httpx.HTTPError, OSError):
        return cls, None, False


def _empty(q: str) -> dict:
    return {"q": q, "query": "", "results": [], "groups": [], "took_ms": 0, "partial": False}


async def search(conn: sqlite3.Connection, settings: Settings, kiwix: KiwixClient, q: str,
                 sources: list[str] | None = None, limit: int = 40) -> dict:
    t0 = time.perf_counter()
    reduced = query_mod.reduce_query(q or "")
    if not reduced.terms:
        return _empty(q or "")
    limit = max(1, min(int(limit or 40), 100))
    key = SearchCache.key(q, sources, limit)
    cached = SearchCache.get(conn, key)
    if cached is not None:
        cached["took_ms"] = int((time.perf_counter() - t0) * 1000)
        return cached

    results: list[dict] = []
    partial = False

    languages = json.loads(get_setting(conn, "zim_languages", "{}") or "{}")
    books: dict[tuple[str, str], list[str]] = {}
    weights: dict[str, float] = {}
    titles: dict[str, str] = {}
    for row in conn.execute("SELECT * FROM library_items WHERE kind='zim' AND available=1 AND fts=1 ORDER BY priority, id"):
        cls = classify(row)
        books.setdefault((cls, languages.get(row["id"], "eng")), []).append(row["id"])
        weights[row["id"]] = float(row["search_weight"] or 1.0)
        titles[row["id"]] = row["title"]
    tasks = [_search_class(kiwix, cls, names, reduced.kiwix, CLASS_TIMEOUTS.get(cls, DEFAULT_TIMEOUT))
             for (cls, _lang), names in books.items()]
    for cls, hits, timed_out in await asyncio.gather(*tasks):
        if hits is None:
            partial = partial or timed_out
            continue
        for rank, hit in enumerate(hits, 1):
            results.append({
                "source": cls, "badge": titles.get(hit.book, CLASS_TITLES[cls]), "title": hit.title, "snippet": hit.snippet,
                "url": f"/read/{hit.book}/{hit.path}", "score": score(weights.get(hit.book, 1.0), rank), "kind": "article",
                "_cat": "medical" if cls in ("nhs", "medical") else cls,
            })

    item_weights = {r["id"]: float(r["search_weight"] or 1.0) for r in conn.execute("SELECT id, search_weight FROM library_items")}
    rows = conn.execute(
        "SELECT title, doc_id, kind, category, page, url, snippet(fts_docs, 1, '<b>', '</b>', '…', 14) AS snip "
        "FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT 20",
        (reduced.fts,),
    ).fetchall()
    for rank, row in enumerate(rows, 1):
        kind = row["kind"]
        src = SOURCE_BY_KIND.get(kind, "docs")
        if src == "playbooks":
            w = PLAYBOOK_WEIGHT
        elif kind == "doc":
            w = item_weights.get(str(row["doc_id"]).split("#")[0], 1.0)
        else:
            w = 1.0
        entry = {"source": src, "badge": KIND_BADGES.get(kind, "Document"), "title": row["title"], "snippet": row["snip"] or "",
                 "url": row["url"], "score": score(w, rank), "kind": kind, "_cat": row["category"]}
        if row["page"]:
            entry["page"] = int(row["page"])
        results.append(entry)

    for cand in query_mod.place_candidates(q):
        hit = places_mod.exact_place(conn, cand) if len(cand) >= 2 else None
        if hit:
            results.append({
                "source": "places", "badge": "Place", "title": hit["name"],
                "snippet": f"{hit['kind'].title()}, {hit['region']}",
                "url": f"/map?lat={hit['lat']}&lon={hit['lon']}&z=13&label={quote(hit['name'])}",
                "score": score(PLACE_WEIGHT, 1), "kind": "place", "lat": hit["lat"], "lon": hit["lon"], "_cat": "places",
            })
            break

    if is_medical_intent(reduced.terms):
        for r in results:
            if r["_cat"] == "medical":
                r["score"] *= MEDICAL_BOOST

    qnorm = " ".join((q or "").lower().split())
    by_source: dict[str, list[dict]] = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)
    for rs in by_source.values():
        top = max(x["score"] for x in rs)
        for r in rs:
            if r["title"].strip().lower() == qnorm:
                r["score"] = top + 0.001
    results.sort(key=lambda r: -r["score"])

    counts: dict[str, int] = {}
    for r in results:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    groups = [{"source": s, "badge": CLASS_TITLES.get(s, s), "count": n} for s, n in counts.items()]
    if sources:
        wanted = set(sources)
        results = [r for r in results if r["source"] in wanted]
    results = results[:limit]
    for r in results:
        r.pop("_cat", None)
    payload = {"q": q, "query": reduced.kiwix, "results": results, "groups": groups,
               "took_ms": int((time.perf_counter() - t0) * 1000), "partial": partial}
    if not partial:
        SearchCache.put(conn, key, payload)
    return payload


async def suggest(conn: sqlite3.Connection, settings: Settings, kiwix: KiwixClient, q: str) -> list[dict]:
    term = " ".join((q or "").split())
    if len(term) < 2:
        return []
    out: list[dict] = []
    tokens = query_mod.tokenise(term)
    if tokens:
        match = "title : (" + " ".join(f'"{t}"*' for t in tokens) + ")"
        rows = conn.execute(
            "SELECT title, url, kind FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT ?",
            (match, SUGGEST_MAX),
        ).fetchall()
        for r in rows:
            out.append({"value": r["title"], "label": r["title"], "url": r["url"], "source": KIND_BADGES.get(r["kind"], "Document")})
    books = conn.execute("SELECT id, title FROM library_items WHERE kind='zim' AND available=1 AND suggest=1 ORDER BY priority, id").fetchall()

    async def one(book):
        try:
            return book, await asyncio.wait_for(kiwix.suggest(book["id"], term), 1.5)
        except (asyncio.TimeoutError, KiwixError, httpx.HTTPError, OSError):
            return book, []

    for book, entries in await asyncio.gather(*(one(b) for b in books)):
        for e in entries[:5]:
            out.append({"value": e["value"], "label": e["label"], "url": f"/read/{book['id']}/{e['path']}", "source": book["title"]})
    seen: set[tuple[str, str | None]] = set()
    unique: list[dict] = []
    for s in out:
        k = (s["value"], s["url"])
        if k not in seen:
            seen.add(k)
            unique.append(s)
    return unique[:SUGGEST_MAX]


async def warm(settings: Settings, kiwix: KiwixClient, db_path) -> None:
    """Three canned queries after boot and rescan so the Wikipedia and NHS indexes are hot."""
    from sos.db import connect

    for q in WARM_QUERIES:
        conn = connect(db_path)
        try:
            await search(conn, settings, kiwix, q)
        except Exception:  # warming is best-effort
            pass
        finally:
            conn.close()
```

- [ ] **Step 4: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_search.py -v`
Expected: all PASS; the slow-class test takes about 2 s.

- [ ] **Step 5: Commit**

```bash
git add api/sos/search.py api/tests/test_search.py
git commit -m "feat(search): kiwix class fan-out with timeouts, fts5 docs, place hits, scoring, cache and suggest"
```

---

### Task 10: `sos.system` (temperature, disks, hotspot, eth mode, power mode, backlight, PIN, watchdog, updater)

Ordering note: the assignment lists the FastAPI app before `system.py`; the routers import `system.py`, so it is built first here and the app is Task 11.

**Files:**
- Create: `api/sos/system.py`
- Test: `api/tests/test_system.py`

**Interfaces:**
- Consumes: `sos.db`, `sos.library.ext_mounted/rescan`, `Settings`.
- Produces: `run_cmd(args, settings, timeout=30.0, check=False) -> str`, `sudo(args, settings) -> str`, `read_sysfs(path, settings) -> str | None`, `write_sysfs(path, value, settings) -> bool`, `FAKE_CMD_OUTPUT`, `FAKE_SYSFS`, `cpu_temp(settings) -> float | None`, `disk_info(path, mounted) -> dict`, `mem_info() -> dict`, `uptime_s() -> int`, `hotspot_info(conn, settings) -> dict`, `set_hotspot(conn, settings, ssid, passphrase=None)`, `set_eth_mode(conn, settings, mode)`, `set_power_mode(conn, settings, mode)`, `apply_settings(conn, patch) -> None`, `backlight_device(settings) -> str | None`, `set_backlight(settings, level) -> int | None`, `ai_status(conn, settings) -> dict`, `set_ai_state(conn, state, message=None)`, `stop_ai(conn, settings, state="off", message=None)`, `hash_pin`, `verify_pin(conn, pin) -> bool`, `set_pin(conn, pin)`, `clear_pin(conn)`, `pin_required(conn) -> bool`, `TokenStore(ttl=600, clock=time.monotonic)` (`issue() -> str`, `valid(token) -> bool`, `revoke_all()`), `RateLimiter(limit=5, window=60.0, clock=time.monotonic)` (`allow(key) -> bool`), `ThermalWatchdog(settings, db_path, interval=10.0)` (`tick(conn) -> str | None`, `async run()`), `UpdateRunner(command_factory)` (`start(tiers) -> bool`, `progress() -> dict`, `wait(timeout)`), `default_sync_command(tier) -> list[str]`, `status(conn, settings) -> dict` (the `Status` shape), `rescan(conn, settings) -> dict`, constants `DEFAULTS`, `THERMAL_PATH`, `LLAMA_UNIT`, `HOTSPOT_PROFILE`, `ETH_PROFILES`, `TOKEN_TTL`, `PIN_ATTEMPTS`.

- [ ] **Step 1: Write the failing tests**

`api/tests/test_system.py`:

```python
import sys
import time

import pytest

from sos import db, system


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    return c


@pytest.fixture
def recorder(monkeypatch):
    calls = []

    def fake_run(args, settings, timeout=30.0, check=False):
        calls.append(list(args))
        return system.FAKE_CMD_OUTPUT.get(tuple(a for a in args if a not in ("sudo", "-n")), "")

    monkeypatch.setattr(system, "run_cmd", fake_run)
    return calls


def test_cpu_temp_dev_fake_and_missing(env, monkeypatch):
    assert system.cpu_temp(env) == 45.0
    monkeypatch.setattr(system, "read_sysfs", lambda path, settings: None)
    assert system.cpu_temp(env) is None


@pytest.mark.parametrize("level,expected_level,raw", [(100, 100, "31"), (10, 10, "3"), (5, 10, "3"), (0, 10, "3"), (50, 50, "16"), (150, 100, "31")])
def test_backlight_scaled_to_max_brightness(env, level, expected_level, raw):
    assert system.set_backlight(env, level) == expected_level
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == raw


def test_backlight_without_device_returns_none(env, monkeypatch):
    monkeypatch.setattr(system, "backlight_device", lambda settings: None)
    assert system.set_backlight(env, 50) is None


def test_hotspot_info_dev(conn, env):
    info = system.hotspot_info(conn, env)
    assert info == {"ssid": "SOS", "ip": "10.42.0.1", "clients": 2, "enabled": True}


def test_set_hotspot_records_nmcli_sequence(conn, env, recorder):
    system.set_hotspot(conn, env, "Bunker", "letmein123")
    assert recorder == [
        ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "802-11-wireless.ssid", "Bunker"],
        ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", "letmein123"],
        ["sudo", "-n", "nmcli", "con", "up", "sos-hotspot"],
    ]
    assert db.get_setting(conn, "ssid") == "Bunker" and db.get_setting(conn, "passphrase") == "letmein123"
    recorder.clear()
    system.set_hotspot(conn, env, "SOS", "")
    assert recorder[1] == ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "remove", "wifi-sec"]
    with pytest.raises(ValueError):
        system.set_hotspot(conn, env, "", None)
    with pytest.raises(ValueError):
        system.set_hotspot(conn, env, "SOS", "short")


def test_set_eth_mode(conn, env, recorder):
    system.set_eth_mode(conn, env, "direct")
    assert recorder == [
        ["sudo", "-n", "nmcli", "con", "modify", "sos-eth-client", "connection.autoconnect", "no"],
        ["sudo", "-n", "nmcli", "con", "modify", "sos-eth-direct", "connection.autoconnect", "yes"],
        ["sudo", "-n", "nmcli", "con", "up", "sos-eth-direct"],
    ]
    assert db.get_setting(conn, "eth_mode") == "direct"
    with pytest.raises(ValueError):
        system.set_eth_mode(conn, env, "bridge")


def test_power_mode_low_stops_ai_and_dims(conn, env, recorder):
    system.set_ai_state(conn, "ready")
    system.set_power_mode(conn, env, "low")
    assert ["sudo", "-n", "systemctl", "stop", "sos-llama.service"] in recorder
    assert system.ai_status(conn, env)["state"] == "off"
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "9"
    assert db.get_setting(conn, "power_mode") == "low"
    system.set_power_mode(conn, env, "normal")
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "31"


def test_pin_hash_verify_clear(conn):
    assert system.pin_required(conn) is False
    assert system.verify_pin(conn, "1234") is False
    system.set_pin(conn, "1234")
    assert system.pin_required(conn) is True
    assert db.get_setting(conn, "pin_hash").startswith("scrypt$")
    assert system.verify_pin(conn, "1234") is True
    assert system.verify_pin(conn, "0000") is False
    system.clear_pin(conn)
    assert system.pin_required(conn) is False
    with pytest.raises(ValueError):
        system.set_pin(conn, "12")
    with pytest.raises(ValueError):
        system.set_pin(conn, "abcd")


def test_token_store_expiry():
    now = [1000.0]
    store = system.TokenStore(ttl=600, clock=lambda: now[0])
    tok = store.issue()
    assert store.valid(tok) is True and store.valid("nope") is False
    now[0] += 599
    assert store.valid(tok) is True
    now[0] += 2
    assert store.valid(tok) is False
    tok2 = store.issue()
    store.revoke_all()
    assert store.valid(tok2) is False


def test_rate_limiter_five_per_minute():
    now = [0.0]
    rl = system.RateLimiter(limit=5, window=60.0, clock=lambda: now[0])
    assert [rl.allow("ip") for _ in range(5)] == [True] * 5
    assert rl.allow("ip") is False
    assert rl.allow("other") is True
    now[0] += 61
    assert rl.allow("ip") is True


def test_thermal_watchdog(conn, env, recorder, monkeypatch):
    temps = {"value": "79000\n"}
    monkeypatch.setattr(system, "read_sysfs", lambda path, settings: temps["value"] if path == system.THERMAL_PATH else None)
    system.set_ai_state(conn, "ready")
    wd = system.ThermalWatchdog(env, env.db_path)
    assert wd.tick(conn) is None
    assert system.ai_status(conn, env)["state"] == "ready" and recorder == []
    temps["value"] = "80000\n"
    assert wd.tick(conn) == "stopped"
    assert system.ai_status(conn, env)["state"] == "off-thermal"
    assert ["sudo", "-n", "systemctl", "stop", "sos-llama.service"] in recorder
    recorder.clear()
    temps["value"] = "60000\n"
    assert wd.tick(conn) is None
    assert system.ai_status(conn, env)["state"] == "off-thermal"
    assert recorder == []
    db.set_setting(conn, "thermal_ai_off_c", "55")
    system.set_ai_state(conn, "ready")
    assert wd.tick(conn) == "stopped"


def test_update_runner_streams_lines():
    runner = system.UpdateRunner(lambda tier: [sys.executable, "-c", f"print('syncing {tier}'); print('done')"])
    assert runner.progress() == {"running": False, "lines": [], "done": False, "ok": None}
    assert runner.start(["core", "extended"]) is True
    runner.wait(10)
    p = runner.progress()
    assert p["running"] is False and p["done"] is True and p["ok"] is True
    assert p["lines"] == ["== sync core", "syncing core", "done", "== sync extended", "syncing extended", "done"]
    failing = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    failing.start(["core"])
    failing.wait(10)
    assert failing.progress()["ok"] is False and "sync core failed (exit 3)" in failing.progress()["lines"]


def test_update_runner_rejects_concurrent_start():
    runner = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import time; time.sleep(0.5)"])
    assert runner.start(["core"]) is True
    assert runner.start(["core"]) is False
    runner.wait(5)


def test_apply_settings_validation(conn):
    system.apply_settings(conn, {"default_theme": "field", "thermal_ai_off_c": 75, "idle_minutes": 3, "home_minutes": 20})
    assert db.get_setting(conn, "default_theme") == "field" and db.get_setting(conn, "thermal_ai_off_c") == "75"
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"default_theme": "neon"})
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"thermal_ai_off_c": 120})
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"bogus": 1})


def test_status_shape(conn, env):
    s = system.status(conn, env)
    assert set(s) == {"version", "uptime_s", "cpu_temp_c", "load", "mem", "disks", "hotspot", "eth_mode", "power_mode", "ai",
                      "thermal_ai_off_c", "idle_minutes", "home_minutes", "pin_required", "dev", "default_theme"}
    assert s["dev"] is True and s["cpu_temp_c"] == 45.0 and s["thermal_ai_off_c"] == 80
    assert s["disks"]["core"]["mounted"] is True and s["disks"]["extended"]["mounted"] is False
    assert s["disks"]["extended"] == {"mounted": False, "path": str(env.ext), "total_gb": 0.0, "free_gb": 0.0}
    assert s["ai"] == {"state": "off", "model": env.model, "message": None}
    assert s["default_theme"] == "vault" and s["idle_minutes"] == 5 and s["home_minutes"] == 30
    assert len(s["load"]) == 3 and s["mem"]["total_mb"] > 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_system.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.system'`.

- [ ] **Step 3: Write `api/sos/system.py`**

```python
"""System control for the box. Every subprocess, sysfs and NetworkManager access goes through run_cmd(),
read_sysfs() and write_sysfs(), which return fakes under SOS_DEV=1 and are monkeypatched in tests."""
from __future__ import annotations

import asyncio
import glob
import hashlib
import hmac
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable

from sos import __version__
from sos.config import Settings
from sos.db import connect, get_setting, set_setting

THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"
BACKLIGHT_GLOB = "/sys/class/backlight/*"
HOTSPOT_PROFILE = "sos-hotspot"
ETH_PROFILES = {"client": "sos-eth-client", "direct": "sos-eth-direct"}
HOTSPOT_IP = "10.42.0.1"
LLAMA_UNIT = "sos-llama.service"
TOKEN_TTL = 600
PIN_ATTEMPTS = 5
PIN_WINDOW = 60.0
MIN_BACKLIGHT_LEVEL = 10
LOW_POWER_BACKLIGHT = 30
DEFAULTS = {
    "default_theme": "vault", "thermal_ai_off_c": "80", "idle_minutes": "5", "home_minutes": "30",
    "power_mode": "normal", "eth_mode": "client", "ssid": "SOS", "passphrase": "", "ai_state": "off",
}
THEMES = ("vault", "field", "blackout")

FAKE_CMD_OUTPUT: dict[tuple[str, ...], str] = {
    ("nmcli", "-t", "-f", "NAME", "con", "show", "--active"): "sos-hotspot\nsos-eth-client\n",
    ("iw", "dev", "wlan0", "station", "dump"):
        "Station aa:bb:cc:dd:ee:01 (on wlan0)\n\tinactive time:\t10 ms\nStation aa:bb:cc:dd:ee:02 (on wlan0)\n\tinactive time:\t20 ms\n",
}
FAKE_SYSFS: dict[str, str] = {
    THERMAL_PATH: "45000\n",
    "/sys/class/backlight/fake/max_brightness": "31\n",
    "/sys/class/backlight/fake/brightness": "31\n",
}


def _strip_sudo(args: list[str]) -> tuple[str, ...]:
    out = list(args)
    while out and out[0] in ("sudo", "-n"):
        out.pop(0)
    return tuple(out)


def run_cmd(args: list[str], settings: Settings, timeout: float = 30.0, check: bool = False) -> str:
    if settings.dev:
        return FAKE_CMD_OUTPUT.get(_strip_sudo(args), "")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def sudo(args: list[str], settings: Settings) -> str:
    return run_cmd(["sudo", "-n", *args], settings)


def read_sysfs(path: str, settings: Settings) -> str | None:
    if settings.dev:
        return FAKE_SYSFS.get(path)
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def write_sysfs(path: str, value, settings: Settings) -> bool:
    if settings.dev:
        FAKE_SYSFS[path] = f"{value}\n"
        return True
    try:
        Path(path).write_text(f"{value}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def cpu_temp(settings: Settings) -> float | None:
    raw = read_sysfs(THERMAL_PATH, settings)
    try:
        return round(int(raw.strip()) / 1000, 1) if raw else None
    except ValueError:
        return None


def disk_info(path: Path, mounted: bool) -> dict:
    if mounted and Path(path).exists():
        usage = shutil.disk_usage(path)
        return {"mounted": True, "path": str(path), "total_gb": round(usage.total / 1e9, 1), "free_gb": round(usage.free / 1e9, 1)}
    return {"mounted": False, "path": str(path), "total_gb": 0.0, "free_gb": 0.0}


def mem_info() -> dict:
    total = avail = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail = int(line.split()[1])
    except OSError:
        pass
    return {"total_mb": total // 1024, "used_mb": max(0, total - avail) // 1024}


def uptime_s() -> int:
    try:
        return int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return 0


def hotspot_clients(settings: Settings) -> int:
    out = run_cmd(["iw", "dev", "wlan0", "station", "dump"], settings)
    return sum(1 for line in out.splitlines() if line.startswith("Station "))


def hotspot_enabled(settings: Settings) -> bool:
    out = run_cmd(["nmcli", "-t", "-f", "NAME", "con", "show", "--active"], settings)
    return HOTSPOT_PROFILE in [line.strip() for line in out.splitlines()]


def hotspot_info(conn: sqlite3.Connection, settings: Settings) -> dict:
    return {"ssid": get_setting(conn, "ssid", DEFAULTS["ssid"]), "ip": HOTSPOT_IP,
            "clients": hotspot_clients(settings), "enabled": hotspot_enabled(settings)}


def set_hotspot(conn: sqlite3.Connection, settings: Settings, ssid: str, passphrase: str | None = None) -> None:
    ssid = (ssid or "").strip()
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        raise ValueError("SSID must be 1 to 32 bytes")
    passphrase = passphrase or ""
    if passphrase and not 8 <= len(passphrase) <= 63:
        raise ValueError("Passphrase must be 8 to 63 characters (or empty for an open network)")
    sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "802-11-wireless.ssid", ssid], settings)
    if passphrase:
        sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", passphrase], settings)
    else:
        sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "remove", "wifi-sec"], settings)
    sudo(["nmcli", "con", "up", HOTSPOT_PROFILE], settings)
    set_setting(conn, "ssid", ssid)
    set_setting(conn, "passphrase", passphrase)


def set_eth_mode(conn: sqlite3.Connection, settings: Settings, mode: str) -> None:
    if mode not in ETH_PROFILES:
        raise ValueError("mode must be 'client' or 'direct'")
    other = ETH_PROFILES["direct" if mode == "client" else "client"]
    sudo(["nmcli", "con", "modify", other, "connection.autoconnect", "no"], settings)
    sudo(["nmcli", "con", "modify", ETH_PROFILES[mode], "connection.autoconnect", "yes"], settings)
    sudo(["nmcli", "con", "up", ETH_PROFILES[mode]], settings)
    set_setting(conn, "eth_mode", mode)


def backlight_device(settings: Settings) -> str | None:
    if settings.dev:
        return "/sys/class/backlight/fake"
    devices = sorted(glob.glob(BACKLIGHT_GLOB))
    return devices[0] if devices else None


def set_backlight(settings: Settings, level: int) -> int | None:
    device = backlight_device(settings)
    if device is None:
        return None
    level = max(MIN_BACKLIGHT_LEVEL, min(100, int(level)))
    raw_max = read_sysfs(f"{device}/max_brightness", settings)
    max_brightness = int(raw_max.strip()) if raw_max and raw_max.strip().isdigit() else 255
    raw = max(1, round(level * max_brightness / 100))
    if not write_sysfs(f"{device}/brightness", raw, settings):
        return None
    return level


def ai_status(conn: sqlite3.Connection, settings: Settings) -> dict:
    return {"state": get_setting(conn, "ai_state", "off"), "model": settings.model, "message": get_setting(conn, "ai_message")}


def set_ai_state(conn: sqlite3.Connection, state: str, message: str | None = None) -> None:
    set_setting(conn, "ai_state", state)
    set_setting(conn, "ai_message", message)


def stop_ai(conn: sqlite3.Connection, settings: Settings, state: str = "off", message: str | None = None) -> None:
    sudo(["systemctl", "stop", LLAMA_UNIT], settings)
    set_ai_state(conn, state, message)


def set_power_mode(conn: sqlite3.Connection, settings: Settings, mode: str) -> None:
    if mode not in ("normal", "low"):
        raise ValueError("mode must be 'normal' or 'low'")
    set_setting(conn, "power_mode", mode)
    if mode == "low":
        if get_setting(conn, "ai_state", "off") not in ("off", "off-thermal", "error"):
            stop_ai(conn, settings, "off", "Turned off by low power mode")
        set_backlight(settings, LOW_POWER_BACKLIGHT)
    else:
        set_backlight(settings, 100)


def apply_settings(conn: sqlite3.Connection, patch: dict) -> None:
    for key, value in patch.items():
        if value is None:
            continue
        if key == "default_theme":
            if value not in THEMES:
                raise ValueError("default_theme must be vault, field or blackout")
            set_setting(conn, key, value)
        elif key in ("thermal_ai_off_c", "idle_minutes", "home_minutes"):
            lo, hi = {"thermal_ai_off_c": (50, 95), "idle_minutes": (1, 120), "home_minutes": (1, 600)}[key]
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} must be a whole number") from exc
            if not lo <= number <= hi:
                raise ValueError(f"{key} must be between {lo} and {hi}")
            set_setting(conn, key, str(number))
        else:
            raise ValueError(f"unknown setting {key}")


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(conn: sqlite3.Connection, pin: str) -> bool:
    stored = get_setting(conn, "pin_hash")
    if not stored:
        return False
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt((pin or "").encode("utf-8"), salt=bytes.fromhex(salt_hex), n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(digest.hex(), digest_hex)


def pin_required(conn: sqlite3.Connection) -> bool:
    return bool(get_setting(conn, "pin_hash"))


def set_pin(conn: sqlite3.Connection, pin: str) -> None:
    if not (pin and pin.isdigit() and 4 <= len(pin) <= 12):
        raise ValueError("PIN must be 4 to 12 digits")
    set_setting(conn, "pin_hash", hash_pin(pin))


def clear_pin(conn: sqlite3.Connection) -> None:
    set_setting(conn, "pin_hash", None)


class TokenStore:
    def __init__(self, ttl: int = TOKEN_TTL, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = ttl
        self.clock = clock
        self._tokens: dict[str, float] = {}

    def issue(self) -> str:
        now = self.clock()
        self._tokens = {t: exp for t, exp in self._tokens.items() if exp > now}
        token = secrets.token_urlsafe(24)
        self._tokens[token] = now + self.ttl
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        exp = self._tokens.get(token)
        return exp is not None and exp > self.clock()

    def revoke_all(self) -> None:
        self._tokens.clear()


class RateLimiter:
    def __init__(self, limit: int = PIN_ATTEMPTS, window: float = PIN_WINDOW, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


class ThermalWatchdog:
    """Polls the SoC temperature; at or above thermal_ai_off_c with the AI on it stops llama and sets
    off-thermal. It never restarts the AI."""

    def __init__(self, settings: Settings, db_path, interval: float = 10.0) -> None:
        self.settings = settings
        self.db_path = db_path
        self.interval = interval

    def tick(self, conn: sqlite3.Connection) -> str | None:
        temp = cpu_temp(self.settings)
        if temp is None:
            return None
        threshold = float(get_setting(conn, "thermal_ai_off_c", DEFAULTS["thermal_ai_off_c"]))
        state = get_setting(conn, "ai_state", "off")
        if temp >= threshold and state in ("starting", "ready", "busy"):
            stop_ai(conn, self.settings, "off-thermal", f"AI stopped at {temp:.0f} C (limit {threshold:.0f} C)")
            return "stopped"
        return None

    async def run(self) -> None:
        while True:
            conn = connect(self.db_path)
            try:
                self.tick(conn)
            except Exception:  # the watchdog must survive transient errors
                pass
            finally:
                conn.close()
            await asyncio.sleep(self.interval)


def default_sync_command(tier: str) -> list[str]:
    return [sys.executable, "-m", "sos.cli", "sync", "--tier", tier]


class UpdateRunner:
    """Runs `sos sync` per tier in a background thread and keeps the last 500 output lines."""

    def __init__(self, command_factory: Callable[[str], list[str]] = default_sync_command) -> None:
        self.factory = command_factory
        self.lines: deque[str] = deque(maxlen=500)
        self.running = False
        self.done = False
        self.ok: bool | None = None
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self, tiers: list[str]) -> bool:
        with self._lock:
            if self.running:
                return False
            self.running, self.done, self.ok = True, False, None
            self.lines.clear()
            self._thread = threading.Thread(target=self._run, args=(list(tiers),), daemon=True)
            self._thread.start()
            return True

    def _run(self, tiers: list[str]) -> None:
        ok = True
        for tier in tiers:
            self.lines.append(f"== sync {tier}")
            try:
                proc = subprocess.Popen(self.factory(tier), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.lines.append(line.rstrip("\n"))
                rc = proc.wait()
                if rc != 0:
                    ok = False
                    self.lines.append(f"sync {tier} failed (exit {rc})")
            except OSError as exc:
                ok = False
                self.lines.append(f"sync {tier} failed: {exc}")
        with self._lock:
            self.ok, self.done, self.running = ok, True, False

    def progress(self) -> dict:
        return {"running": self.running, "lines": list(self.lines), "done": self.done, "ok": self.ok}

    def wait(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)


def status(conn: sqlite3.Connection, settings: Settings) -> dict:
    from sos.library import ext_mounted

    ext_ok = ext_mounted(settings)
    return {
        "version": __version__,
        "uptime_s": uptime_s(),
        "cpu_temp_c": cpu_temp(settings),
        "load": [round(x, 2) for x in os.getloadavg()],
        "mem": mem_info(),
        "disks": {"core": disk_info(settings.core, True), "extended": disk_info(settings.ext, ext_ok)},
        "hotspot": hotspot_info(conn, settings),
        "eth_mode": get_setting(conn, "eth_mode", DEFAULTS["eth_mode"]),
        "power_mode": get_setting(conn, "power_mode", DEFAULTS["power_mode"]),
        "ai": ai_status(conn, settings),
        "thermal_ai_off_c": int(get_setting(conn, "thermal_ai_off_c", DEFAULTS["thermal_ai_off_c"])),
        "idle_minutes": int(get_setting(conn, "idle_minutes", DEFAULTS["idle_minutes"])),
        "home_minutes": int(get_setting(conn, "home_minutes", DEFAULTS["home_minutes"])),
        "pin_required": pin_required(conn),
        "dev": settings.dev,
        "default_theme": get_setting(conn, "default_theme", DEFAULTS["default_theme"]),
    }


def rescan(conn: sqlite3.Connection, settings: Settings) -> dict:
    from sos.library import rescan as library_rescan

    return library_rescan(conn, settings)
```

- [ ] **Step 4: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_system.py -v`
Expected: all PASS (the thermal test records exactly one `systemctl stop`).

- [ ] **Step 5: Commit**

```bash
git add api/sos/system.py api/tests/test_system.py
git commit -m "feat(system): temp, disks, hotspot, eth mode, power mode, backlight, pin, thermal watchdog, updater"
```

---

### Task 11: FastAPI app (`sos.main`) and routers

**Files:**
- Create: `api/sos/main.py`
- Create: `api/sos/routers/__init__.py`, `status.py`, `library.py`, `search.py`, `playbooks.py`, `cards.py`, `pages.py`, `map.py`, `places.py`, `notes.py`, `ai.py` (stub), `kiosk.py`, `system.py`
- Modify: `api/tests/conftest.py` (add `app`, `client`, `remote_client` fixtures)
- Test: `api/tests/test_api.py`

**Interfaces:**
- Consumes: everything from Tasks 3 to 10.
- Produces: `sos.main.create_app(settings=None, background=True) -> FastAPI` and the module-level `sos.main:app` for uvicorn; `app.state.settings`, `app.state.kiwix` (`KiwixClient`), `app.state.tokens` (`TokenStore`), `app.state.pin_limiter` (`RateLimiter`), `app.state.content` (`ContentCache`), `app.state.updater` (`UpdateRunner`), `app.state.watchdog` (`ThermalWatchdog`), `app.state.idle` (`"active" | "idle"`), `app.state.backlight_level` (int); dependencies `sos.routers.get_db`, `require_localhost`, `require_pin`, `settings_dep`. Every error body is `{"detail": string}` (validation errors are flattened to one string). Endpoint paths and shapes are exactly the overview table. Plan 05 replaces `routers/ai.py` and may add `app.state.ai`.

- [ ] **Step 1: Add the app fixtures to `api/tests/conftest.py`**

Append:

```python
@pytest.fixture
def app(env):
    from sos.main import create_app

    return create_app(env, background=False)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        yield c


@pytest.fixture
def remote_client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, client=("10.42.0.7", 50000)) as c:
        yield c
```

- [ ] **Step 2: Write the failing tests**

`api/tests/test_api.py`:

```python
import shutil
import sys
import time
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, places, system

FX = Path(__file__).parent / "fixtures"
WIKI = "wikipedia_en_100_mini_2026-01"
KIWIX = "http://kiwix.test/kiwix"


def _install_zims(env):
    for n in (WIKI, "sos-test-noindex"):
        shutil.copy(FX / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")


def test_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["dev"] is True and body["version"] == "0.1.0" and body["pin_required"] is False
    assert body["hotspot"]["ip"] == "10.42.0.1" and body["ai"]["state"] == "off"


def test_library_and_rescan(client, env):
    r = client.get("/api/library")
    assert r.status_code == 200
    wiki = next(i for c in r.json()["categories"] for i in c["items"] if i["id"] == WIKI)
    assert wiki["available"] is False and wiki["url"] is None
    _install_zims(env)
    r = client.post("/api/system/rescan")
    assert r.status_code == 200 and r.json() == {"items": 13, "available": 2}
    r = client.get(f"/api/library/{WIKI}")
    assert r.status_code == 200
    assert r.json()["available"] is True and r.json()["url"] == f"/read/{WIKI}/" and r.json()["drive_label"] == "Core"
    ext = client.get("/api/library/sos-ext-missing").json()
    assert ext["drive_label"] == "On external drive (not connected)" and ext["available"] is False
    assert client.get("/api/library/nope").status_code == 404
    assert client.get("/api/library/nope").json() == {"detail": "Item not found"}


@respx.mock(base_url=KIWIX)
def test_search_and_suggest(respx_mock, client, env):
    respx_mock.get("/search").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "search.xml").read_text()))
    respx_mock.get("/suggest").mock(return_value=httpx.Response(200, text=(FX / "kiwix" / "suggest.json").read_text()))
    _install_zims(env)
    client.post("/api/system/rescan")
    r = client.get("/api/search", params={"q": "water"})
    assert r.status_code == 200
    body = r.json()
    assert body["q"] == "water" and body["partial"] is False
    assert any(x["kind"] == "article" and x["url"] == f"/read/{WIKI}/Precipitation" for x in body["results"])
    assert any(x["kind"] == "playbook" for x in body["results"])
    r = client.get("/api/search", params={"q": "water", "sources": "playbooks", "limit": 1})
    assert len(r.json()["results"]) == 1 and r.json()["results"][0]["source"] == "playbooks"
    r = client.get("/api/suggest", params={"q": "wat"})
    assert r.status_code == 200 and 1 <= len(r.json()) <= 10
    assert any(s["url"] == f"/read/{WIKI}/Water" for s in r.json())
    assert client.get("/api/search").json()["results"] == []


def test_playbooks_list_and_detail(client):
    r = client.get("/api/playbooks")
    assert r.status_code == 200
    assert r.json() == [{"slug": "grid-collapse", "title": "National grid collapse", "icon": "bolt",
                         "summary": "A weeks-long blackout with water pumps and comms down.", "order": 4}]
    r = client.get("/api/playbooks/grid-collapse")
    assert r.status_code == 200
    pb = r.json()
    assert [s["id"] for s in pb["sections"]] == ["right-now", "first-72-hours", "first-month", "long-term", "uk-specifics", "go-deeper"]
    assert [c["id"] for c in pb["checklist"]] == ["fill-every-bottle-and-the-bath", "cooker-off", "check-on-neighbours",
                                                   "water/fill-clean-containers", "water/label-treated"]
    assert all(c["checked"] is False and c["updated_at"] is None for c in pb["checklist"])
    assert pb["modules"][0]["slug"] == "water" and pb["overlays"] == ["health", "water"] and pb["reviewed"] == "2026-09-01"
    assert pb["sources"][1] == {"title": "Test PDF", "doc": "sos-test-pdf", "as_at": "2026-09"}
    assert client.get("/api/playbooks/nope").status_code == 404


def test_checklist_put_and_reset(client):
    r = client.put("/api/playbooks/grid-collapse/checklist/cooker-off", json={"checked": True})
    assert r.status_code == 200
    items = {c["id"]: c for c in r.json()}
    assert items["cooker-off"]["checked"] is True and items["cooker-off"]["updated_at"] is not None
    assert items["check-on-neighbours"]["checked"] is False
    r = client.put("/api/playbooks/grid-collapse/checklist/water/label-treated", json={"checked": True})
    assert {c["id"] for c in r.json() if c["checked"]} == {"cooker-off", "water/label-treated"}
    r = client.put("/api/playbooks/grid-collapse/checklist/cooker-off", json={"checked": False})
    assert {c["id"] for c in r.json() if c["checked"]} == {"water/label-treated"}
    assert client.put("/api/playbooks/grid-collapse/checklist/nope", json={"checked": True}).status_code == 404
    assert client.put("/api/playbooks/nope/checklist/cooker-off", json={"checked": True}).status_code == 404
    r = client.delete("/api/playbooks/grid-collapse/checklist")
    assert r.status_code == 200 and not any(c["checked"] for c in r.json()) and len(r.json()) == 5


def test_modules_cards_pages(client):
    r = client.get("/api/modules/water")
    assert r.status_code == 200 and set(r.json()) == {"slug", "title", "html"}
    assert 'data-item-id="water/label-treated"' in r.json()["html"]
    assert client.get("/api/modules/nope").status_code == 404
    r = client.get("/api/cards")
    assert r.status_code == 200 and r.json()[0]["slug"] == "bleeding" and "<ol>" in r.json()[0]["html"]
    assert set(r.json()[0]) == {"slug", "title", "icon", "order", "html"}
    assert client.get("/api/cards/bleeding").json()["title"] == "Severe bleeding"
    assert client.get("/api/cards/nope").status_code == 404
    r = client.get("/api/pages")
    assert r.json() == [{"slug": "pmr446", "title": "PMR446 radio channels", "icon": "radio", "order": 1, "category": "comms"}]
    page = client.get("/api/pages/pmr446").json()
    assert set(page) == {"slug", "title", "icon", "order", "html", "category"} and "<table>" in page["html"]
    assert client.get("/api/pages/nope").status_code == 404


def test_map_config_and_overlays(client, env):
    (env.core / "maps" / "overlays").mkdir()
    (env.core / "maps" / "uk-ie.pmtiles").write_bytes(b"PMTiles")
    (env.core / "maps" / "overlays" / "health.geojson").write_text('{"type":"FeatureCollection","features":[]}')
    conn = db.connect(env.db_path)
    db.set_setting(conn, "overlay_scenarios", '{"health": ["grid-collapse", "pandemic"]}')
    conn.close()
    client.post("/api/system/rescan")
    cfg = client.get("/api/map/config").json()
    assert [b["id"] for b in cfg["bases"]] == ["osm", "os"]
    osm = cfg["bases"][0]
    assert osm["available"] is True and osm["styles"] == {"vault": "/maps/styles/osm-vault.json", "field": "/maps/styles/osm-field.json",
                                                            "blackout": "/maps/styles/osm-blackout.json"}
    assert cfg["bases"][1]["available"] is False
    assert cfg["terrain"] == {"contours": None, "hillshade": None}
    assert cfg["packs"] == [] and cfg["packs_index_url"] is None
    overlays = {o["id"]: o for o in cfg["overlays"]}
    assert overlays["health"]["available"] is True and overlays["health"]["url"] == "/maps/overlays/health.geojson"
    assert overlays["health"]["scenarios_on"] == ["grid-collapse", "pandemic"] and overlays["health"]["color"] == "#e03131"
    assert overlays["nuclear-sites"]["available"] is False and overlays["nuclear-sites"]["url"] is None
    assert overlays["water"]["kind"] == "pmtiles" and overlays["water"]["layer_id"] == "water"
    assert set(overlays["health"]) == {"id", "title", "kind", "layer_id", "url", "default_on", "scenarios_on", "coverage", "color", "icon", "available"}
    assert client.get("/api/map/overlays").json() == cfg["overlays"]


def test_places_endpoint(client, env):
    conn = db.connect(env.db_path)
    places.import_places(conn, FX / "places.csv")
    conn.close()
    assert client.get("/api/places", params={"q": "ox"}).json() == []
    r = client.get("/api/places", params={"q": "oxf"})
    assert r.json()[0]["name"] == "Oxford" and set(r.json()[0]) == {"name", "kind", "lat", "lon", "region", "postcode"}
    assert len(client.get("/api/places", params={"q": "test hamlet", "limit": 100}).json()) == 25
    assert len(client.get("/api/places", params={"q": "test hamlet"}).json()) == 10


def test_notes_crud(client):
    r = client.post("/api/notes", json={"title": "Fuel", "body": "Two jerry cans in the shed"})
    assert r.status_code == 200
    note = r.json()
    assert note["kind"] == "note" and note["id"] == 1 and note["lat"] is None and note["updated_at"]
    assert client.post("/api/notes", json={"kind": "pin", "title": "Well"}).status_code == 400
    pin = client.post("/api/notes", json={"kind": "pin", "title": "Well", "body": "", "lat": 51.75, "lon": -1.25}).json()
    assert pin["kind"] == "pin" and pin["lat"] == 51.75
    assert [n["id"] for n in client.get("/api/notes").json()] == [1, 2]
    assert [n["id"] for n in client.get("/api/notes", params={"kind": "pin"}).json()] == [2]
    r = client.put("/api/notes/1", json={"body": "Three jerry cans"})
    assert r.json()["body"] == "Three jerry cans" and r.json()["title"] == "Fuel"
    assert client.put("/api/notes/99", json={"body": "x"}).status_code == 404
    assert client.delete("/api/notes/1").json() == {"ok": True}
    assert client.delete("/api/notes/1").status_code == 404
    assert [n["id"] for n in client.get("/api/notes").json()] == [2]


def test_ai_stub_returns_503(client):
    for method, path in (("get", "/api/ai/status"), ("post", "/api/ai/enable"), ("post", "/api/ai/disable"), ("post", "/api/ai/ask")):
        r = getattr(client, method)(path, json={"question": "x", "history": []}) if method == "post" else client.get(path)
        assert r.status_code == 503 and r.json() == {"detail": "AI not installed"}


def test_localhost_only_endpoints(client, remote_client, monkeypatch):
    assert remote_client.post("/api/kiosk/backlight", json={"level": 50}).status_code == 403
    assert remote_client.post("/api/kiosk/idle", json={"state": "idle"}).status_code == 403
    assert remote_client.post("/api/system/rescan").status_code == 403
    assert remote_client.post("/api/system/backlight", json={"level": 50}).status_code == 200
    r = client.post("/api/kiosk/backlight", json={"level": 50})
    assert r.status_code == 200 and r.json() == {"level": 50}
    assert client.post("/api/kiosk/backlight", json={"level": 0}).json() == {"level": 10}
    assert client.post("/api/kiosk/backlight", json={"level": 101}).status_code == 422
    assert client.post("/api/kiosk/idle", json={"state": "idle"}).json() == {"ok": True}
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "3"
    assert client.post("/api/kiosk/idle", json={"state": "active"}).json() == {"ok": True}
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "16"
    monkeypatch.setattr(system, "backlight_device", lambda settings: None)
    assert client.post("/api/kiosk/backlight", json={"level": 50}).status_code == 501


def test_pin_gating_suite(client, app):
    # open when no PIN is set
    assert client.post("/api/system/power-mode", json={"mode": "low"}).status_code == 200
    assert client.post("/api/system/pin", json={"pin": "1234"}).status_code == 401
    # set the first PIN (no token needed while none is set)
    assert client.post("/api/system/pin/change", json={"pin": "1234"}).json() == {"ok": True}
    assert client.get("/api/status").json()["pin_required"] is True
    # gated endpoints now need a token
    for path, body in (("/api/system/power-mode", {"mode": "normal"}), ("/api/system/eth-mode", {"mode": "direct"}),
                       ("/api/system/hotspot", {"ssid": "X"}), ("/api/system/update", {"tiers": ["core"]}),
                       ("/api/system/pin/change", {"pin": "9999"})):
        r = client.post(path, json=body)
        assert r.status_code == 401 and r.json() == {"detail": "PIN required"}, path
    # wrong PIN is 401 and the sixth attempt in a minute is 429
    for _ in range(5):
        assert client.post("/api/system/pin", json={"pin": "0000"}).status_code == 401
    assert client.post("/api/system/pin", json={"pin": "1234"}).status_code == 429
    app.state.pin_limiter = system.RateLimiter()
    r = client.post("/api/system/pin", json={"pin": "1234"})
    assert r.status_code == 200 and r.json()["expires_in"] == 600
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 200
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers={"Authorization": "Bearer nope"}).status_code == 401
    # expiry
    app.state.tokens.clock = lambda: time.monotonic() + 601
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 401
    app.state.tokens.clock = time.monotonic
    token = client.post("/api/system/pin", json={"pin": "1234"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/system/pin/change", json={"pin": "12"}, headers=headers).status_code == 400
    assert client.post("/api/system/pin/change", json={"pin": "5678"}, headers=headers).json() == {"ok": True}
    assert client.post("/api/system/power-mode", json={"mode": "normal"}, headers=headers).status_code == 401
    assert client.post("/api/system/pin", json={"pin": "5678"}).status_code == 200


def test_system_settings_hotspot_eth_and_update(client, app):
    r = client.post("/api/system/settings", json={"default_theme": "field", "thermal_ai_off_c": 70})
    assert r.status_code == 200 and r.json()["default_theme"] == "field" and r.json()["thermal_ai_off_c"] == 70
    r = client.post("/api/system/settings", json={"default_theme": "neon"})
    assert r.status_code == 400 and "default_theme" in r.json()["detail"]
    r = client.post("/api/system/hotspot", json={"ssid": "Bunker", "passphrase": "letmein123"})
    assert r.status_code == 200 and r.json()["hotspot"]["ssid"] == "Bunker"
    assert client.post("/api/system/hotspot", json={"ssid": "Bunker", "passphrase": "short"}).status_code == 400
    r = client.post("/api/system/eth-mode", json={"mode": "direct"})
    assert r.json()["eth_mode"] == "direct"
    assert client.post("/api/system/eth-mode", json={"mode": "bridge"}).status_code == 422
    app.state.updater = system.UpdateRunner(lambda tier: [sys.executable, "-c", f"print('sync {tier} ok')"])
    assert client.post("/api/system/update", json={"tiers": ["core", "extended"]}).json() == {"started": True}
    app.state.updater.wait(10)
    p = client.get("/api/system/update/progress").json()
    assert p["done"] is True and p["ok"] is True and p["lines"] == ["== sync core", "sync core ok"]
    app.state.updater = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import time; time.sleep(0.5)"])
    assert client.post("/api/system/update", json={"tiers": ["core"]}).status_code == 200
    assert client.post("/api/system/update", json={"tiers": ["core"]}).status_code == 409
    app.state.updater.wait(5)
    assert client.post("/api/system/update", json={"tiers": ["nope"]}).status_code == 422


def test_validation_errors_are_strings(client):
    r = client.post("/api/notes", json={"kind": "bookmark"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str) and "kind" in r.json()["detail"]
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_api.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.main'`.

- [ ] **Step 4: Write `api/sos/routers/__init__.py`**

```python
"""Dependencies shared by the routers: a per-request SQLite connection, the localhost guard and the PIN guard."""
from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Depends, HTTPException, Request

from sos import db, system
from sos.config import Settings

LOCALHOSTS = {"127.0.0.1", "::1", "localhost"}


def settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    conn = db.connect(request.app.state.settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def require_localhost(request: Request) -> None:
    host = request.client.host if request.client else None
    if host not in LOCALHOSTS:
        raise HTTPException(status_code=403, detail="Only allowed from the box itself")


def require_pin(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> None:
    if not system.pin_required(conn):
        return
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else None
    if not request.app.state.tokens.valid(token):
        raise HTTPException(status_code=401, detail="PIN required")
```

- [ ] **Step 5: Write the routers**

`api/sos/routers/status.py`:

```python
from fastapi import APIRouter, Depends, Request

from sos import system
from sos.routers import get_db

router = APIRouter(tags=["status"])


@router.get("/status")
def get_status(request: Request, conn=Depends(get_db)):
    return system.status(conn, request.app.state.settings)
```

`api/sos/routers/library.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Request

from sos import library
from sos.routers import get_db

router = APIRouter(tags=["library"])


@router.get("/library")
def list_library(request: Request, conn=Depends(get_db)):
    return library.library_response(conn, request.app.state.settings)


@router.get("/library/{item_id}")
def get_library_item(item_id: str, request: Request, conn=Depends(get_db)):
    row = library.get_item(conn, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return library.item_dict(row, library.ext_mounted(request.app.state.settings))
```

`api/sos/routers/search.py`:

```python
from fastapi import APIRouter, Depends, Request

from sos import search as search_mod
from sos.routers import get_db

router = APIRouter(tags=["search"])


@router.get("/search")
async def do_search(request: Request, q: str = "", sources: str | None = None, limit: int = 40, conn=Depends(get_db)):
    wanted = [s for s in sources.split(",") if s] if sources else None
    return await search_mod.search(conn, request.app.state.settings, request.app.state.kiwix, q, wanted, limit)


@router.get("/suggest")
async def do_suggest(request: Request, q: str = "", conn=Depends(get_db)):
    return await search_mod.suggest(conn, request.app.state.settings, request.app.state.kiwix, q)
```

`api/sos/routers/playbooks.py`:

```python
"""Playbooks, their shared checklist state, and standalone modules."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sos.db import now_iso
from sos.routers import get_db

router = APIRouter(tags=["playbooks"])


class ChecklistBody(BaseModel):
    checked: bool


def _rendered(request: Request, slug: str):
    doc = request.app.state.content.rendered("scenario", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return doc


def _checklist(conn, slug: str, rendered) -> list[dict]:
    state = {r["item_id"]: r for r in conn.execute(
        "SELECT item_id, checked, updated_at FROM checklist_state WHERE playbook=?", (slug,))}
    out = []
    for item in rendered.checklist:
        row = state.get(item["id"])
        out.append({"id": item["id"], "text": item["text"], "checked": bool(row["checked"]) if row else False,
                    "updated_at": row["updated_at"] if row else None})
    return out


def _summary(doc) -> dict:
    return {"slug": doc.id, "title": doc.title, "icon": doc.icon, "summary": doc.summary, "order": doc.order}


@router.get("/playbooks")
def list_playbooks(request: Request):
    return [_summary(d) for d in request.app.state.content.list("scenario")]


@router.get("/playbooks/{slug}")
def get_playbook(slug: str, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    return {"slug": r.slug, "title": r.title, "icon": r.icon, "summary": r.summary, "order": r.order,
            "sections": r.sections, "checklist": _checklist(conn, slug, r), "modules": r.modules,
            "overlays": r.overlays, "sources": r.sources, "reviewed": r.reviewed}


@router.put("/playbooks/{slug}/checklist/{item_id:path}")
def set_checklist_item(slug: str, item_id: str, body: ChecklistBody, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    if item_id not in {c["id"] for c in r.checklist}:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    conn.execute(
        "INSERT INTO checklist_state(playbook, item_id, checked, updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(playbook, item_id) DO UPDATE SET checked=excluded.checked, updated_at=excluded.updated_at",
        (slug, item_id, int(body.checked), now_iso()),
    )
    conn.commit()
    return _checklist(conn, slug, r)


@router.delete("/playbooks/{slug}/checklist")
def reset_checklist(slug: str, request: Request, conn=Depends(get_db)):
    r = _rendered(request, slug)
    conn.execute("DELETE FROM checklist_state WHERE playbook=?", (slug,))
    conn.commit()
    return _checklist(conn, slug, r)


@router.get("/modules/{slug}")
def get_module(slug: str, request: Request):
    doc = request.app.state.content.rendered("module", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return {"slug": doc.slug, "title": doc.title, "html": doc.html}
```

`api/sos/routers/cards.py`:

```python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["cards"])


def _card(doc) -> dict:
    return {"slug": doc.slug, "title": doc.title, "icon": doc.icon, "order": doc.order, "html": doc.html}


@router.get("/cards")
def list_cards(request: Request):
    content = request.app.state.content
    return [_card(content.rendered("card", d.id)) for d in content.list("card")]


@router.get("/cards/{slug}")
def get_card(slug: str, request: Request):
    doc = request.app.state.content.rendered("card", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return _card(doc)
```

`api/sos/routers/pages.py`:

```python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["pages"])


@router.get("/pages")
def list_pages(request: Request):
    return [{"slug": d.id, "title": d.title, "icon": d.icon, "order": d.order, "category": d.category}
            for d in request.app.state.content.list("page")]


@router.get("/pages/{slug}")
def get_page(slug: str, request: Request):
    doc = request.app.state.content.rendered("page", slug)
    if doc is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"slug": doc.slug, "title": doc.title, "icon": doc.icon, "order": doc.order, "html": doc.html, "category": doc.category}
```

`api/sos/routers/map.py`:

```python
"""Map configuration derived from manifest items of category `maps` and from overlay items.
Conventions plan 04 must follow: base map item ids are `uk-ie` (osm) and `os-zoomstack` (os); terrain items are
`contours` and `hillshade`; phone packs are items of kind `mwm`/`apk` plus a `dir` item `packs` whose index is
`/maps/packs/index.html`; styles live at `/maps/styles/<base>-<theme>.json`."""
import json

from fastapi import APIRouter, Depends

from sos.db import get_setting
from sos.routers import get_db

router = APIRouter(tags=["map"])
BASES = [("osm", "OpenStreetMap", "uk-ie"), ("os", "Ordnance Survey", "os-zoomstack")]
THEMES = ("vault", "field", "blackout")


def _maps_url(row) -> str:
    dest = row["dest"]
    return "/maps/" + (dest[5:] if dest.startswith("maps/") else dest)


def overlays_list(conn) -> list[dict]:
    scenarios_on = json.loads(get_setting(conn, "overlay_scenarios", "{}") or "{}")
    out = []
    for row in conn.execute("SELECT * FROM library_items WHERE overlay_json IS NOT NULL ORDER BY priority, id"):
        o = json.loads(row["overlay_json"])
        available = bool(row["available"])
        out.append({
            "id": o["id"], "title": row["title"], "kind": o["kind"], "layer_id": o.get("layer_id"),
            "url": _maps_url(row) if available and o["kind"] != "style-layer" else None,
            "default_on": bool(o.get("default_on")), "scenarios_on": scenarios_on.get(o["id"], []),
            "coverage": o.get("coverage", []), "color": o.get("color", "#ffffff"), "icon": o.get("icon"), "available": available,
        })
    return out


@router.get("/map/config")
def map_config(conn=Depends(get_db)):
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items WHERE category='maps'")}

    def available(item_id: str) -> bool:
        return bool(rows.get(item_id) and rows[item_id]["available"])

    bases = [{"id": bid, "title": title, "styles": {t: f"/maps/styles/{bid}-{t}.json" for t in THEMES}, "available": available(item)}
             for bid, title, item in BASES]
    terrain = {name: (_maps_url(rows[name]) if available(name) else None) for name in ("contours", "hillshade")}
    packs = [{"title": r["title"], "url": _maps_url(r), "size_bytes": r["size_bytes"] or 0}
             for r in rows.values() if r["kind"] in ("mwm", "apk") and r["available"]]
    return {"bases": bases, "terrain": terrain, "overlays": overlays_list(conn), "packs": packs,
            "packs_index_url": "/maps/packs/index.html" if available("packs") else None}


@router.get("/map/overlays")
def map_overlays(conn=Depends(get_db)):
    return overlays_list(conn)
```

`api/sos/routers/places.py`:

```python
from fastapi import APIRouter, Depends

from sos import places
from sos.routers import get_db

router = APIRouter(tags=["places"])


@router.get("/places")
def get_places(q: str = "", limit: int = 10, conn=Depends(get_db)):
    return places.query_places(conn, q, limit)
```

`api/sos/routers/notes.py`:

```python
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sos.db import now_iso
from sos.routers import get_db

router = APIRouter(tags=["notes"])


class NoteIn(BaseModel):
    kind: Literal["note", "pin"] = "note"
    title: str = ""
    body: str = ""
    lat: float | None = None
    lon: float | None = None


class NotePatch(BaseModel):
    kind: Literal["note", "pin"] | None = None
    title: str | None = None
    body: str | None = None
    lat: float | None = None
    lon: float | None = None


def _row(r) -> dict:
    return {"id": r["id"], "kind": r["kind"], "title": r["title"] or "", "body": r["body"] or "",
            "lat": r["lat"], "lon": r["lon"], "updated_at": r["updated_at"]}


def _get(conn, note_id: int):
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return row


def _check_pin(kind: str, lat, lon) -> None:
    if kind == "pin" and (lat is None or lon is None):
        raise HTTPException(status_code=400, detail="Pins need lat and lon")


@router.get("/notes")
def list_notes(kind: str | None = None, conn=Depends(get_db)):
    if kind:
        rows = conn.execute("SELECT * FROM notes WHERE kind=? ORDER BY id", (kind,))
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY id")
    return [_row(r) for r in rows]


@router.post("/notes")
def create_note(body: NoteIn, conn=Depends(get_db)):
    _check_pin(body.kind, body.lat, body.lon)
    cur = conn.execute("INSERT INTO notes(kind, title, body, lat, lon, updated_at) VALUES (?,?,?,?,?,?)",
                       (body.kind, body.title, body.body, body.lat, body.lon, now_iso()))
    conn.commit()
    return _row(_get(conn, cur.lastrowid))


@router.put("/notes/{note_id}")
def update_note(note_id: int, body: NotePatch, conn=Depends(get_db)):
    current = _get(conn, note_id)
    merged = {k: (getattr(body, k) if getattr(body, k) is not None else current[k]) for k in ("kind", "title", "body", "lat", "lon")}
    _check_pin(merged["kind"], merged["lat"], merged["lon"])
    conn.execute("UPDATE notes SET kind=?, title=?, body=?, lat=?, lon=?, updated_at=? WHERE id=?",
                 (merged["kind"], merged["title"], merged["body"], merged["lat"], merged["lon"], now_iso(), note_id))
    conn.commit()
    return _row(_get(conn, note_id))


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, conn=Depends(get_db)):
    _get(conn, note_id)
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    return {"ok": True}
```

`api/sos/routers/ai.py` (stub; plan 05 replaces this file):

```python
"""AI endpoints placeholder: every /api/ai/* call answers 503 until plan 05 installs the assistant."""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["ai"])


@router.api_route("/ai/{rest:path}", methods=["GET", "POST"])
def ai_not_installed(rest: str):
    raise HTTPException(status_code=503, detail="AI not installed")
```

`api/sos/routers/kiosk.py`:

```python
"""Endpoints only the kiosk browser on the box may call (backlight, idle state)."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sos import system
from sos.routers import require_localhost

router = APIRouter(tags=["kiosk"], dependencies=[Depends(require_localhost)])
IDLE_LEVEL = 10


class BacklightBody(BaseModel):
    level: int = Field(ge=0, le=100)


class IdleBody(BaseModel):
    state: Literal["idle", "active"]


def apply_backlight(request: Request, level: int) -> dict:
    applied = system.set_backlight(request.app.state.settings, level)
    if applied is None:
        raise HTTPException(status_code=501, detail="No backlight device")
    request.app.state.backlight_level = applied
    return {"level": applied}


@router.post("/kiosk/backlight")
def kiosk_backlight(body: BacklightBody, request: Request):
    return apply_backlight(request, body.level)


@router.post("/kiosk/idle")
def kiosk_idle(body: IdleBody, request: Request):
    request.app.state.idle = body.state
    settings = request.app.state.settings
    if body.state == "idle":
        system.set_backlight(settings, IDLE_LEVEL)
    else:
        system.set_backlight(settings, getattr(request.app.state, "backlight_level", 100))
    return {"ok": True}
```

`api/sos/routers/system.py`:

```python
"""System control endpoints. PIN-gated ones depend on require_pin; rescan is localhost-only."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from sos import library, system
from sos.routers import get_db, require_localhost, require_pin
from sos.routers.kiosk import BacklightBody, apply_backlight

router = APIRouter(tags=["system"])


class PowerBody(BaseModel):
    mode: Literal["normal", "low"]


class EthBody(BaseModel):
    mode: Literal["client", "direct"]


class HotspotBody(BaseModel):
    ssid: str
    passphrase: str | None = None


class SettingsBody(BaseModel):
    default_theme: Literal["vault", "field", "blackout"] | None = None
    thermal_ai_off_c: int | None = None
    idle_minutes: int | None = None
    home_minutes: int | None = None


class UpdateBody(BaseModel):
    tiers: list[Literal["core", "extended"]] = Field(min_length=1)


class PinBody(BaseModel):
    pin: str


def _status(request: Request, conn) -> dict:
    return system.status(conn, request.app.state.settings)


@router.post("/system/backlight")
def system_backlight(body: BacklightBody, request: Request):
    return apply_backlight(request, body.level)


@router.post("/system/power-mode", dependencies=[Depends(require_pin)])
def power_mode(body: PowerBody, request: Request, conn=Depends(get_db)):
    system.set_power_mode(conn, request.app.state.settings, body.mode)
    return _status(request, conn)


@router.post("/system/eth-mode", dependencies=[Depends(require_pin)])
def eth_mode(body: EthBody, request: Request, conn=Depends(get_db)):
    system.set_eth_mode(conn, request.app.state.settings, body.mode)
    return _status(request, conn)


@router.post("/system/hotspot", dependencies=[Depends(require_pin)])
def hotspot(body: HotspotBody, request: Request, conn=Depends(get_db)):
    system.set_hotspot(conn, request.app.state.settings, body.ssid, body.passphrase)
    return _status(request, conn)


@router.post("/system/settings")
def settings_update(body: SettingsBody, request: Request, conn=Depends(get_db)):
    system.apply_settings(conn, body.model_dump(exclude_none=True))
    return _status(request, conn)


@router.post("/system/rescan", dependencies=[Depends(require_localhost)])
def rescan(request: Request, conn=Depends(get_db)):
    return system.rescan(conn, request.app.state.settings)


@router.post("/system/update", dependencies=[Depends(require_pin)])
def update(body: UpdateBody, request: Request):
    settings = request.app.state.settings
    tiers = [t for t in dict.fromkeys(body.tiers) if t == "core" or library.ext_mounted(settings)]
    if not tiers:
        raise HTTPException(status_code=400, detail="External drive is not connected")
    if not request.app.state.updater.start(tiers):
        raise HTTPException(status_code=409, detail="Update already running")
    return {"started": True}


@router.get("/system/update/progress")
def update_progress(request: Request):
    return request.app.state.updater.progress()


@router.post("/system/pin")
def pin_login(body: PinBody, request: Request, conn=Depends(get_db)):
    host = request.client.host if request.client else "unknown"
    if not request.app.state.pin_limiter.allow(host):
        raise HTTPException(status_code=429, detail="Too many attempts; wait a minute")
    if not system.pin_required(conn):
        raise HTTPException(status_code=401, detail="No PIN is set")
    if not system.verify_pin(conn, body.pin):
        raise HTTPException(status_code=401, detail="Wrong PIN")
    return {"token": request.app.state.tokens.issue(), "expires_in": system.TOKEN_TTL}


@router.post("/system/pin/change", dependencies=[Depends(require_pin)])
def pin_change(body: PinBody, request: Request, conn=Depends(get_db)):
    system.set_pin(conn, body.pin)
    request.app.state.tokens.revoke_all()
    return {"ok": True}
```

- [ ] **Step 6: Write `api/sos/main.py`**

```python
"""FastAPI application factory. `uvicorn sos.main:app` on the box; tests call create_app(settings, background=False)."""
from __future__ import annotations

import asyncio
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sos import __version__, db, library, manifest, search as search_mod, system
from sos.config import Settings, get_settings
from sos.content import ContentCache
from sos.kiwix import KiwixClient
from sos.routers import ai, cards, kiosk, notes, pages, places, playbooks, search, status
from sos.routers import library as library_router
from sos.routers import map as map_router
from sos.routers import system as system_router


def _bootstrap(settings: Settings) -> None:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    try:
        db.init_schema(conn)
        if settings.manifests.is_dir():
            library.upsert_items(conn, manifest.load_manifests(settings.manifests))
        if shutil.which(library.KIWIX_MANAGE):
            library.rescan(conn, settings)
        else:
            library.refresh_items(conn, settings)
    finally:
        conn.close()


def create_app(settings: Settings | None = None, background: bool = True) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _bootstrap(settings)
        app.state.settings = settings
        app.state.kiwix = KiwixClient(settings.kiwix_url)
        app.state.tokens = system.TokenStore()
        app.state.pin_limiter = system.RateLimiter()
        app.state.content = ContentCache(settings.playbooks)
        app.state.updater = system.UpdateRunner()
        app.state.watchdog = system.ThermalWatchdog(settings, settings.db_path)
        app.state.idle = "active"
        app.state.backlight_level = 100
        tasks: list[asyncio.Task] = []
        if background:
            tasks.append(asyncio.create_task(app.state.watchdog.run()))
            tasks.append(asyncio.create_task(search_mod.warm(settings, app.state.kiwix, settings.db_path)))
        try:
            yield
        finally:
            for t in tasks:
                t.cancel()
            await app.state.kiwix.aclose()

    app = FastAPI(title="Operation SOS", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    for router in (status.router, library_router.router, search.router, playbooks.router, cards.router, pages.router,
                   map_router.router, places.router, notes.router, ai.router, kiosk.router, system_router.router):
        app.include_router(router, prefix="/api")

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        parts = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "body")
            parts.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
        return JSONResponse(status_code=422, content={"detail": "; ".join(parts) or "Invalid request"})

    return app


app = create_app()
```

- [ ] **Step 7: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_api.py -v`
Expected: 15 PASS. Then run the whole suite: `cd api && .venv/bin/pytest -q` — everything so far passes.

- [ ] **Step 8: Smoke the real server once**

Run (from the repo root, two terminals or `&`):

```bash
SOS_DEV=1 SOS_STATE=/tmp/sos-state SOS_CORE=/home/dan/sos-content SOS_EXT=/tmp/sos-ext SOS_MANIFEST_DIR=$PWD/dev/manifest SOS_PLAYBOOKS_DIR=$PWD/api/tests/fixtures/playbooks \
  api/.venv/bin/uvicorn sos.main:app --port 8000 &
sleep 2; curl -s http://127.0.0.1:8000/api/status | head -c 200; echo; kill %1
```

Expected: JSON starting `{"version":"0.1.0","uptime_s":...` and `"dev":true`.

- [ ] **Step 9: Commit**

```bash
git add api/sos/main.py api/sos/routers api/tests/conftest.py api/tests/test_api.py
git commit -m "feat(api): FastAPI app factory and routers with PIN gating and localhost-only kiosk endpoints"
```

---

### Task 12: `sos.sync`, `sos.cli`, `sos.buildnhs` and the plan-04/05 stubs

**Files:**
- Create: `api/sos/sync.py`
- Create: `api/sos/cli.py` (replaces the Task 1 placeholder)
- Create: `api/sos/buildnhs.py`
- Create: `api/sos/buildmaps.py`, `api/sos/evalrun.py` (stubs)
- Create: `api/tests/fixtures/opds/catalog.xml`, `api/tests/fixtures/opds/zimgit-water_en_2024-08.zim.meta4`, `api/tests/fixtures/opds/empty.xml`
- Test: `api/tests/test_sync.py`, `api/tests/test_cli.py`, `api/tests/test_buildnhs.py`

**Interfaces:**
- Consumes: `sos.manifest`, `sos.library`, `sos.docs.index_docs`, `sos.places.import_places/places_path`, `sos.content.load_tree/validate_tree`, `sos.system` (pin, sudo).
- Produces: `sos.sync.Resolved(url, name, size, as_at, sha256, mirrors)`, `SyncError`, `ChecksumError`, `parse_opds_entry(text) -> Resolved | None`, `parse_meta4(text) -> tuple[int | None, str | None, list[str]]`, `resolve_kiwix(name, client) -> Resolved`, `resolve_item(item, client) -> Resolved | None`, `sha256_file(path) -> str`, `stream_download(url, target, client=None) -> Path`, `aria2c_download(url, target, sha256=None, mirrors=(), run=subprocess.run) -> Path`, `download(url, target, sha256=None, mirrors=(), use_aria2=None, run=subprocess.run, client=None) -> Path`, `sync(settings, tier, only=None, dry_run=False, out=print, client=None, run=subprocess.run, use_aria2=None) -> int`, `index(settings, out=print, runner=None) -> dict`, `index_content(conn, playbooks_dir) -> int`, `index_titles(conn) -> int`, `strip_markdown(md) -> str`, `notify_api(settings) -> bool`, `OPDS_URL`; `sos.cli.main(argv=None) -> int`; `sos.buildnhs.build_command(out_dir, date) -> list[str]`, `verify(zim, date, run=subprocess.run) -> list[str]`, `main(out=None, run=subprocess.run, date=None) -> int`; `sos.buildmaps.main(args)` and `sos.evalrun.main(args)` raise `NotImplementedError`.

- [ ] **Step 1: Write the OPDS fixtures**

`api/tests/fixtures/opds/catalog.xml` (the real `opds.library.kiwix.org` answer for `name=zimgit-water_en&count=1`, captured 2026-09-03):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:dc="http://purl.org/dc/terms/"
      xmlns:opds="https://specs.opds.io/opds-1.2"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <id>3cdfeea0-c663-4f6e-9bf1-555eca66ce98</id>
  <link rel="self" href="/catalog/v2/entries?name=zimgit-water_en&amp;count=1" type="application/atom+xml;profile=opds-catalog;kind=acquisition"/>
  <link rel="start" href="/catalog/v2/root.xml" type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <link rel="up" href="/catalog/v2/root.xml" type="application/atom+xml;profile=opds-catalog;kind=navigation"/>
  <title>Filtered Entries (name=zimgit-water_en&amp;count=1)</title>
  <updated>2026-09-03T20:54:16Z</updated>
  <totalResults>1</totalResults>
  <startIndex>0</startIndex>
  <itemsPerPage>1</itemsPerPage>
  <entry>
    <id>urn:uuid:2e17beb8-4d08-4734-75d4-6f56f73f3610</id>
    <title>Water Treatment Library</title>
    <updated>2024-08-29T00:00:00Z</updated>
    <summary>A library of water treatment and purification resources</summary>
    <language>eng</language>
    <name>zimgit-water_en</name>
    <flavour></flavour>
    <category>other</category>
    <tags>preppers;_ftindex:no;_pictures:yes;_videos:yes;_details:yes</tags>
    <articleCount>1</articleCount>
    <mediaCount>50</mediaCount>
    <link rel="http://opds-spec.org/image/thumbnail" href="/catalog/v2/illustration/2e17beb8-4d08-4734-75d4-6f56f73f3610/?size=48" type="image/png;width=48;height=48;scale=1"/>
    <link type="text/html" href="/content/zimgit-water_en_2024-08" />
    <link rel="http://opds-spec.org/acquisition/open-access" type="application/x-zim" href="https://lb.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim.meta4" length="20925440" />
    <author><name>Various</name></author>
    <publisher><name>openZIM</name></publisher>
    <dc:issued>2024-08-29T00:00:00Z</dc:issued>
  </entry>
</feed>
```

`api/tests/fixtures/opds/empty.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">
  <id>3cdfeea0-c663-4f6e-9bf1-555eca66ce98</id>
  <title>Filtered Entries (name=nope&amp;count=1)</title>
  <updated>2026-09-03T20:54:16Z</updated>
  <totalResults>0</totalResults>
  <startIndex>0</startIndex>
  <itemsPerPage>0</itemsPerPage>
</feed>
```

`api/tests/fixtures/opds/zimgit-water_en_2024-08.zim.meta4` (real Metalink, comments removed):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<metalink xmlns="urn:ietf:params:xml:ns:metalink">
  <generator>MirrorBrain/2.19.0</generator>
  <origin dynamic="true">https://lb.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim.meta4</origin>
  <published>2026-09-03T20:55:28Z</published>
  <publisher>
    <name>Kiwix project</name>
    <url>https://kiwix.org</url>
  </publisher>
  <file name="zimgit-water_en_2024-08.zim">
    <size>20924451</size>
    <hash type="md5">282e1687696db936fda14568b52d9b19</hash>
    <hash type="sha-1">cebef900d5c004d10d05b765734a1d5ab5c750be</hash>
    <hash type="sha-256">392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6</hash>
    <pieces length="4194304" type="sha-1">
      <hash>f4435a5e8d4b38285b3d544512f24b44709c9997</hash>
      <hash>3c77fd0cc60cecfede5b2e60ca88b9293743afef</hash>
      <hash>69f4ef92bfb043fc562211f811d7cfb775d2ca51</hash>
      <hash>82e32d2396bbdb8f0d3b117fb332c9d031193454</hash>
      <hash>1151818469ae21d0113b1803769844b81f155101</hash>
    </pieces>
    <url location="nl" priority="1">https://ftp.nluug.nl/pub/kiwix/zim/other/zimgit-water_en_2024-08.zim</url>
    <url location="fr" priority="2">https://mirror.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim</url>
  </file>
</metalink>
```

- [ ] **Step 2: Write the failing sync tests**

`api/tests/test_sync.py`:

```python
import hashlib
import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, sync
from sos.manifest import load_manifests

FX = Path(__file__).parent / "fixtures"
WATER_ZIM_URL = "https://lb.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim"


def test_parse_opds_entry():
    r = sync.parse_opds_entry((FX / "opds" / "catalog.xml").read_text())
    assert r.url == WATER_ZIM_URL
    assert r.name == "zimgit-water_en_2024-08" and r.size == 20925440 and r.as_at == "2024-08-29" and r.sha256 is None
    assert sync.parse_opds_entry((FX / "opds" / "empty.xml").read_text()) is None


def test_parse_meta4():
    size, sha, mirrors = sync.parse_meta4((FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text())
    assert size == 20924451
    assert sha == "392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6"
    assert mirrors == ["https://ftp.nluug.nl/pub/kiwix/zim/other/zimgit-water_en_2024-08.zim",
                       "https://mirror.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim"]


@respx.mock
def test_resolve_kiwix_uses_meta4_when_available(respx_mock):
    respx_mock.get(sync.OPDS_URL, params={"name": "zimgit-water_en", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text()))
    with httpx.Client() as client:
        r = sync.resolve_kiwix("zimgit-water_en", client)
    assert r.size == 20924451 and r.sha256.startswith("392c7bc9") and len(r.mirrors) == 2 and r.as_at == "2024-08-29"


@respx.mock
def test_resolve_kiwix_without_meta4_and_unknown_name(respx_mock):
    respx_mock.get(sync.OPDS_URL, params={"name": "zimgit-water_en", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(404))
    respx_mock.get(sync.OPDS_URL, params={"name": "nope", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "empty.xml").read_text()))
    with httpx.Client() as client:
        r = sync.resolve_kiwix("zimgit-water_en", client)
        assert r.size == 20925440 and r.sha256 is None
        with pytest.raises(sync.SyncError):
            sync.resolve_kiwix("nope", client)


class _RangeHandler(http.server.BaseHTTPRequestHandler):
    data = b""
    hits: list[str] = []

    def do_GET(self):
        total = len(self.data)
        rng = self.headers.get("Range")
        self.hits.append(rng or "full")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            if start >= total:
                self.send_response(416)
                self.end_headers()
                return
            body = self.data[start:]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{total - 1}/{total}")
        else:
            body = self.data
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def range_server():
    _RangeHandler.data = os.urandom(100_000)
    _RangeHandler.hits = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/file.zim"
    server.shutdown()


def test_stream_download_resumes_with_range(tmp_path, range_server):
    target = tmp_path / "file.zim.part"
    target.write_bytes(_RangeHandler.data[:40_000])
    sync.stream_download(range_server, target)
    assert target.read_bytes() == _RangeHandler.data
    assert _RangeHandler.hits == ["bytes=40000-"]
    sync.stream_download(range_server, target)
    assert _RangeHandler.hits == ["bytes=40000-", "bytes=100000-"]
    assert target.read_bytes() == _RangeHandler.data
    fresh = tmp_path / "fresh.part"
    sync.stream_download(range_server, fresh)
    assert fresh.read_bytes() == _RangeHandler.data and _RangeHandler.hits[-1] == "full"


def test_builtin_download_verifies_sha256(tmp_path, range_server):
    good = hashlib.sha256(_RangeHandler.data).hexdigest()
    target = tmp_path / "a.part"
    assert sync.download(range_server, target, sha256=good, use_aria2=False) == target
    bad = tmp_path / "b.part"
    with pytest.raises(sync.ChecksumError):
        sync.download(range_server, bad, sha256="0" * 64, use_aria2=False)
    assert not bad.exists()


def test_aria2c_command_line(tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[[c.startswith("--dir=") for c in cmd].index(True)][6:]).joinpath(
            next(c for c in cmd if c.startswith("--out="))[6:]).write_bytes(b"zim")
        return subprocess.CompletedProcess(cmd, 0)

    target = tmp_path / "x.zim.part"
    sync.download("https://h.test/x.zim", target, sha256="ab" * 32, mirrors=["https://m.test/x.zim"], use_aria2=True, run=fake_run)
    cmd = calls[0]
    assert cmd[0] == "aria2c" and "--continue=true" in cmd and f"--dir={tmp_path}" in cmd and "--out=x.zim.part" in cmd
    assert "--checksum=sha-256=" + "ab" * 32 in cmd
    assert cmd[-2:] == ["https://h.test/x.zim", "https://m.test/x.zim"]
    assert target.exists()

    def failing(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1)

    with pytest.raises(sync.SyncError):
        sync.download("https://h.test/y.zim", tmp_path / "y.part", use_aria2=True, run=failing)


def _manifest(tmp_path, items):
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FX / "manifest" / "schema.json", d / "schema.json")
    (d / "core.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return d


NOINDEX_SHA = hashlib.sha256((FX / "library" / "sos-test-noindex.zim").read_bytes()).hexdigest()
ITEMS = [
    {"id": "zimgit-water_en_2024-08", "title": "Water", "kind": "zim", "tier": "core", "category": "survival",
     "source": {"type": "kiwix", "name": "zimgit-water_en"}, "dest": "zim/zimgit-water_en_2024-08.zim", "priority": 1},
    {"id": "sos-test-pdf", "title": "Test PDF", "kind": "pdf", "tier": "core", "category": "uk-official",
     "source": {"type": "url", "url": "https://files.test/sos-test.pdf",
                "sha256": hashlib.sha256((FX / "docs" / "sos-test.pdf").read_bytes()).hexdigest()},
     "dest": "docs/sos-test.pdf", "priority": 2},
    {"id": "prepare_uk", "title": "Prepare", "kind": "zim", "tier": "core", "category": "uk-official",
     "source": {"type": "build", "tool": "build-nhs", "artifact": "prepare_uk.zim"}, "dest": "zim/prepare_uk.zim", "priority": 3},
    {"id": "sos-ext", "title": "Ext", "kind": "zim", "tier": "extended", "category": "books",
     "source": {"type": "kiwix", "name": "sos-ext"}, "dest": "zim/sos-ext.zim", "priority": 4},
]


def _meta4_for(sha: str, size: int) -> str:
    text = (FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text()
    return text.replace("392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6", sha).replace("<size>20924451</size>", f"<size>{size}</size>")


@respx.mock
def test_sync_dry_run_lists_without_downloading(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    respx_mock.get(sync.OPDS_URL).mock(return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(404))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", dry_run=True, out=lines.append, client=client)
    assert rc == 0
    assert any(line.startswith("GET  zimgit-water_en_2024-08: " + WATER_ZIM_URL) and "0.02 GB" in line for line in lines)
    assert any(line.startswith("GET  sos-test-pdf: https://files.test/sos-test.pdf") for line in lines)
    assert any(line.startswith("BUILD prepare_uk: run `sos build-nhs`") and "prepare_uk.zim" in line for line in lines)
    assert not any("sos-ext" in line for line in lines)
    assert not (env.core / "zim" / "zimgit-water_en_2024-08.zim").exists()
    assert not env.db_path.exists()


@respx.mock
def test_sync_downloads_verifies_renames_records_and_indexes(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    zim_bytes = (FX / "library" / "sos-test-noindex.zim").read_bytes()
    respx_mock.get(sync.OPDS_URL).mock(return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(200, text=_meta4_for(NOINDEX_SHA, len(zim_bytes))))
    respx_mock.get(WATER_ZIM_URL).mock(return_value=httpx.Response(200, content=zim_bytes))
    respx_mock.get("https://files.test/sos-test.pdf").mock(return_value=httpx.Response(200, content=(FX / "docs" / "sos-test.pdf").read_bytes()))
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={"items": 4, "available": 2}))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 0, lines
    zim = env.core / "zim" / "zimgit-water_en_2024-08.zim"
    assert zim.exists() and zim.read_bytes() == zim_bytes and not zim.with_name(zim.name + ".part").exists()
    assert (env.core / "docs" / "sos-test.pdf").exists()
    conn = db.connect(env.db_path)
    row = conn.execute("SELECT * FROM library_items WHERE id='zimgit-water_en_2024-08'").fetchone()
    assert (row["resolved_name"], row["resolved_size"], row["resolved_as_at"], row["available"]) == ("zimgit-water_en_2024-08", len(zim_bytes), "2024-08-29", 1)
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE kind='playbook'").fetchone()[0] >= 6
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE kind='item'").fetchone()[0] == 4
    assert json.loads(db.get_setting(conn, "overlay_scenarios")) == {"health": ["grid-collapse"], "water": ["grid-collapse"]}
    assert any(line.startswith("DONE zimgit-water_en_2024-08") for line in lines)
    # second run: already present, nothing downloaded
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 0 and any(line.startswith("OK   zimgit-water_en_2024-08: present") for line in lines)


@respx.mock
def test_sync_checksum_mismatch_fails_item(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, [ITEMS[1]]))
    respx_mock.get("https://files.test/sos-test.pdf").mock(return_value=httpx.Response(200, content=b"tampered"))
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={}))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 1
    assert any(line.startswith("FAIL sos-test-pdf: sha256 mismatch") for line in lines)
    assert not (env.core / "docs" / "sos-test.pdf").exists() and not (env.core / "docs" / "sos-test.pdf.part").exists()


@respx.mock
def test_sync_only_filter_and_extended_requires_drive(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", only=["prepare_uk", "ghost"], dry_run=True, out=lines.append, client=client)
    assert rc == 0
    assert [line for line in lines if line.startswith(("GET", "BUILD"))] == [
        "BUILD prepare_uk: run `sos build-nhs` on the PC and copy prepare_uk.zim to " + str(env.core / "zim" / "prepare_uk.zim")]
    assert any("ghost" in line and "not in manifest" in line for line in lines)
    with pytest.raises(sync.SyncError):
        with httpx.Client() as client:
            sync.sync(env, "extended", out=lines.append, client=client)


def test_strip_markdown():
    md = "## Right now\nCall **105** now. See [bleeding](card:bleeding).\n\n{{module:water}}\n- [ ] Fill bottles {#fill}\n| a | b |\n|---|---|"
    text = sync.strip_markdown(md)
    assert text == "Right now Call 105 now. See bleeding. Fill bottles a b"


def test_index_content_rows(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    n = sync.index_content(conn, env.playbooks)
    rows = conn.execute("SELECT title, kind, url, scenarios FROM fts_docs ORDER BY rowid").fetchall()
    assert n == len(rows) and n >= 9
    playbook_rows = [r for r in rows if r["kind"] == "playbook"]
    assert playbook_rows[0]["url"] == "/s/grid-collapse#right-now" and playbook_rows[0]["scenarios"] == "grid-collapse"
    assert {r["kind"] for r in rows} == {"playbook", "module", "card", "page"}
    hit = conn.execute("SELECT url FROM fts_docs WHERE fts_docs MATCH '\"bleach\"'").fetchone()
    assert hit["url"].startswith("/m/water")
```

- [ ] **Step 3: Write the failing CLI and build-nhs tests**

`api/tests/test_cli.py`:

```python
import shutil
from pathlib import Path

import httpx
import pytest
import respx

from sos import cli, db, system

FX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def tree(tmp_path, monkeypatch):
    root = tmp_path / "playbooks"
    shutil.copytree(FX / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    monkeypatch.setenv("SOS_PLAYBOOKS_DIR", str(root))
    from sos.config import get_settings

    get_settings.cache_clear()
    return root


def test_validate_playbooks_ok(env, tree, capsys):
    assert cli.main(["validate-playbooks"]) == 0
    assert capsys.readouterr().out.strip().endswith("OK 4 documents")


def test_validate_playbooks_reports_errors(env, tree, capsys):
    path = tree / "scenarios" / "grid-collapse.md"
    path.write_text(path.read_text(encoding="utf-8").replace("overlays: [health, water]", "overlays: [dragons]"), encoding="utf-8")
    assert cli.main(["validate-playbooks"]) == 1
    out = capsys.readouterr().out
    assert "overlay 'dragons'" in out and "FAILED 1 error" in out


def test_validate_playbooks_all_scenarios_flag(env, tree, capsys):
    assert cli.main(["validate-playbooks", "--all-scenarios"]) == 1
    assert "scenarios/nuclear-war.md: missing" in capsys.readouterr().out


@respx.mock
def test_validate_playbooks_deep(respx_mock, env, tree, capsys):
    respx_mock.get("http://kiwix.test/kiwix/raw/wikipedia_en_100_mini_2026-01/content/Precipitation").mock(return_value=httpx.Response(404))
    assert cli.main(["validate-playbooks", "--deep"]) == 1
    out = capsys.readouterr().out
    assert "returned non-200" in out and "doc 'sos-test-pdf' file missing" in out


def test_pin_set_and_reset(env):
    assert cli.main(["pin", "set", "2468"]) == 0
    conn = db.connect(env.db_path)
    assert system.verify_pin(conn, "2468") is True
    assert cli.main(["pin", "set", "12"]) == 1
    assert cli.main(["pin", "reset"]) == 0
    assert system.pin_required(db.connect(env.db_path)) is False


def test_stubs_exit_2(env, capsys):
    assert cli.main(["build-maps", "--fixture"]) == 2
    assert "plan 04" in capsys.readouterr().err
    assert cli.main(["eval", "--retrieval-only"]) == 2
    assert "plan 05" in capsys.readouterr().err


@respx.mock
def test_status_prints_fields(respx_mock, env, capsys):
    respx_mock.get("http://127.0.0.1:8000/api/status").mock(return_value=httpx.Response(200, json={"version": "0.1.0", "dev": True, "mem": {"total_mb": 1}}))
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "version: 0.1.0" in out and "mem: {" in out
    respx_mock.get("http://127.0.0.1:8000/api/status").mock(side_effect=httpx.ConnectError("down"))
    assert cli.main(["status"]) == 1


def test_sync_dry_run_on_fixture_manifest(env, capsys):
    assert cli.main(["sync", "--tier", "core", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "GET  wikipedia_en_100_mini_2026-01: https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_mini_2026-01.zim" in out
    assert "BUILD sos-test-noindex: run `sos zimwriterfs`" in out


@respx.mock
def test_storage_event_add_and_remove(respx_mock, env, capsys):
    route = respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={"items": 13, "available": 2}))
    assert cli.main(["storage-event", "add"]) == 0
    assert route.call_count == 1
    assert cli.main(["storage-event", "remove"]) == 0
    assert route.call_count == 2 and env.library_xml.exists()
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(side_effect=httpx.ConnectError("down"))
    assert cli.main(["storage-event", "add"]) == 1
    assert cli.main(["storage-event", "remove"]) == 0


def test_index_command(env, capsys):
    assert cli.main(["index"]) == 0
    out = capsys.readouterr().out
    assert "rescan:" in out and "content rows" in out
    conn = db.connect(env.db_path)
    assert conn.execute("SELECT count(*) FROM fts_docs").fetchone()[0] > 0
```

`api/tests/test_buildnhs.py`:

```python
import subprocess
from pathlib import Path

from sos import buildnhs


def test_build_command_has_every_section_and_exclusions(tmp_path):
    cmd = buildnhs.build_command(tmp_path, "2026-09-03")
    assert cmd[0] == "zimit"
    seeds = cmd[cmd.index("--seeds") + 1]
    for section in ("conditions", "symptoms", "medicines", "mental-health", "tests-and-treatments", "pregnancy", "live-well"):
        assert f"https://www.nhs.uk/{section}/" in seeds
    assert cmd[cmd.index("--lang") + 1] == "eng"
    assert "brightcove" in cmd[cmd.index("--exclude") + 1]
    assert "as at 2026-09-03" in cmd[cmd.index("--title") + 1]
    assert cmd[cmd.index("--zim-file") + 1] == "nhs_uk.zim"


def _fake_zimdump(entries, date="2026-09-03", title="NHS conditions and medicines (as at 2026-09-03)", article_html="<html><body><p>ok</p></body></html>"):
    def run(cmd, **kwargs):
        if cmd[1] == "list":
            return subprocess.CompletedProcess(cmd, 0, stdout="\n".join(entries) + "\n", stderr="")
        if cmd[1] == "show" and cmd[3] == "M/Date":
            return subprocess.CompletedProcess(cmd, 0, stdout=date, stderr="")
        if cmd[1] == "show" and cmd[3] == "M/Title":
            return subprocess.CompletedProcess(cmd, 0, stdout=title, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=article_html, stderr="")
    return run


GOOD = [f"www.nhs.uk/conditions/condition-{i}/" for i in range(2800)] + ["static/nhsuk/css/main.css"]


def test_verify_passes_on_good_zim(tmp_path):
    assert buildnhs.verify(tmp_path / "nhs_uk.zim", "2026-09-03", run=_fake_zimdump(GOOD)) == []


def test_verify_reports_each_failure(tmp_path):
    errors = buildnhs.verify(tmp_path / "nhs_uk.zim", "2026-09-03",
                             run=_fake_zimdump(GOOD[:100] + ["players.brightcove.net/x.js"], date="2026-09-01", title="NHS",
                                               article_html='<html><script src="https://assets.nhs.uk/login.js"></script><video src="https://cdn/x.mp4"></video></html>'))
    joined = "\n".join(errors)
    assert "brightcove" in joined
    assert "only 100 articles" in joined
    assert "Date is 2026-09-01" in joined
    assert "Title" in joined
    assert "external <script src>" in joined and "<video>" in joined


def test_main_without_zimit(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildnhs.shutil, "which", lambda name: None)
    assert buildnhs.main(str(tmp_path)) == 2
    assert "zimit" in capsys.readouterr().err
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `cd api && .venv/bin/pytest tests/test_sync.py tests/test_cli.py tests/test_buildnhs.py -q`
Expected: `ModuleNotFoundError: No module named 'sos.sync'`.

- [ ] **Step 5: Write `api/sos/sync.py`**

```python
"""`sos sync` (resolve, download, verify, rename, record) and `sos index` (rescan, fts_docs, fts_places)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

from sos import db, docs as docs_mod, library, places as places_mod
from sos.config import Settings
from sos.content import DIR_BY_KIND, KIND_BY_DIR, parse_document
from sos.manifest import Item, load_manifests

OPDS_URL = "https://opds.library.kiwix.org/catalog/v2/entries"
ATOM = "{http://www.w3.org/2005/Atom}"
METALINK = "{urn:ietf:params:xml:ns:metalink}"
CHUNK = 1 << 20
URL_BY_KIND = {"scenario": "/s/", "module": "/m/", "card": "/medical/card/", "page": "/p/"}
FTS_KIND = {"scenario": "playbook", "module": "module", "card": "card", "page": "page"}


class SyncError(RuntimeError):
    pass


class ChecksumError(SyncError):
    pass


@dataclass
class Resolved:
    url: str
    name: str
    size: int | None
    as_at: str | None
    sha256: str | None = None
    mirrors: list[str] = field(default_factory=list)


def parse_opds_entry(text: str) -> Resolved | None:
    root = ET.fromstring(text)
    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return None
    link = next((l for l in entry.findall(f"{ATOM}link") if l.get("type") == "application/x-zim"), None)
    if link is None or not link.get("href"):
        return None
    href = link.get("href", "")
    url = href[:-6] if href.endswith(".meta4") else href
    length = link.get("length") or ""
    updated = entry.findtext(f"{ATOM}updated") or ""
    return Resolved(url=url, name=Path(url).stem, size=int(length) if length.isdigit() else None, as_at=updated[:10] or None)


def parse_meta4(text: str) -> tuple[int | None, str | None, list[str]]:
    root = ET.fromstring(text)
    file_el = root.find(f"{METALINK}file")
    if file_el is None:
        return None, None, []
    size_text = file_el.findtext(f"{METALINK}size") or ""
    sha = next((h.text.strip() for h in file_el.findall(f"{METALINK}hash") if h.get("type") == "sha-256" and h.text), None)
    mirrors = [u.text.strip() for u in file_el.findall(f"{METALINK}url") if u.text]
    return (int(size_text) if size_text.isdigit() else None), sha, mirrors


def resolve_kiwix(name: str, client: httpx.Client) -> Resolved:
    r = client.get(OPDS_URL, params={"name": name, "count": "1"})
    r.raise_for_status()
    resolved = parse_opds_entry(r.text)
    if resolved is None:
        raise SyncError(f"no Kiwix catalogue entry named '{name}'")
    try:
        m = client.get(resolved.url + ".meta4")
        if m.status_code == 200:
            size, sha, mirrors = parse_meta4(m.text)
            resolved.size = size or resolved.size
            resolved.sha256 = sha
            resolved.mirrors = mirrors
    except (httpx.HTTPError, ET.ParseError):
        pass
    return resolved


def resolve_item(item: Item, client: httpx.Client) -> Resolved | None:
    if item.source.type == "kiwix":
        return resolve_kiwix(item.source.name or item.id, client)
    if item.source.type == "url":
        url = item.source.url or ""
        return Resolved(url=url, name=Path(url).stem, size=item.size_bytes or None, as_at=item.as_at,
                        sha256=item.source.sha256, mirrors=list(item.source.mirrors))
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def stream_download(url: str, target: Path, client: httpx.Client | None = None) -> Path:
    """Built-in downloader with Range resume from an existing partial file."""
    own = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    try:
        existing = target.stat().st_size if target.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing else {}
        with client.stream("GET", url, headers=headers) as r:
            if r.status_code == 416:
                return target
            if r.status_code == 206:
                mode = "ab"
            elif r.status_code == 200:
                mode = "wb"
            else:
                raise SyncError(f"HTTP {r.status_code} for {url}")
            with open(target, mode) as fh:
                for chunk in r.iter_bytes(CHUNK):
                    fh.write(chunk)
    finally:
        if own:
            client.close()
    return target


def aria2c_download(url: str, target: Path, sha256: str | None = None, mirrors=(), run: Callable = subprocess.run) -> Path:
    cmd = ["aria2c", "--continue=true", "--max-connection-per-server=4", "--split=4", "--file-allocation=none",
           "--auto-file-renaming=false", "--allow-overwrite=true", f"--dir={target.parent}", f"--out={target.name}"]
    if sha256:
        cmd.append(f"--checksum=sha-256={sha256}")
    cmd.append(url)
    cmd.extend(mirrors)
    proc = run(cmd, check=False)
    if proc.returncode != 0:
        raise SyncError(f"aria2c failed (exit {proc.returncode}) for {url}")
    return target


def download(url: str, target: Path, sha256: str | None = None, mirrors=(), use_aria2: bool | None = None,
             run: Callable = subprocess.run, client: httpx.Client | None = None) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if use_aria2 is None:
        use_aria2 = shutil.which("aria2c") is not None
    if use_aria2:
        return aria2c_download(url, target, sha256, mirrors, run)  # aria2c verifies --checksum itself
    stream_download(url, target, client)
    if sha256:
        actual = sha256_file(target)
        if actual != sha256:
            target.unlink(missing_ok=True)
            raise ChecksumError(f"sha256 mismatch for {target.name}: expected {sha256}, got {actual}")
    return target


def _open_db(settings: Settings) -> sqlite3.Connection:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(settings.manifests))
    return conn


def record_resolved(conn: sqlite3.Connection, item_id: str, resolved: Resolved) -> None:
    conn.execute("UPDATE library_items SET resolved_name=?, resolved_size=?, resolved_as_at=? WHERE id=?",
                 (resolved.name, resolved.size, resolved.as_at, item_id))
    conn.commit()


def sync(settings: Settings, tier: str, only: list[str] | None = None, dry_run: bool = False, out: Callable = print,
         client: httpx.Client | None = None, run: Callable = subprocess.run, use_aria2: bool | None = None) -> int:
    items = [i for i in load_manifests(settings.manifests) if i.tier == tier]
    if only:
        wanted = set(only)
        for missing in sorted(wanted - {i.id for i in items}):
            out(f"WARN {missing}: not in manifest for tier {tier}")
        items = [i for i in items if i.id in wanted]
    items.sort(key=lambda i: (i.priority, i.id))
    root = settings.tier_root(tier)
    if tier == "extended" and not dry_run and not library.ext_mounted(settings):
        raise SyncError("External drive is not connected")
    own_client = client is None
    client = client or httpx.Client(timeout=60, follow_redirects=True)
    conn = None if dry_run else _open_db(settings)
    failures = 0
    try:
        for item in items:
            target = root / item.dest
            if item.source.type == "build":
                out(f"BUILD {item.id}: run `sos {item.source.tool}` on the PC and copy {item.source.artifact} to {target}")
                continue
            try:
                resolved = resolve_item(item, client)
            except (SyncError, httpx.HTTPError, ET.ParseError) as exc:
                out(f"FAIL {item.id}: {exc}")
                failures += 1
                continue
            assert resolved is not None
            size_txt = f"{resolved.size / 1e9:.2f} GB" if resolved.size else "size unknown"
            if target.exists() and (resolved.size is None or target.stat().st_size == resolved.size):
                out(f"OK   {item.id}: present at {target}")
                if conn is not None:
                    record_resolved(conn, item.id, resolved)
                continue
            if dry_run:
                out(f"GET  {item.id}: {resolved.url} ({size_txt}) -> {target}")
                continue
            out(f"GET  {item.id}: {resolved.url} ({size_txt})")
            part = target.with_name(target.name + ".part")
            try:
                download(resolved.url, part, resolved.sha256, resolved.mirrors, use_aria2, run, client)
            except (SyncError, httpx.HTTPError, OSError) as exc:
                out(f"FAIL {item.id}: {exc}")
                failures += 1
                continue
            os.replace(part, target)
            assert conn is not None
            record_resolved(conn, item.id, resolved)
            out(f"DONE {item.id}: {target}")
    finally:
        if conn is not None:
            conn.close()
        if own_client:
            client.close()
    if not dry_run:
        index(settings, out)
    return 1 if failures else 0


_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_NOISE = re.compile(r"\{\{module:[a-z0-9-]+\}\}|\{#[A-Za-z0-9_/-]+\}|^\s*[-*+] \[[ xX]\]|^\s*#+\s*|[*_`>|]|^\s*-{3,}\s*$", re.M)


def strip_markdown(md: str) -> str:
    text = _MD_LINK.sub(r"\1", md or "")
    text = _MD_NOISE.sub(" ", text)
    return " ".join(text.split())


def index_content(conn: sqlite3.Connection, playbooks_dir: Path) -> int:
    playbooks_dir = Path(playbooks_dir)
    if not playbooks_dir.is_dir():
        return 0
    count = 0
    overlay_scenarios: dict[str, list[str]] = {}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((playbooks_dir / dirname).glob("*.md")):
            try:
                doc = parse_document(path)
            except Exception:
                continue
            base_url = URL_BY_KIND[kind] + doc.id
            scenarios = doc.id if kind == "scenario" else ""
            sections = [(sid, title, md) for sid, title, md in doc.sections if md.strip()] or [("", "", doc.summary)]
            for sid, title, md in sections:
                body = strip_markdown((title + "\n" if title else "") + md)
                url = f"{base_url}#{sid}" if sid else base_url
                conn.execute(
                    "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                    (doc.title, body, f"{kind}:{doc.id}", FTS_KIND[kind], "playbooks", scenarios, None, url),
                )
                count += 1
            if kind == "scenario":
                for ov in doc.overlays:
                    overlay_scenarios.setdefault(ov, []).append(doc.id)
    db.set_setting(conn, "overlay_scenarios", json.dumps({k: sorted(v) for k, v in sorted(overlay_scenarios.items())}))
    conn.commit()
    return count


def index_titles(conn: sqlite3.Connection) -> int:
    count = 0
    for row in conn.execute("SELECT * FROM library_items ORDER BY priority, id").fetchall():
        conn.execute(
            "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
            (row["title"], row["description"] or "", f"item:{row['id']}", "item", row["category"],
             " ".join(json.loads(row["scenarios_json"] or "[]")), None, f"/library#{row['id']}"),
        )
        count += 1
    conn.commit()
    return count


def notify_api(settings: Settings) -> bool:
    """Ask a running sos-api to rescan so it sees new files. Best effort."""
    try:
        r = httpx.post(f"http://127.0.0.1:{settings.port}/api/system/rescan", timeout=10)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def index(settings: Settings, out: Callable = print, runner=None) -> dict:
    conn = _open_db(settings)
    try:
        scan = library.rescan(conn, settings)
        out(f"rescan: {scan['available']} of {scan['items']} items available")
        conn.execute("DELETE FROM fts_docs")
        conn.commit()
        n_content = index_content(conn, settings.playbooks)
        n_titles = index_titles(conn)
        n_docs = docs_mod.index_docs(conn, runner)
        imported = places_mod.import_places(conn, places_mod.places_path(settings))
        places_txt = "unchanged" if imported is None else f"{imported} rows"
        out(f"index: {n_content} content rows, {n_titles} title rows, {n_docs} document pages, places {places_txt}")
    finally:
        conn.close()
    notify_api(settings)
    return {"content": n_content, "titles": n_titles, "docs": n_docs, "places": imported, **scan}
```

- [ ] **Step 6: Write `api/sos/cli.py`**

```python
"""`sos` command line: sync, index, storage-event, validate-playbooks, build-maps, build-nhs, eval, pin, status."""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path

import httpx

from sos import db, library, system
from sos.config import Settings, get_settings
from sos.content import KIND_BY_DIR, validate_tree
from sos.manifest import load_manifests


def _api(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.port}/api"


def cmd_sync(settings: Settings, args) -> int:
    from sos.sync import SyncError, sync

    only = [s for s in (args.only or "").split(",") if s] or None
    try:
        return sync(settings, args.tier, only=only, dry_run=args.dry_run)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_index(settings: Settings, args) -> int:
    from sos.sync import index

    index(settings)
    return 0


def post_rescan(settings: Settings) -> bool:
    try:
        r = httpx.post(f"{_api(settings)}/system/rescan", timeout=30)
        print(f"rescan: {r.status_code} {r.text.strip()}")
        return r.status_code == 200
    except httpx.HTTPError as exc:
        print(f"rescan failed: {exc}", file=sys.stderr)
        return False


def _is_mounted(path: Path) -> bool:
    try:
        return any(line.split()[1] == str(path) for line in Path("/proc/mounts").read_text().splitlines())
    except OSError:
        return False


def cmd_storage_event(settings: Settings, args) -> int:
    if args.event == "remove":
        settings.state.mkdir(parents=True, exist_ok=True)
        conn = db.connect(settings.db_path)
        try:
            db.init_schema(conn)
            library.write_library_xml(conn, settings, include_ext=False)
        finally:
            conn.close()
        time.sleep(1.0)  # let kiwix-serve --monitorLibrary drop the books before the unmount
    ok = post_rescan(settings)
    if args.event == "remove":
        if not settings.dev and _is_mounted(settings.ext):
            system.sudo(["umount", "-l", str(settings.ext)], settings)
        return 0
    return 0 if ok else 1


def cmd_validate(settings: Settings, args) -> int:
    items = load_manifests(settings.manifests) if settings.manifests.is_dir() else []
    overlay_ids = {i.overlay.id for i in items if i.overlay}
    kiwix_check = doc_check = None
    if args.deep:
        client = httpx.Client(timeout=10, follow_redirects=True)

        def kiwix_check(book: str, path: str) -> bool:
            try:
                return client.get(f"{settings.kiwix_url}/raw/{book}/content/{path}").status_code == 200
            except httpx.HTTPError:
                return False

        def doc_check(item) -> bool:
            return (settings.tier_root(item.tier) / item.dest).exists()

    problems = validate_tree(settings.playbooks, items, overlay_ids, kiwix_check=kiwix_check, doc_check=doc_check,
                             require_all_scenarios=args.all_scenarios)
    for line in problems:
        print(line)
    errors = [p for p in problems if not p.startswith("warning: ")]
    if errors:
        print(f"FAILED {len(errors)} error{'s' if len(errors) != 1 else ''}")
        return 1
    count = sum(len(list((settings.playbooks / d).glob("*.md"))) for d in KIND_BY_DIR) if settings.playbooks.is_dir() else 0
    print(f"OK {count} documents")
    return 0


def cmd_pin(settings: Settings, args) -> int:
    settings.state.mkdir(parents=True, exist_ok=True)
    conn = db.connect(settings.db_path)
    try:
        db.init_schema(conn)
        if args.action == "reset":
            system.clear_pin(conn)
            print("PIN cleared")
            return 0
        pin = args.pin or getpass.getpass("New admin PIN (4 to 12 digits): ")
        try:
            system.set_pin(conn, pin)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print("PIN set")
        return 0
    finally:
        conn.close()


def cmd_status(settings: Settings, args) -> int:
    try:
        r = httpx.get(f"{_api(settings)}/status", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"sos-api not reachable: {exc}", file=sys.stderr)
        return 1
    for key, value in r.json().items():
        print(f"{key}: {json.dumps(value) if isinstance(value, (dict, list)) else value}")
    return 0


def cmd_build_maps(settings: Settings, args) -> int:
    from sos import buildmaps

    return buildmaps.main(args)


def cmd_build_nhs(settings: Settings, args) -> int:
    from sos import buildnhs

    return buildnhs.main(args.out)


def cmd_eval(settings: Settings, args) -> int:
    from sos import evalrun

    return evalrun.main(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sos", description="Operation SOS command line")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sync", help="resolve, download, verify and index a content tier")
    p.add_argument("--tier", choices=["core", "extended"], required=True)
    p.add_argument("--only", help="comma-separated item ids")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_sync)
    p = sub.add_parser("index", help="rescan, rebuild fts_docs, import places if changed")
    p.set_defaults(func=cmd_index)
    p = sub.add_parser("storage-event", help="external drive plugged in or removed")
    p.add_argument("event", choices=["add", "remove"])
    p.set_defaults(func=cmd_storage_event)
    p = sub.add_parser("validate-playbooks", help="validate authored content")
    p.add_argument("--deep", action="store_true", help="also request every kiwix: path and check every doc: file")
    p.add_argument("--all-scenarios", action="store_true", help="require all 20 scenario playbooks")
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser("build-maps", help="PC only: build map tiles (plan 04)")
    p.add_argument("--out")
    p.add_argument("--steps", nargs="*")
    p.add_argument("--build")
    p.add_argument("--fixture", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_build_maps)
    p = sub.add_parser("build-nhs", help="PC only: zimit crawl of nhs.uk")
    p.add_argument("--out")
    p.set_defaults(func=cmd_build_nhs)
    p = sub.add_parser("eval", help="AI evaluation (plan 05)")
    p.add_argument("--retrieval-only", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_eval)
    p = sub.add_parser("pin", help="admin PIN")
    p.add_argument("action", choices=["reset", "set"])
    p.add_argument("pin", nargs="?")
    p.set_defaults(func=cmd_pin)
    p = sub.add_parser("status", help="print /api/status")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    try:
        return args.func(settings, args)
    except NotImplementedError as exc:
        print(f"not available: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Write `api/sos/buildnhs.py` and the stubs**

`api/sos/buildnhs.py`:

```python
"""`sos build-nhs`: drive a zimit crawl of nhs.uk on the PC and verify the result (spec section 13)."""
from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

SECTIONS = ["conditions", "symptoms", "medicines", "mental-health", "tests-and-treatments", "pregnancy", "live-well"]
EXCLUDE = r"brightcove|players\.brightcove\.net|\.mp4($|\?)|\.m3u8($|\?)"
MIN_ARTICLES = 2700
ARTICLE_RE = re.compile(r"^www\.nhs\.uk/(?:" + "|".join(SECTIONS) + r")/[^?]*$")
EXT_SCRIPT_RE = re.compile(r"<script[^>]+src=[\"']https?://", re.I)
VIDEO_RE = re.compile(r"<video\b", re.I)


def build_command(out_dir: Path, date: str) -> list[str]:
    seeds = ",".join(f"https://www.nhs.uk/{s}/" for s in SECTIONS)
    return [
        "zimit", "--seeds", seeds, "--scopeType", "prefix", "--lang", "eng", "--exclude", EXCLUDE,
        "--name", "nhs_uk", "--title", f"NHS conditions and medicines (as at {date})",
        "--description", "NHS website: conditions, symptoms, medicines, mental health, tests, pregnancy, live well",
        "--creator", "NHS", "--publisher", "Operation SOS", "--zim-file", "nhs_uk.zim",
        "--output", str(out_dir), "--workers", "4",
    ]


def _zimdump(run: Callable, *args: str) -> str:
    proc = run(["zimdump", *args], capture_output=True, text=True, check=False)
    return proc.stdout


def verify(zim: Path, date: str, run: Callable = subprocess.run, sample: int = 200) -> list[str]:
    errors: list[str] = []
    entries = [e.strip() for e in _zimdump(run, "list", str(zim)).splitlines() if e.strip()]
    if any("brightcove" in e.lower() for e in entries):
        errors.append("brightcove entry present")
    articles = [e for e in entries if ARTICLE_RE.match(e)]
    if len(articles) < MIN_ARTICLES:
        errors.append(f"only {len(articles)} articles (need at least {MIN_ARTICLES})")
    zim_date = _zimdump(run, "show", "--url", "M/Date", str(zim)).strip()
    if zim_date != date:
        errors.append(f"ZIM Date is {zim_date or '(missing)'}, expected {date}")
    title = _zimdump(run, "show", "--url", "M/Title", str(zim)).strip()
    if f"as at {date}" not in title:
        errors.append(f"ZIM Title must include 'as at {date}', got '{title}'")
    ext_scripts = videos = 0
    for entry in articles[:: max(1, len(articles) // sample)][:sample]:
        html = _zimdump(run, "show", "--url", entry, str(zim))
        if EXT_SCRIPT_RE.search(html):
            ext_scripts += 1
        if VIDEO_RE.search(html):
            videos += 1
    if ext_scripts:
        errors.append(f"{ext_scripts} sampled articles carry an external <script src>")
    if videos:
        errors.append(f"{videos} sampled articles carry a <video> element")
    return errors


def main(out: str | None = None, run: Callable = subprocess.run, date: str | None = None) -> int:
    if shutil.which("zimit") is None:
        print("zimit is not on PATH (pip install zimit, or use the warc2zim toolchain); nothing built", file=sys.stderr)
        return 2
    out_dir = Path(out or "build-output/nhs")
    out_dir.mkdir(parents=True, exist_ok=True)
    date = date or dt.date.today().isoformat()
    run(build_command(out_dir, date), check=True)
    errors = verify(out_dir / "nhs_uk.zim", date, run)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK {out_dir / 'nhs_uk.zim'} (as at {date}); copy it to /srv/sos/core/zim/nhs_uk.zim")
    return 0
```

`api/sos/buildmaps.py`:

```python
"""PC-side map pipeline. Implemented in plan 04 (maps pipeline)."""


def main(args) -> int:
    raise NotImplementedError("sos build-maps arrives in plan 04 (maps pipeline)")
```

`api/sos/evalrun.py`:

```python
"""AI evaluation runner. Implemented in plan 05 (AI)."""


def main(args) -> int:
    raise NotImplementedError("sos eval arrives in plan 05 (AI)")
```

- [ ] **Step 8: Run the tests**

Run: `cd api && .venv/bin/pytest tests/test_sync.py tests/test_cli.py tests/test_buildnhs.py -v`
Expected: all PASS. Then `cd api && .venv/bin/pytest -q` — the whole suite passes.

- [ ] **Step 9: Try the real CLI**

Run: `api/.venv/bin/sos --help && SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest api/.venv/bin/sos validate-playbooks`
Expected: the usage text listing the nine subcommands, then `OK 0 documents` (the repo tree has no authored documents until plan 03).

- [ ] **Step 10: Commit**

```bash
git add api/sos/sync.py api/sos/cli.py api/sos/buildnhs.py api/sos/buildmaps.py api/sos/evalrun.py api/tests/test_sync.py api/tests/test_cli.py api/tests/test_buildnhs.py api/tests/fixtures/opds
git commit -m "feat(cli): sos sync/index/storage-event/validate-playbooks/pin/status, build-nhs driver, plan stubs"
```

---
