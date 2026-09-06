import subprocess
from pathlib import Path

import pytest

from sos import buildcrawl

REPO = Path(__file__).resolve().parents[2]


class FakeRun:
    """Records every command instead of running it, so the crawl toolchain can be tested offline."""

    def __init__(self, outputs: dict | None = None):
        self.calls: list[list[str]] = []
        self.outputs = outputs or {}

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        stdout = ""
        if cmd[0] == "zimdump":
            stdout = self.outputs.get(tuple(cmd[1:3]), self.outputs.get(cmd[1], ""))
            if cmd[1] == "show":
                url = cmd[cmd.index("--url") + 1].removeprefix("M/")
                stdout = self.outputs.get(("show", url), self.outputs.get("show", ""))
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")


def test_every_build_item_in_the_manifest_has_a_crawl():
    import json

    items = json.loads((REPO / "manifest" / "core.json").read_text())["items"]
    build_zims = {i["id"] for i in items if i["source"]["type"] == "build" and i["kind"] == "zim"}
    assert build_zims == set(buildcrawl.CRAWLS)


@pytest.mark.parametrize("crawl_id", sorted(buildcrawl.CRAWLS))
def test_crawl_home_matches_the_manifest_reader_home_and_dest(crawl_id):
    import json

    items = {i["id"]: i for i in json.loads((REPO / "manifest" / "core.json").read_text())["items"]}
    item = items[crawl_id]
    crawl = buildcrawl.CRAWLS[crawl_id]
    assert crawl.home == item["reader_home"]
    assert item["dest"] == f"zim/{crawl_id}.zim"
    assert len(crawl.description) <= 80
    # zimscraperlib refuses a ZIM Title longer than 30 characters
    assert len(crawl.title.format(date="2026-09-05")) <= 30
    assert "as at 2026-09-05" in crawl.title.format(date="2026-09-05")


@pytest.mark.parametrize("crawl_id", sorted(buildcrawl.CRAWLS))
def test_seeds_are_read_and_cover_the_home_url(crawl_id):
    crawl = buildcrawl.CRAWLS[crawl_id]
    seeds = crawl.seed_urls(REPO)
    assert seeds
    assert all(s.startswith("https://") for s in seeds)
    assert len(set(seeds)) == len(seeds)


def test_nhs_wget_command_covers_every_section_and_excludes_video():
    crawl = buildcrawl.CRAWLS["nhs_uk"]
    cmd = buildcrawl.wget_command(crawl, Path("/w"), Path("/w/seeds.txt"), "pages")
    assert cmd[0] == "wget"
    assert "--recursive" in cmd and cmd[cmd.index("--level") + 1] == "0"
    accept = cmd[cmd.index("--accept-regex") + 1]
    for section in ("conditions", "symptoms", "medicines", "mental-health", "tests-and-treatments",
                    "pregnancy", "live-well"):
        assert section in accept
    reject = cmd[cmd.index("--reject-regex") + 1]
    assert "brightcove" in reject and "m3u8" in reject
    assert cmd[cmd.index("--user-agent") + 1].startswith("OperationSOS/")
    assert "robots=on" in cmd
    assert "--warc-file" in cmd


def test_page_scope_crawls_are_not_recursive():
    for crawl_id in ("govuk_resilience", "legislation_uk"):
        cmd = buildcrawl.wget_command(buildcrawl.CRAWLS[crawl_id], Path("/w"), Path("/w/s.txt"), "pages")
        assert "--recursive" not in cmd


def test_legislation_waits_for_the_robots_crawl_delay():
    cmd = buildcrawl.wget_command(buildcrawl.CRAWLS["legislation_uk"], Path("/w"), Path("/w/s.txt"), "p")
    assert float(cmd[cmd.index("--wait") + 1]) >= 4
    assert "--random-wait" in cmd


def test_warc2zim_command_sets_the_main_page_and_metadata(tmp_path):
    crawl = buildcrawl.CRAWLS["prepare_uk"]
    cmd = buildcrawl.warc2zim_command(crawl, tmp_path, [tmp_path / "a.warc.gz"], "2026-09-05")
    assert cmd[cmd.index("--url") + 1] == "https://prepare.campaign.gov.uk/"
    assert cmd[cmd.index("--name") + 1] == "prepare_uk"
    assert cmd[cmd.index("--zim-file") + 1] == "prepare_uk.zim"
    assert "as at 2026-09-05" in cmd[cmd.index("--title") + 1]
    assert cmd[cmd.index("--lang") + 1] == "eng"
    assert cmd[-1].endswith("a.warc.gz")


def test_zimit_command_is_used_when_zimit_is_present(tmp_path):
    run = FakeRun()
    buildcrawl.build("prepare_uk", tmp_path, run=run, date="2026-09-05",
                     which=lambda name: "/usr/bin/zimit" if name == "zimit" else None)
    assert run.calls[0][0] == "zimit"
    assert run.calls[0][run.calls[0].index("--scopeType") + 1] == "prefix"


def test_build_falls_back_to_wget_and_warc2zim(tmp_path):
    run = FakeRun()
    (tmp_path / "pages-00000.warc.gz").write_bytes(b"")
    which = {"warc2zim": "/venv/bin/warc2zim", "zimwriterfs": "/usr/bin/zimwriterfs"}
    buildcrawl.build("prepare_uk", tmp_path, run=run, date="2026-09-05", which=which.get)
    assert run.calls[0][0] == "wget"
    assert any(c[0].endswith("warc2zim") for c in run.calls)
    assert (tmp_path / "seeds.txt").read_text().startswith("https://prepare.campaign.gov.uk/")


