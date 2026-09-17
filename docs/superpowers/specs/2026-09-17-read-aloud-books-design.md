# Reading a book aloud

**Date:** 2026-09-17. **Status:** agreed with the owner; built the same evening.

The owner, on the first cut: "if i press read it reads all the crap like it reads all the chapters list front page etc … it needs to be much better thought out". Decisions taken with the owner: from the front of a book the voice jumps to chapter one; pause and resume as well as stop; the British Piper voices offered as catalogue items; a speed setting; no cache of spoken audio (Piper on a Pi 5 makes speech faster than it plays, and the reader fetches the next piece while one plays, so a cache would only save the seconds before the first piece, which the short first piece already covers).

## 1. What is read

The book's own files are walked from the current place, chapter after chapter (`web/src/reader/aloud.ts`). Before the blocks are taken, the furniture is removed:

- Gutenberg's licence header and footer (`.pgheader`, `.pg-boilerplate`, `.pgfooter`), the cover wrapper (`.x-ebookmaker-cover`), transcriber's notes (`.transnote`), title pages (`.titlepage`), the contents and illustrations tables (`#toc`, `#loi`, `.toc`, `.loi`), any `nav` or `[epub:type~=toc]`, and every `table` (a table read aloud is noise; the reflowed guides carry none).
- Figure captions (`figcaption`) and "(Larger)" links; footnote anchors and page-number spans (`.pagenum`, `.pageno`, `sup`).
- Any block whose text is mostly links (a contents list written as paragraphs).

A block is one of the innermost `p, h1–h6, li, blockquote, dd, dt, pre` elements with words in it, so a list item's paragraph is read once. A heading is a piece on its own, so the voice pauses either side of it; "CHAPTER I" and a bare "XII" are said as "Chapter 1" and "Chapter 12".

## 2. Where it starts

- Pressed on the front matter — before the first chapter — the voice jumps to chapter one and the page goes with it. Chapter one is the first block, in the first fifteen files, whose heading says Chapter, Part, Book, Prologue, Letter or a bare numeral; failing that, the first file with three readable paragraphs.
- Pressed anywhere else, it starts at the paragraph at the top of the screen.

## 3. Playing

- One audio element for the whole app, created on the tap that starts the reading and reused for every piece: Safari on the iPad plays only what a touch started, and a new element per piece would have stopped after the first.
- The next piece is fetched while this one plays. The first piece is about 200 characters; the rest 600.
- Pause holds the current piece; Resume continues it. Stop ends the reading. Leaving the book stops it.
- The page follows the voice: each piece's first paragraph is scrolled (smoothly) or turned to as it is read. If you scroll the page yourself the voice carries on and the page stops following; Resume, or a new Read, re-attaches it.
- The controls: while reading, Pause and Stop; while paused, Resume and Stop. In reading mode they are one middle-tap away.

## 4. Voice settings

- `GET /api/voices` lists the Piper voices installed on the box (`models/piper/*.onnx` with their `.onnx.json`), with a name a person would use; `POST /api/speak` takes `voice` (an installed id) and `speed` (0.7–1.4, Piper's `length_scale` is its inverse) and always a short silence between sentences.
- The catalogue offers the single-speaker British medium voices besides Alba: Alan, Cori, Jenny and a northern English man, each a `model` item in the `ai` category fetched from Hugging Face with a checksum; the box's sync fetches the `.onnx.json` beside each. Aru and Semaine are multi-speaker models and are not offered.
- In the reader bar, Voice opens a row with the installed voices, the speed (slower, normal, faster) and a link to the AI sources for more. The choice is kept in the browser (`sos.voice.id`, `sos.voice.speed`) and applies to briefings and pages as well as books.

## 5. Also

Scrolling, the bar no longer shows Previous and Next: there are no pages to turn.
