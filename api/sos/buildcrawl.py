"""`sos build-crawl <id>`: build the "build" ZIM items in manifest/core.json on the PC (spec section 13).

Each item is a bounded crawl of a public UK government or NHS site. Two toolchains are supported:

* `zimit` when it is on PATH (needs Docker/browsertrix; the canonical openZIM route), and
* `wget --warc-file` + `warc2zim` otherwise, which is the route that works on a PC with no Docker
  and no root. Both produce ZIM entries whose paths are `<host>/<path>`, exactly the form the
  playbooks link as `kiwix:<id>/<host>/<path>`.
* `zimwriterfs` is the last-resort fallback when neither `zimit` nor `warc2zim` is installed: the
  mirrored file tree is packed directly and a redirect is written for every directory URL so that
  `<host>/<path>/` still resolves.

The crawl definitions (seeds, scope, excludes) live in CRAWLS below; the seed lists themselves stay
in tools/zimit/*.txt so they can be edited without touching code.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin, urlsplit

from sos.buildnhs import EXCLUDE as NHS_EXCLUDE
from sos.buildnhs import EXT_SCRIPT_RE, MIN_ARTICLES, SECTIONS, VIDEO_RE

USER_AGENT = "OperationSOS/0.1 (offline UK emergency knowledge box; +https://github.com/OperationSOS)"
# NHS (and other) pages embed JSON payloads whose escaped quotes wget parses as relative links,
# producing thousands of 404s like /conditions/x/%5C%22https://example.org%5C%22. Never request those.
JUNK = r"%5C%22|%22|%5C|/mailto:|/tel:"
ASSET_EXT = r"css|js|mjs|png|jpe?g|svg|gif|ico|webp|woff2?|ttf|eot"
REPO_ROOT = Path(__file__).resolve().parents[2]
LINK_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#>]+)""", re.IGNORECASE)


