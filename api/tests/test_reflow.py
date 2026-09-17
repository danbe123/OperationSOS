"""The box's own reflow: page furniture out, lines into paragraphs, headings and lists kept, an EPUB
the indexer and the reader can open, and a quality gate that sends damaged OCR back to the PDF."""
import zipfile
from pathlib import Path

import pytest

from sos import docs, reflow
from sos.reflow import Block, blocks_from_pages, chapters, convert, looks_like_heading, split_pages, strip_furniture, text_quality, write_epub

BOOK = """CAMPING AND WOODCRAFT

CHAPTER I

THE TENT

Where no trees stand conveniently, a forked stake
can be placed at each end of the tent, the rope run
over the crotches and staked out as a guy fore-and-
aft. Often a natural support can be found.

It is better to set up shears and a ridge pole. The
guy is much in the way.
12
\f94 CAMPING AND WOODCRAFT

2. Choosing a site

A wedge tent should face the morning sun; a lean-to
should face the fire. Points to weigh:
• shelter from the wind
• dry ground, above the flood line and away from dead
trees
• water within a hundred yards

The ground should slope a little so that rain runs off
without cutting a trench round the tent. This is the
whole of it.
13
\f94 CAMPING AND WOODCRAFT

The second night is easier than the first, because
the camp is made.
14
\f95 CAMPING AND WOODCRAFT
Last page of the book, with a sentence that ends here.
15
"""


def _pages():
    return strip_furniture(split_pages(BOOK))


def test_furniture_is_the_running_head_and_the_page_numbers():
    pages = _pages()
    flat = [ln for p in pages for ln in p if ln.strip()]
    assert not any("CAMPING AND WOODCRAFT" in ln and ln.strip().startswith("9") for ln in flat)
    assert not any(ln.strip() in ("12", "13", "14", "15") for ln in flat)
    assert "THE TENT" in flat                      # a title that appears once is not furniture
    assert flat[0] == "CAMPING AND WOODCRAFT"      # the book's own title line on page one stays: it is not at a recurring edge on enough pages


def test_a_chapter_title_repeated_at_the_top_of_its_pages_is_kept_once():
    # A book long enough that a three-page chapter head is under the book-wide furniture share.
    words = "axe bread canvas dew ember flint gaiter hemp ice juniper knot lantern moss net oak pine quill".split()
    filler = [f"TOPIC {n}\n\nA page about {w}, with its own prose about {w} and nothing repeated.\n{40 + n}" for n, w in enumerate(words)]
    book = "\n\f".join([
        "SHELTER VENTILATION\nWITHOUT FILTERS\n\nNumerous tests have shown that the hazards are\nminor compared to the dangers.\n54",
        "SHELTER VENTILATION\nWITHOUT FILTERS\n\nA 1973 report stated this conclusion, and so on for\nanother page of prose.\n55",
        "SHELTER VENTILATION\nWITHOUT FILTERS\n\nMore of the chapter here, still under the same title.\n56",
        "WATER\n\nA new chapter begins with its own title, once.\n57",
    ] + filler)
    blocks = blocks_from_pages(strip_furniture(split_pages(book)))
    heads = [b.text for b in blocks if b.kind == "h1"]
    assert heads[:2] == ["SHELTER VENTILATION WITHOUT FILTERS", "WATER"]   # two lines, one title
    assert heads.count("SHELTER VENTILATION WITHOUT FILTERS") == 1
    assert sum(1 for b in blocks if b.kind == "p") == 4 + 17


def test_a_short_item_carries_on_when_the_next_line_starts_lowercase():
    page = ["On finding a casualty:", "• ensure your own safety;", "if necessary, remove the casualty from danger (but see",
            "the note below on enclosed spaces);", "• give immediate treatment to the casualty who is not",
            "breathing and/or whose heart has stopped;", "", "Others can be treated later, when the ship is safe and the",
            "sea is calm."]
    blocks = blocks_from_pages([page])
    items = [b.text for b in blocks if b.kind == "li"]
    assert items == ["ensure your own safety; if necessary, remove the casualty from danger (but see the note below on enclosed spaces);",
                     "give immediate treatment to the casualty who is not breathing and/or whose heart has stopped;"]
    assert blocks[-1] == Block("p", "Others can be treated later, when the ship is safe and the sea is calm.")


def test_convert_refuses_a_book_that_reflows_into_fragments(tmp_path):
    table = "\n".join(f"{i}. {i * 3} GHz." for i in range(400))
    with pytest.raises(ValueError, match="fragments"):
        convert(Path("x.pdf"), tmp_path / "t.epub", "Band plan", text=lambda p: table)


def test_lines_become_paragraphs_with_hyphens_mended_and_short_lines_closing_them():
    blocks = blocks_from_pages(_pages())
    paras = [b.text for b in blocks if b.kind == "p"]
    assert paras[0].startswith("Where no trees stand conveniently, a forked stake can be placed")
    assert "fore-and-aft" in paras[0]               # a real compound keeps its hyphen ("fore-and-" + "aft")
    assert paras[0].endswith("Often a natural support can be found.")
    assert paras[1] == "It is better to set up shears and a ridge pole. The guy is much in the way."
    assert "The ground should slope a little so that rain runs off without cutting a trench round the tent. This is the whole of it." in paras


