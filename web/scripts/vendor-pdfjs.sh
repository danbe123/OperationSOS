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
# The stock viewer forbids inline styles and lets a PDF's scripts fetch anywhere. The box injects its
# own theme stylesheet into the viewer, and nothing on the box may call out, so the policy is patched
# to allow the one and forbid the other. check-vendor verifies the patch is present.
python3 - <<'PY'
from pathlib import Path
p = Path("public/pdfjs/web/viewer.html"); s = p.read_text()
assert "style-src 'self';" in s, "viewer.html policy has changed; update vendor-pdfjs.sh"
s = s.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';", 1)
import re
s = re.sub(r"connect-src \*[^;]*;", "connect-src 'self' blob: data:;", s, count=1)
p.write_text(s)
PY
echo "${VER}" > public/pdfjs/VERSION
test -f public/pdfjs/web/viewer.html
echo "PDF.js ${VER} vendored into public/pdfjs ($(du -sh public/pdfjs | cut -f1))"