def test_build_falls_back_to_zimwriterfs_with_directory_redirects(tmp_path):
    run = FakeRun()
    page = tmp_path / "files" / "prepare.campaign.gov.uk" / "coping-with-trauma" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<html></html>")
    buildcrawl.build("prepare_uk", tmp_path, run=run, date="2026-09-05",
                     which=lambda name: "/usr/bin/zimwriterfs" if name == "zimwriterfs" else None)
    assert any(c[0] == "zimwriterfs" for c in run.calls)
    redirects = (tmp_path / "redirects.tsv").read_text()
    assert "prepare.campaign.gov.uk/coping-with-trauma/\t\tprepare.campaign.gov.uk/coping-with-trauma/index.html" in redirects


def test_build_returns_2_when_no_toolchain_is_available(tmp_path, capsys):
    assert buildcrawl.build("prepare_uk", tmp_path, run=FakeRun(), which=lambda n: None)[0] == 2
    assert "warc2zim" in capsys.readouterr().err


def test_main_rejects_an_unknown_id(capsys):
    assert buildcrawl.main("nope") == 2
    assert "unknown crawl" in capsys.readouterr().err


def test_directory_redirects(tmp_path):
    for rel in ("host/a/index.html", "host/a/b/index.html", "host/a/style.css"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x")
    assert buildcrawl.directory_redirects(tmp_path) == [
        ("host/a/", "host/a/index.html"), ("host/a/b/", "host/a/b/index.html")]


def test_harvest_links_resolves_relative_urls_and_applies_the_limit(tmp_path):
    page = tmp_path / "www.gov.uk" / "government" / "publications" / "x" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text(
        '<a href="/government/publications/x/the-guidance">g</a>'
        '<a href="https://assets.publishing.service.gov.uk/media/1/leaflet.pdf">pdf</a>'
        '<a href="https://example.com/other">no</a>')
    found = buildcrawl.harvest_links(tmp_path, buildcrawl.CRAWLS["govuk_resilience"].follow_regex, 10)
    assert "https://www.gov.uk/government/publications/x/the-guidance" in found
    assert "https://assets.publishing.service.gov.uk/media/1/leaflet.pdf" in found
    assert not any("example.com" in u for u in found)
    assert len(buildcrawl.harvest_links(tmp_path, buildcrawl.CRAWLS["govuk_resilience"].follow_regex, 1)) == 1


def test_required_paths_reads_the_playbooks(tmp_path):
    (tmp_path / "scenario").mkdir()
    (tmp_path / "scenario" / "p.md").write_text(
        "see [x](kiwix:nhs_uk/www.nhs.uk/conditions/sepsis/) and [y](kiwix:prepare_uk/prepare.campaign.gov.uk/)")
    assert buildcrawl.required_paths("nhs_uk", tmp_path) == ["www.nhs.uk/conditions/sepsis/"]
    assert buildcrawl.required_paths("prepare_uk", tmp_path) == ["prepare.campaign.gov.uk/"]
    assert buildcrawl.required_paths("nhs_uk", tmp_path / "nope") == []


GOOD_NHS = (["www.nhs.uk/conditions/"]
            + [f"www.nhs.uk/conditions/condition-{i}/" for i in range(2800)] + ["static/main.css"])


def _outputs(entries, date="2026-09-05", title="NHS conditions and medicines (as at 2026-09-05)",
             article="<html><body>ok</body></html>"):
    out = {"list": "\n".join(entries) + "\n", ("show", "Date"): date, ("show", "Title"): title,
           "show": article}
    return out


def test_verify_passes_on_a_good_zim(tmp_path):
    run = FakeRun(_outputs(GOOD_NHS))
    assert buildcrawl.verify(buildcrawl.CRAWLS["nhs_uk"], tmp_path / "nhs_uk.zim", "2026-09-05", run,
                             required=["www.nhs.uk/conditions/condition-3/"]) == []


def test_verify_reports_every_failure(tmp_path):
    run = FakeRun(_outputs(GOOD_NHS[1:101] + ["players.brightcove.net/x.js"], date="2026-09-01",
                           title="NHS",
                           article='<html><script src="https://a/x.js"></script><video></video></html>'))
    errors = buildcrawl.verify(buildcrawl.CRAWLS["nhs_uk"], tmp_path / "nhs_uk.zim", "2026-09-05", run,
                               required=["www.nhs.uk/conditions/sepsis/"])
    joined = "\n".join(errors)
    assert "brightcove" in joined
    assert "only 100 articles" in joined
    assert "main page www.nhs.uk/conditions/ is not an entry" in joined
    assert "playbook link(s) missing" in joined and "sepsis" in joined
    assert "Date is 2026-09-01" in joined and "Title" in joined
    assert "external <script src>" in joined and "<video>" in joined


def test_verify_reads_metadata_from_the_new_zimdump_spelling(tmp_path):
    class OldStyle(FakeRun):
        def __call__(self, cmd, **kwargs):
            if cmd[1] == "show" and cmd[2] == "--url" and cmd[3].startswith("M/"):
                return subprocess.CompletedProcess(cmd, 1, stdout="Entry not found\n", stderr="")
            return super().__call__(cmd, **kwargs)

    run = OldStyle(_outputs(GOOD_NHS))
    assert buildcrawl.verify(buildcrawl.CRAWLS["nhs_uk"], tmp_path / "nhs_uk.zim", "2026-09-05", run) == []