@dataclass(frozen=True)
class Crawl:
    """One buildable ZIM item."""

    id: str
    home: str                      # reader_home: the ZIM entry that is the main page
    home_url: str                  # the URL that entry came from
    title: str                     # {date} is substituted; must be <= 30 chars formatted
    description: str               # <= 80 chars (openZIM metadata convention)
    long_description: str
    creator: str
    seed_file: str | None = None   # relative to tools/zimit/
    seeds: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    recursive: bool = False
    level: int = 0                 # 0 = unlimited, only meaningful when recursive
    accept_regex: str | None = None
    reject_regex: str | None = None
    follow_regex: str | None = None    # second pass: links harvested out of the first pass
    follow_limit: int = 0
    wait: float = 1.0
    zimit_scope: str = "prefix"
    zimit_exclude: str = ""
    min_entries: int = 1
    article_re: str = ""
    tags: str = "uk;emergency;_category:uk-official"
    publisher: str = "Operation SOS"
    licence: str = "OGL v3"
    check_media: bool = False      # NHS: no external <script src>, no <video>
    extra_reject: tuple[str, ...] = field(default_factory=tuple)

    def seed_urls(self, repo: Path = REPO_ROOT) -> list[str]:
        urls = list(self.seeds)
        if self.seed_file:
            text = (repo / "tools" / "zimit" / self.seed_file).read_text()
            urls += [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
        seen: dict[str, None] = {}
        for u in urls:
            seen.setdefault(u, None)
        return list(seen)


_NHS_SECTIONS = "|".join(SECTIONS)

CRAWLS: dict[str, Crawl] = {
    "prepare_uk": Crawl(
        id="prepare_uk",
        home="prepare.campaign.gov.uk/",
        home_url="https://prepare.campaign.gov.uk/",
        title="Prepare UK as at {date}",
        description="UK government Prepare campaign advice",
        long_description=(
            "The government's own advice on kits, stored water, emergency alerts and power cuts, "
            "crawled from prepare.campaign.gov.uk."
        ),
        creator="Cabinet Office",
        seed_file="prepare_uk.txt",
        domains=("prepare.campaign.gov.uk",),
        recursive=True,
        reject_regex=r"(wp-json|xmlrpc|wp-admin|wp-login|/feed/|\?(p|s|replytocom|share)=)|" + JUNK,
        wait=1.0,
        min_entries=20,
        article_re=r"^prepare\.campaign\.gov\.uk/[^?]*$",
    ),
    "govuk_resilience": Crawl(
        id="govuk_resilience",
        home="www.gov.uk/alerts",
        home_url="https://www.gov.uk/alerts",
        title="GOV.UK as at {date}",
        description="GOV.UK and devolved emergency guidance",
        long_description=(
            "CMO power-outage advice, UKHSA flooding, heat, radiation and chemical guidance, FSA "
            "foraging, law summaries, LRF contacts, Emergency Alerts, nidirect, Ready Scotland, DWI "
            "and HSE pages, crawled from the seed list in tools/zimit/govuk_resilience.txt."
        ),
        creator="GOV.UK",
        seed_file="govuk_resilience.txt",
        domains=(
            "www.gov.uk", "assets.publishing.service.gov.uk", "www.nidirect.gov.uk",
            "ready.campaign.gov.scot", "www.dwi.gov.uk", "www.hse.gov.uk", "www.thepsr.co.uk",
        ),
        recursive=False,
        reject_regex=r"(/print$|/search/|/email-signup|\.atom$|/api/)|" + JUNK,
        follow_regex=(
            r"^https://(assets\.publishing\.service\.gov\.uk/[^?#]+\.pdf"
            r"|www\.gov\.uk/government/publications/[^/?#]+/[^/?#]+"
            r"|ready\.campaign\.gov\.scot/[^?#]+"
            r"|www\.dwi\.gov\.uk/[^?#]+"
            r"|www\.thepsr\.co\.uk/[^?#]+)$"
        ),
        follow_limit=300,
        wait=1.0,
        min_entries=40,
        article_re=r"^(www\.gov\.uk|www\.nidirect\.gov\.uk|ready\.campaign\.gov\.scot|www\.dwi\.gov\.uk|www\.hse\.gov\.uk|www\.thepsr\.co\.uk)/[^?]*$",
    ),
    "legislation_uk": Crawl(
        id="legislation_uk",
        home="www.legislation.gov.uk/ukpga/1988/33/section/139",
        home_url="https://www.legislation.gov.uk/ukpga/1988/33/section/139",
        title="Legislation as at {date}",
        description="Extracts from legislation.gov.uk",
        long_description=(
            "Theft Act, Wildlife and Countryside Act, CRoW, Deer Act, Firearms Acts, CJA 1988 s139, "
            "Offensive Weapons Act 2019, Civil Contingencies Act 2004 and the other Acts listed in "
            "tools/zimit/legislation_uk.txt, with the sections of each Act one level deep."
        ),
        creator="The National Archives",
        seed_file="legislation_uk.txt",
        domains=("www.legislation.gov.uk",),
        recursive=False,
        reject_regex=r"(/data\.(pdf|docx|xml|rdf|xht|htm)$|/defralex|\?view=|/changes/|/resources/|/made/data)|" + JUNK,
        follow_regex=r"^https://www\.legislation\.gov\.uk/[a-z]+/[^/?#]+/[^/?#]+/(section|part|schedule|chapter|crossheading)/[^?#]+$",
        follow_limit=900,
        wait=4.0,          # legislation.gov.uk robots.txt asks for Crawl-delay: 5
        min_entries=35,
        article_re=r"^www\.legislation\.gov\.uk/[^?]*$",
    ),
    "nhs_uk": Crawl(
        id="nhs_uk",
        home="www.nhs.uk/conditions/",
        home_url="https://www.nhs.uk/conditions/",
        title="NHS website as at {date}",
        description="NHS website conditions and medicines",
        long_description=(
            "NHS website: conditions, symptoms, medicines, mental health, tests and treatments, "
            "pregnancy and live well, as a dated snapshot built by sos build-crawl nhs_uk."
        ),
        creator="NHS",
        seeds=tuple(f"https://www.nhs.uk/{s}/" for s in SECTIONS),
        domains=("www.nhs.uk", "assets.nhs.uk"),
        recursive=True,
        accept_regex=(
            rf"^https?://(www\.nhs\.uk/({_NHS_SECTIONS})(/|$)"
            rf"|(www|assets)\.nhs\.uk/[^?]*\.({ASSET_EXT})(\?|$))"
        ),
        reject_regex=(
            NHS_EXCLUDE + r"|/service-search|/nhs-services/|/using-the-nhs/|/start4life"
            r"|/common-health-questions/|/contact-us/|/about-us/|/tools/|" + JUNK
        ),
        wait=1.0,
        zimit_exclude=NHS_EXCLUDE,
        min_entries=MIN_ARTICLES,
        article_re=r"^www\.nhs\.uk/(?:" + _NHS_SECTIONS + r")/[^?]*$",
        tags="nhs;health;_category:medical",
        check_media=True,
    ),
}


# --------------------------------------------------------------------------------------- commands

def zimit_command(crawl: Crawl, out_dir: Path, date: str, repo: Path = REPO_ROOT) -> list[str]:
    """The canonical openZIM route, used when zimit (and therefore Docker) is available."""
    cmd = [
        "zimit", "--seeds", ",".join(crawl.seed_urls(repo)), "--scopeType", crawl.zimit_scope,
        "--lang", "eng", "--name", crawl.id, "--title", crawl.title.format(date=date),
        "--description", crawl.description, "--creator", crawl.creator,
        "--publisher", crawl.publisher, "--zim-file", f"{crawl.id}.zim",
        "--output", str(out_dir), "--workers", "4",
    ]
    if crawl.zimit_exclude:
        cmd[cmd.index("--lang"):cmd.index("--lang")] = ["--exclude", crawl.zimit_exclude]
    return cmd


def wget_command(crawl: Crawl, work: Path, seeds_file: Path, warc_prefix: str,
                 recursive: bool | None = None) -> list[str]:
    """A polite mirror of the seed list into `work/files` while recording a WARC."""
    cmd = [
        "wget", "--no-verbose", "--input-file", str(seeds_file),
        "--directory-prefix", str(work / "files"), "--force-directories",
        "--page-requisites", "--span-hosts", "--domains", ",".join(crawl.domains),
        "--warc-file", str(work / warc_prefix), "--warc-max-size", "1G", "--warc-cdx",
        "--execute", "robots=on", "--user-agent", USER_AGENT,
        "--wait", str(crawl.wait), "--random-wait", "--tries", "3", "--timeout", "45",
    ]
    if recursive if recursive is not None else crawl.recursive:
        cmd += ["--recursive", "--no-parent", "--level", str(crawl.level)]
    if crawl.accept_regex:
        cmd += ["--accept-regex", crawl.accept_regex]
    if crawl.reject_regex:
        cmd += ["--reject-regex", crawl.reject_regex]
    return cmd


def warc2zim_command(crawl: Crawl, out_dir: Path, warcs: Iterable[Path], date: str,
                     warc2zim: str = "warc2zim") -> list[str]:
    return [
        warc2zim, "--name", crawl.id, "--output", str(out_dir), "--zim-file", f"{crawl.id}.zim",
        "--url", crawl.home_url, "--title", crawl.title.format(date=date),
        "--description", crawl.description, "--long-description", crawl.long_description,
        "--lang", "eng", "--creator", crawl.creator, "--publisher", crawl.publisher,
        "--tags", crawl.tags, "--source", crawl.home_url, "--continue-on-error",
        *[str(w) for w in warcs],
    ]


def directory_redirects(files: Path) -> list[tuple[str, str]]:
    """`<host>/<path>/` -> `<host>/<path>/index.html`, so directory URLs resolve in a zimwriterfs ZIM."""
    out: list[tuple[str, str]] = []
    for index in files.rglob("index.html"):
        rel = index.relative_to(files).as_posix()
        out.append((rel[: -len("index.html")], rel))
    return sorted(out)


def zimwriterfs_command(crawl: Crawl, files: Path, zim: Path, date: str,
                        redirects: Path | None = None) -> list[str]:
    cmd = [
        "zimwriterfs", "--welcome", crawl.home or "index.html", "--language", "eng",
        "--name", crawl.id, "--title", crawl.title.format(date=date),
        "--description", crawl.description, "--longDescription", crawl.long_description,
        "--creator", crawl.creator, "--publisher", crawl.publisher, "--tags", crawl.tags,
        "--source", crawl.home_url, "--skip-libmagic-check",
    ]
    if redirects is not None:
        cmd += ["--redirects", str(redirects)]
    return cmd + [str(files), str(zim)]


# ---------------------------------------------------------------------------------------- helpers

def file_url(files: Path, path: Path) -> str:
    """Reconstruct the URL a wget -x mirrored file came from."""
    rel = path.relative_to(files).as_posix()
    return "https://" + rel


def harvest_links(files: Path, pattern: str, limit: int) -> list[str]:
    """Pull the links matching `pattern` out of the pages downloaded by the first wget pass."""
    rx = re.compile(pattern)
    found: dict[str, None] = {}
    for page in sorted(files.rglob("*")):
        if not page.is_file() or page.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".svg",
                                                         ".pdf", ".css", ".js", ".woff", ".woff2",
                                                         ".ico", ".webp"}:
            continue
        try:
            text = page.read_text(errors="ignore")
        except OSError:
            continue
        if "<" not in text:
            continue
        base = file_url(files, page)
        for raw in LINK_RE.findall(text):
            url = urljoin(base, html.unescape(raw.strip()))
            url = urlsplit(url)._replace(fragment="").geturl()
            if rx.match(url):
                found.setdefault(url, None)
                if len(found) >= limit:
                    return list(found)
    return list(found)


