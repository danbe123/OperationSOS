.RECIPEPREFIX := >
.PHONY: dev test e2e build fixtures deploy venv smoke
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

smoke:
> dev/smoke.sh

test: venv
> cd api && .venv/bin/pytest -q
> if [ -f web/package.json ]; then pnpm --dir web test -- --run; fi
> SOS_PLAYBOOKS_DIR=playbooks SOS_MANIFEST_DIR=manifest $(SOS) validate-playbooks --all-scenarios
> bash dev/smoke-selftest.sh

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
