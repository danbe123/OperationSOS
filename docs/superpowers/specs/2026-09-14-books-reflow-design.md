# Books read like a Kindle, not a scanned PDF: design

Date: 2026-09-14. Status: approved in conversation (the owner wants a "proper ereader view of the books
not pdfs converted like a kindle display").

## 1. What is wrong

The Library already has a reader for every book (`web/src/screens/Doc.tsx`): EPUBs render through
epub.js, which reflows text, remembers position and paginates like a Kindle. But most of the library's
~80 books (Hesperian's *Where There Is No Doctor*/*Dentist*, UK/US field manuals, the OpenStax textbook
set, UK Building Regulations Approved Documents, the woodcraft PDFs) are `kind: "pdf"` and render through
PDF.js as fixed page images: pan and zoom, not reflow. The owner wants one consistent, reflowable reading
experience across the whole library, not two.

## 2. Convert once, at content-build time, and reuse the existing EPUB reader

Every current `kind: "pdf"` item is converted to EPUB with Calibre's `ebook-convert`, run on the dev PC as
part of content curation — never on the Pi, never at request time. The converted EPUB becomes the item's
primary form and opens in the EPUB reader that already exists. Conversion is automated for every book, no
manual per-book cleanup pass: text-heavy manuals convert cleanly; diagram-heavy books (dosage charts,
illustrated medical guides) may come out rougher, and that's accepted — see section 6 for the fallback.

Two approaches were ruled out:

- Converting on-demand at runtime: no benefit, since the content is static; wastes Pi CPU on every open.
- A bespoke reflow renderer built on `pdftohtml` output: reinvents what epub.js already does well, for a
  worse result, for more code.

## 3. Manifest

One new optional item field, `pdf_dest` (same path pattern as `dest`): set only on a converted item,
naming where the original PDF is kept alongside the EPUB as a fallback file.

A converted item changes from:

```json
{ "id": "where-there-is-no-doctor", "kind": "pdf", "source": { "type": "url", "url": "https://…" },
  "dest": "docs/where-there-is-no-doctor.pdf" }
```

to:

```json
{ "id": "where-there-is-no-doctor", "kind": "epub",
  "source": { "type": "build", "tool": "pdf2epub", "artifact": "docs/where-there-is-no-doctor.epub",
              "url": "https://…" },
  "dest": "docs/where-there-is-no-doctor.epub",
  "pdf_dest": "docs/where-there-is-no-doctor.pdf" }
```

`source.url` is kept (the schema already allows `url` alongside a `build` source; nothing conditionally
forbids it) so `build-books` knows what to fetch. No other schema change: a converted item is one manifest
row, not two, so the Library grid never shows a book twice.

The `scmg-*` chapter PDFs (13 items, one book split into chapters) keep their existing one-item-per-chapter
structure — each chapter converts to its own small EPUB rather than being merged into one book. That's a
scope decision, not a deferred question: merging chapters is out of scope here.

## 4. `sos build-books`

A new PC-only CLI subcommand (`api/sos/buildbooks.py`, registered in `cli.py` next to `build-crawl` and
`build-maps`, following the same `run: Callable` injection pattern as `buildcrawl.py` so it's unit-testable
without invoking Calibre). For every manifest item with `source.tool == "pdf2epub"`:

1. Locate the source PDF (already present from an earlier `sos sync core`, or fetched from `source.url`).
2. Run `ebook-convert <pdf> <epub>`, using the item's `title` for EPUB metadata.
3. Write the `.epub` to `dest`; the original PDF stays (or is fetched) at `pdf_dest` — nothing is copied.
   (Amended 2026-09-14 after the build: the tool also passes `--enable-heuristics` so Calibre unwraps PDF lines into
   paragraphs, retries once with `--flow-size 0` when Calibre's splitter gives up, and reports FAIL — leaving the
   item as `kind: "pdf"` — when the PDF has no text layer or the EPUB keeps under half of the PDF's words.)
4. Report `OK`/`FAIL` per item, in the same style as `sos sync`'s per-item output.

A `FAIL` is not a blocking error for the batch: that book's manifest entry simply isn't migrated (stays
`kind: "pdf"`, unchanged) until it's revisited. No code elsewhere needs to know about partially-migrated
state — an un-migrated book behaves exactly as it does today.

Calibre isn't currently installed in the dev environment (only `pdftotext` is present). It installs
user-local via the official Linux installer script (no sudo), the same pattern as the other tools already
in `~/.local/bin`.

## 5. Backend: `api/sos/library.py`

`file_url()` already resolves a served path from `dest`. Add the same resolution for `pdf_dest` — call it
`pdf_fallback_url` — into `item_dict()`, so `/api/library` tells the frontend where the original PDF sits
(omitted entirely for items with no `pdf_dest`, which is every book that was always EPUB or never got
converted).

## 6. Frontend: view the original layout

`web/src/api/types.ts`: add `pdf_fallback_url?: string | null` to `LibraryItem`.

`web/src/screens/Doc.tsx`: when the item is an EPUB with `pdf_fallback_url` set, show a small toggle in the
reader chrome ("Reflowed" / "Original layout") that switches the same screen between the existing
`EpubReader` (default) and the existing `PdfChrome` component pointed at `pdf_fallback_url`. Both viewers
already exist and are already themed; this is a toggle, not new viewer code. This is the safety valve for
section 2's "no manual per-book cleanup": if a conversion mangles a table or separates a diagram from its
caption, the original is one tap away.

## 7. Scope

Every current `kind: "pdf"` item across every category (books, medical, survival, reference, education,
uk-official) — roughly 80 books — gets converted via `build-books` and checked in as a manifest edit.
Books that are already EPUB (Nessmuk, Beard, Kreps, the 1911 Boy Scouts Handbook) are unaffected: no
`pdf_dest`, no toggle shown.

## 8. Testing

- `api/tests/test_manifest.py` / `test_manifest_content.py`: schema accepts `pdf_dest`; a `build`-source
  item may carry `source.url`; duplicate-`dest` check also covers `pdf_dest` (an epub's `pdf_dest` must
  not collide with another item's `dest`).
- `api/sos/buildbooks.py`: unit tests with an injected fake `run`, covering OK, a non-zero `ebook-convert`
  exit (reported as `FAIL`, manifest untouched), and the `pdf_dest` copy.
- Frontend: a `Doc.tsx` test that the original-layout toggle renders only when `pdf_fallback_url` is
  present, and switches between `EpubReader` and `PdfChrome`.