def test_headings_lists_and_page_breaks():
    blocks = blocks_from_pages(_pages())
    assert Block("h1", "CAMPING AND WOODCRAFT") in blocks
    assert Block("h1", "CHAPTER I") in blocks
    assert Block("h1", "THE TENT") in blocks
    assert Block("h2", "2. Choosing a site") in blocks
    items = [b.text for b in blocks if b.kind == "li"]
    assert items == ["shelter from the wind", "dry ground, above the flood line and away from dead trees", "water within a hundred yards"]
    # a page ending mid-sentence carries its paragraph over the break; one ending on a full stop does not
    joined = " ".join(b.text for b in blocks)
    assert "The second night is easier than the first, because the camp is made." in joined


def test_mended_hyphen_only_for_a_lowercase_continuation():
    assert reflow._join("wood-", "craft is") == "woodcraft is"
    assert reflow._join("the T-", "Shirt") == "the T-Shirt"
    assert reflow._join("fore-and-", "aft") == "fore-and-aft"


@pytest.mark.parametrize("line,kind", [
    ("CHAPTER IV", "h1"), ("Part Two", "h1"), ("THE MAKING OF FIRE", "h1"), ("3.2 Water from snow", "h2"),
    ("12. The First Aid Kit", "h2"), ("This is an ordinary sentence.", None), ("• a bullet", None),
    ("AB", None), ("A very long capitalised line that goes on and on past ninety characters would not be a heading at all, would it", None),
])
def test_looks_like_heading(line, kind):
    assert looks_like_heading(line) == kind


def test_quality_flags_garbled_ocr_and_counts_words():
    clean = strip_furniture(["The quick brown fox jumps over the lazy dog. " * 30])
    q = text_quality(clean)
    assert q.words == 270 and q.garble == 0 and q.damaged is False
    damaged = strip_furniture(["‘Jlustration is adapted fr0m one by T. H. cnbdr bEfore the war. " * 20])
    assert text_quality(damaged).garble > 0.2
    assert text_quality(damaged).damaged is True
    assert text_quality(strip_furniture(["a few words"])).damaged is True


def test_chapters_cut_at_headings_and_fold_stubs():
    blocks = [Block("h1", "Preface"), Block("p", "short"), Block("h1", "One"), Block("p", "x " * 300),
              Block("h2", "One point one"), Block("p", "y " * 4200), Block("h2", "One point two"), Block("p", "z")]
    parts = chapters(blocks)
    assert [t for t, _ in parts] == ["Preface", "One point two"] or [t for t, _ in parts][0] == "Preface"
    # the preface (one word) folds into the next chapter; the long chapter is cut at the h2 that follows 4000 words
    assert parts[0][0] == "Preface" and any(b.kind == "h1" and b.text == "One" for b in parts[0][1])
    assert parts[-1][0] == "One point two"


def test_write_epub_is_a_valid_package_the_indexer_reads(tmp_path):
    out = tmp_path / "book.epub"
    n = write_epub(out, "A Test & Book", blocks_from_pages(_pages()), author="H. Kephart")
    assert n >= 1
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert names[0] == "mimetype" and zf.getinfo("mimetype").compress_type == zipfile.ZIP_STORED
        assert zf.read("mimetype") == b"application/epub+zip"
        assert "META-INF/container.xml" in names and "OEBPS/content.opf" in names and "OEBPS/nav.xhtml" in names
        opf = zf.read("OEBPS/content.opf").decode()
        assert "<dc:title>A Test &amp; Book</dc:title>" in opf and "<dc:creator>H. Kephart</dc:creator>" in opf
        chapter = zf.read("OEBPS/ch001.xhtml").decode()
        assert "<h1>CAMPING AND WOODCRAFT</h1>" in chapter and "<ul><li>shelter from the wind</li>" in chapter
    pages = docs.epub_pages(out)
    assert pages and "forked stake can be placed" in " ".join(pages)


def test_convert_writes_a_report_or_refuses_damaged_text(tmp_path):
    epub = tmp_path / "out.epub"
    report = convert(Path("x.pdf"), epub, "Camping", text=lambda p: BOOK)
    assert epub.exists() and report.paragraphs >= 4 and report.headings >= 3 and report.chapters >= 1
    assert report.quality.garble == 0
    bad = tmp_path / "bad.epub"
    with pytest.raises(ValueError, match="damaged"):
        convert(Path("x.pdf"), bad, "Bad", text=lambda p: "‘Jlustration fr0m cnbdr bEfore " * 100)
    assert not bad.exists()
    with pytest.raises(ValueError, match="no usable text"):
        convert(Path("x.pdf"), bad, "Empty", text=lambda p: "\f\f")
