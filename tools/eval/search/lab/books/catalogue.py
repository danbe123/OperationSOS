"""The household catalogue with the metadata the ZIMs expose but the household build ignores: for Survivor Library the
category pages (`index.php/library-<category>/`: a table of title and PDF link per book), for Gutenberg the books table
(title, author, LCC shelf) from the dev database, read-only.  `python catalogue.py` writes catalogue.json in the scratch dir.
Run with the API venv (needs libzim)."""
from __future__ import annotations
import html, json, re, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, DB_PATH   # noqa: E402

SL_ZIM = "/home/dan/sos-content/zim/survivorlibrary.com_en_all.zim"
ROW = re.compile(r'<td>([^<]*)</td><td>([^<]*)</td><td>[^<]*</td><td><a href="\.\./\.\./library/([^"]+?)\.pdf"')


def survivor_pdf_paths() -> list[str]:
    """Every /library/<slug>.pdf entry of the Survivor Library crawl (its books), walking the archive once."""
    from libzim.reader import Archive
    a = Archive(SL_ZIM)
    out = []
    for i in range(a.entry_count):
        e = a._get_entry_by_id(i)
        if not e.is_redirect and re.match(r"www\.survivorlibrary\.com/library/(.+)\.pdf$", e.path, re.I):
            out.append(e.path)
    return out


def survivor_categories() -> tuple[dict, dict]:
    """({slug: display title}, {slug: [category names]}) from every library-<category> page of the crawl."""
    from libzim.reader import Archive
    a = Archive(SL_ZIM)
    titles: dict[str, str] = {}
    cats: dict[str, list[str]] = {}
    for i in range(a.entry_count):
        e = a._get_entry_by_id(i)
        if e.is_redirect or not re.match(r"www\.survivorlibrary\.com/index\.php/library-[^/]+/$", e.path):
            continue
        page = bytes(e.get_item().content).decode("utf-8", "replace")
        name = html.unescape(re.search(r"<title>(.*?)</title>", page, re.S).group(1)).strip()
        name = re.sub(r"^Library-", "", name).replace("_", " ").strip()
        for _date, title, slug in ROW.findall(page):
            slug = html.unescape(slug)
            titles.setdefault(slug, html.unescape(title).replace("_", " ").strip())
            cats.setdefault(slug, [])
            if name not in cats[slug]:
                cats[slug].append(name)
    return titles, cats


def main() -> None:
    from sos.books import SHELF_NAMES
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    gut = [{"key": f"gutenberg_en_all:{r['id']}", "id": r["id"], "title": r["title"], "author": (r["author"] or "").strip(),
            "shelf": r["shelf"] or "", "shelf_name": SHELF_NAMES.get(r["shelf"] or "", ""), "html_path": r["html_path"],
            "popularity": r["popularity"]}
           for r in conn.execute("SELECT id,title,author,shelf,html_path,popularity FROM books WHERE zim='gutenberg_en_all' ORDER BY id")]
    ids = {l.strip() for l in open("/home/dan/sos-content/embeddings/household.ids") if l.strip()}
    titles, cats = survivor_categories()
    sl = []
    for line in survivor_pdf_paths():
        m = re.match(r"www\.survivorlibrary\.com/library/(.+)\.pdf$", line, re.I)
        if m:
            slug = m.group(1)
            sl.append({"key": f"survivorlibrary.com_en_all:{slug}", "slug": slug, "path": line,
                       "title": titles.get(slug) or re.sub(r"[-_]+", " ", slug).strip(),
                       "slug_title": re.sub(r"[-_]+", " ", slug).strip(), "categories": cats.get(slug, []),
                       "in_production_index": f"survivorlibrary.com_en_all:{slug}" in ids})
    for g in gut:
        g["in_production_index"] = g["key"] in ids
    out = {"gutenberg": gut, "survivor": sl}
    (SCRATCH / "books").mkdir(parents=True, exist_ok=True)
    (SCRATCH / "books/catalogue.json").write_text(json.dumps(out))
    print(len(gut), len(sl), "survivor with a category:", sum(1 for s in sl if s["categories"]),
          "with several:", sum(1 for s in sl if len(s["categories"]) > 1), "categories:", len({c for v in cats.values() for c in v}))


if __name__ == "__main__":
    main()
