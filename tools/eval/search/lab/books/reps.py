"""The book representations under test: what text (or texts) stands for a book.  Pure functions of the catalogue row and the
extracted record, so the same definitions serve the embedding run, the tests of the winner and the report.

  a   today's household text: "<title> by <author>. <first 2,584 characters of the book>", cut to 2,584 (production)
  b1  title, author and LCC shelf name only (Survivor Library: the title read off the file name)
  b2  b1 plus the subjects the page exposes (Gutenberg dc.subject) or the Survivor Library category page(s) and its own title
  c0  b2 plus the first 1,000 characters of the book, as today
  c1  b2 plus the first real prose (title page, contents list, licence skipped), up to 1,500 characters
  c2  b1 plus that prose (no subjects), to split c1's gain between subjects and prose
  d   ten windows of ~1,500 characters across the book, each prefixed with the title (dt) or bare (dp)
"""
from __future__ import annotations
import re

TODAY = 2584
SHELF_SUBJECT_MAX = 400


def heading_today(row: dict) -> str:
    if "slug" in row:
        return re.sub(r"[-_]+", " ", row["slug"]).strip()
    author = (row.get("author") or "").strip()
    return f"{row['title']} by {author}" if author else row["title"]


def meta1(row: dict, shelf_names: dict) -> str:
    if "slug" in row:
        return row["slug_title"] + "."
    author = (row.get("author") or "").strip()
    head = f"{row['title']} by {author}" if author else row["title"]
    shelf = shelf_names.get(row.get("shelf") or "", "")
    return f"{head}. {shelf}." if shelf else f"{head}."


def meta2(row: dict, rec: dict, shelf_names: dict) -> str:
    if "slug" in row:
        cats = ", ".join(row.get("categories") or [])
        return f"{row['title']}." + (f" Category: {cats}." if cats else "")
    subj = "; ".join(rec.get("subjects") or [])[:SHELF_SUBJECT_MAX]
    return meta1(row, shelf_names) + (f" Subjects: {subj}." if subj else "")


def rep_texts(row: dict, rec: dict, shelf_names: dict) -> dict:
    today = (rec.get("today") or "")
    prose = rec.get("prose") or ""
    m1, m2 = meta1(row, shelf_names), meta2(row, rec, shelf_names)
    wins = list(rec.get("windows") or []) or [today[:1500] or m1]
    title = row["title"] if "slug" not in row else row["slug_title"]
    return {
        "a": f"{heading_today(row)}. {today[:TODAY]}"[:TODAY],
        "b1": m1,
        "b2": m2,
        "c0": f"{m2} {today[:1000]}".strip(),
        "c1": f"{m2} {prose}".strip(),
        "c2": f"{m1} {prose}".strip(),
        "dt": [f"{title}. {w}" for w in wins],
        "dp": wins,
    }