def required_paths(crawl_id: str, playbooks: Path) -> list[str]:
    """Every `kiwix:<id>/<path>` the authored playbooks link into this ZIM."""
    if not playbooks.is_dir():
        return []
    rx = re.compile(r"kiwix:" + re.escape(crawl_id) + r"/([^)\"'\s]+)")
    found: set[str] = set()
    for md in playbooks.rglob("*.md"):
        found.update(rx.findall(md.read_text(errors="ignore")))
    return sorted(found)


# ----------------------------------------------------------------------------------- verification

def _zimdump(run: Callable, *args: str) -> str:
    proc = run(["zimdump", *args], capture_output=True, text=True, check=False)
    return proc.stdout or ""


def _metadata(run: Callable, zim: Path, key: str) -> str:
    """zim-tools changed how metadata is addressed; try both spellings."""
    for args in ((f"M/{key}",), ("--ns", "M", "--url", key)):
        if args[0].startswith("M/"):
            value = _zimdump(run, "show", "--url", args[0], str(zim)).strip()
        else:
            value = _zimdump(run, "show", *args, str(zim)).strip()
        if value and "not found" not in value.lower():
            return value
    return ""


def verify(crawl: Crawl, zim: Path, date: str, run: Callable = subprocess.run,
           required: Iterable[str] = (), sample: int = 40) -> list[str]:
    errors: list[str] = []
    entries = [e.strip() for e in _zimdump(run, "list", str(zim)).splitlines() if e.strip()]
    entry_set = set(entries)
    if crawl.zimit_exclude and any("brightcove" in e.lower() for e in entries):
        errors.append("brightcove entry present")
    articles = [e for e in entries if re.match(crawl.article_re, e)] if crawl.article_re else entries
    if len(articles) < crawl.min_entries:
        errors.append(f"only {len(articles)} articles (need at least {crawl.min_entries})")
    if crawl.home not in entry_set:
        errors.append(f"main page {crawl.home} is not an entry")
    missing = [p for p in required if p not in entry_set and p.rstrip("/") not in entry_set]
    if missing:
        errors.append(f"{len(missing)} playbook link(s) missing: {', '.join(missing[:8])}")
    zim_date = _metadata(run, zim, "Date")
    if zim_date != date:
        errors.append(f"ZIM Date is {zim_date or '(missing)'}, expected {date}")
    title = _metadata(run, zim, "Title")
    if f"as at {date}" not in title:
        errors.append(f"ZIM Title must include 'as at {date}', got '{title}'")
    if crawl.check_media and articles:
        ext_scripts = videos = 0
        step = max(1, len(articles) // sample)
        for entry in articles[::step][:sample]:
            page = _zimdump(run, "show", "--url", entry, str(zim))
            if EXT_SCRIPT_RE.search(page):
                ext_scripts += 1
            if VIDEO_RE.search(page):
                videos += 1
        if ext_scripts:
            errors.append(f"{ext_scripts} sampled articles carry an external <script src>")
        if videos:
            errors.append(f"{videos} sampled articles carry a <video> element")
    return errors


# ------------------------------------------------------------------------------------------ build

def _write_seeds(path: Path, urls: Iterable[str]) -> Path:
    path.write_text("\n".join(urls) + "\n")
    return path


def crawl_with_wget(crawl: Crawl, work: Path, run: Callable, repo: Path = REPO_ROOT) -> list[Path]:
    """Mirror the site into `work/files` and return the WARC files that were written."""
    (work / "files").mkdir(parents=True, exist_ok=True)
    seeds = _write_seeds(work / "seeds.txt", crawl.seed_urls(repo))
    # wget exits 8 on any server error response, which a partial-site crawl always sees.
    run(wget_command(crawl, work, seeds, "pages"), check=False)
    if crawl.follow_regex and crawl.follow_limit:
        extra = harvest_links(work / "files", crawl.follow_regex, crawl.follow_limit)
        already = set(crawl.seed_urls(repo))
        extra = [u for u in extra if u not in already]
        if extra:
            follow_seeds = _write_seeds(work / "follow.txt", extra)
            run(wget_command(crawl, work, follow_seeds, "follow", recursive=False), check=False)
    return sorted(work.glob("*.warc.gz")) or sorted(work.glob("*.warc"))


def build(crawl_id: str, out: str | Path | None = None, run: Callable = subprocess.run,
          date: str | None = None, playbooks: Path | None = None, repo: Path = REPO_ROOT,
          which: Callable[[str], str | None] = shutil.which, skip_crawl: bool = False) -> tuple[int, Path | None]:
    """Crawl and pack one item. Returns (exit code, path of the ZIM when one was written)."""
    crawl = CRAWLS[crawl_id]
    date = date or dt.date.today().isoformat()
    work = Path(out or f"build-output/{crawl_id}")
    work.mkdir(parents=True, exist_ok=True)
    zim_dir = work / "zim"
    zim_dir.mkdir(exist_ok=True)
    zim = zim_dir / f"{crawl_id}.zim"

    if which("zimit"):
        run(zimit_command(crawl, zim_dir, date, repo), check=True)
    else:
        warcs = sorted(work.glob("*.warc.gz")) if skip_crawl else crawl_with_wget(crawl, work, run, repo)
        warc2zim = which("warc2zim")
        if warc2zim and warcs:
            run(warc2zim_command(crawl, zim_dir, warcs, date, warc2zim), check=True)
        elif which("zimwriterfs"):
            redirects = work / "redirects.tsv"
            rows = directory_redirects(work / "files")
            redirects.write_text("".join(f"{path}\t\t{target}\n" for path, target in rows))
            run(zimwriterfs_command(crawl, work / "files", zim, date, redirects), check=True)
        else:
            print("neither zimit, warc2zim nor zimwriterfs is on PATH; nothing built", file=sys.stderr)
            return 2, None

    errors = verify(crawl, zim, date, run, required_paths(crawl_id, playbooks) if playbooks else [])
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        return 1, zim
    print(f"OK {zim} (as at {date})")
    return 0, zim


def main(crawl_id: str = "nhs_uk", out: str | None = None, run: Callable = subprocess.run,
         date: str | None = None, playbooks: Path | None = None, skip_crawl: bool = False) -> int:
    """`date` defaults to today; pass the crawl date when re-packing WARCs fetched earlier, because
    warc2zim takes the ZIM Date from the WARC records rather than from the day it runs."""
    if crawl_id not in CRAWLS:
        print(f"unknown crawl {crawl_id}; known: {', '.join(sorted(CRAWLS))}", file=sys.stderr)
        return 2
    return build(crawl_id, out, run, date, playbooks, skip_crawl=skip_crawl)[0]
