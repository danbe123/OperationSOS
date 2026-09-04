#!/usr/bin/env bash
# Fetch the PDF.js prebuilt viewer matching the pinned pdfjs-dist version into public/pdfjs (git-ignored).
set -euo pipefail
cd "$(dirname "$0")/.."
VER="$(node -p "require('pdfjs-dist/package.json').version")"
ZIP="pdfjs-${VER}-dist.zip"
URL="https://github.com/mozilla/pdf.js/releases/download/v${VER}/${ZIP}"
TMP="$(mktemp -d)"
echo "Fetching PDF.js ${VER} from ${URL}"
curl -sSL -o "${TMP}/${ZIP}" "${URL}"
rm -rf public/pdfjs
mkdir -p public/pdfjs
python3 -m zipfile -e "${TMP}/${ZIP}" public/pdfjs
rm -f public/pdfjs/web/compressed.tracemonkey-pldi-09.pdf
find public/pdfjs -name '*.map' -delete
rm -rf "${TMP}"
echo "${VER}" > public/pdfjs/VERSION
test -f public/pdfjs/web/viewer.html
echo "PDF.js ${VER} vendored into public/pdfjs ($(du -sh public/pdfjs | cut -f1))"
