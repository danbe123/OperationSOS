"""Regenerates the fixtures that are derived rather than hand-written. Standard library only.
Run via `make fixtures` or `api/.venv/bin/python api/tests/fixtures/gen_fixtures.py`."""
from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = HERE.parents[1]
REPO = API.parent
sys.path.insert(0, str(API))

REAL_PLACES = [
    ("Oxford", "city", 51.7520, -1.2577, "England", ""),
    ("Oxted", "town", 51.2573, 0.0060, "England", ""),
    ("Oxwich", "village", 51.5560, -4.1580, "Wales", ""),
    ("Burnley", "town", 53.7890, -2.2480, "England", ""),
    ("Burnham-on-Sea", "town", 51.2390, -2.9990, "England", ""),
    ("London", "city", 51.5074, -0.1278, "England", ""),
    ("Birmingham", "city", 52.4862, -1.8904, "England", ""),
    ("Manchester", "city", 53.4808, -2.2426, "England", ""),
    ("Leeds", "city", 53.8008, -1.5491, "England", ""),
    ("Bristol", "city", 51.4545, -2.5879, "England", ""),
    ("Norwich", "city", 52.6309, 1.2974, "England", ""),
    ("Exeter", "city", 50.7184, -3.5339, "England", ""),
    ("Cardiff", "city", 51.4816, -3.1791, "Wales", ""),
    ("Swansea", "city", 51.6214, -3.9436, "Wales", ""),
    ("Edinburgh", "city", 55.9533, -3.1883, "Scotland", ""),
    ("Glasgow", "city", 55.8642, -4.2518, "Scotland", ""),
    ("Inverness", "city", 57.4778, -4.2247, "Scotland", ""),
    ("Aberdeen", "city", 57.1497, -2.0943, "Scotland", ""),
    ("Lerwick", "town", 60.1546, -1.1494, "Scotland", ""),
    ("Belfast", "city", 54.5973, -5.9301, "Northern Ireland", ""),
    ("Derry", "city", 54.9966, -7.3086, "Northern Ireland", ""),
    ("Dublin", "city", 53.3498, -6.2603, "Republic of Ireland", ""),
    ("Cork", "city", 51.8985, -8.4756, "Republic of Ireland", ""),
    ("Galway", "city", 53.2707, -9.0568, "Republic of Ireland", ""),
    ("Douglas", "town", 54.1500, -4.4800, "Isle of Man", ""),
    ("St Helier", "town", 49.1858, -2.1069, "Jersey", ""),
    ("St Peter Port", "town", 49.4550, -2.5368, "Guernsey", ""),
    ("Kirkby Lonsdale", "town", 54.2020, -2.5970, "England", ""),
    ("Newcastle upon Tyne", "city", 54.9783, -1.6178, "England", ""),
    ("Stoke-on-Trent", "city", 53.0027, -2.1794, "England", ""),
    ("SW1A 1AA", "postcode", 51.5010, -0.1416, "England", "SW1A 1AA"),
    ("OX1 1AA", "postcode", 51.7530, -1.2560, "England", "OX1 1AA"),
    ("M1 1AE", "postcode", 53.4780, -2.2420, "England", "M1 1AE"),
    ("BB11 1AA", "postcode", 53.7880, -2.2470, "England", "BB11 1AA"),
    ("EH1 1AA", "postcode", 55.9500, -3.1900, "Scotland", "EH1 1AA"),
    ("High Street", "road", 51.7515, -1.2555, "England", ""),
]


def write_places(path: Path, total: int = 200) -> None:
    rows = list(REAL_PLACES)
    i = 0
    while len(rows) < total:
        rows.append((f"Test Hamlet {i:03d}", "hamlet", round(50.0 + i * 0.05, 4), round(-3.0 + i * 0.03, 4), "England", ""))
        i += 1
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write("name,kind,lat,lon,region,postcode\n")
        for name, kind, lat, lon, region, postcode in rows:
            fh.write(f"{name},{kind},{lat},{lon},{region},{postcode}\n")


def make_pdf(path: Path, pages: list[list[str]]) -> None:
    """A minimal but valid PDF 1.4 with one Helvetica text block per page (no parentheses in text)."""
    objs: list[bytes] = []

    def add(body: bytes) -> int:
        objs.append(body)
        return len(objs)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_obj = add(b"")
    page_ids = []
    for lines in pages:
        ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"] + [f"({ln}) Tj T*" for ln in lines] + ["ET"]
        stream = "\n".join(ops).encode("latin-1")
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_ids.append(add(
            f"<< /Type /Page /Parent {pages_obj} 0 R /MediaBox [0 0 612 792] /Contents {content} 0 R "
            f"/Resources << /Font << /F1 {font} 0 R >> >> >>".encode()))
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objs[pages_obj - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode())
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n".encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root {catalog} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


def make_png(path: Path, w: int = 48, h: int = 48) -> None:
    raw = b"".join(b"\x00" + bytes([0x33, 0xCC, 0x33] * w) for _ in range(h))

    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def build_noindex_zim() -> bool:
    if shutil.which("zimwriterfs") is None:
        print("zimwriterfs not on PATH; keeping the committed sos-test-noindex.zim")
        return False
    env = dict(os.environ)
    for magic in ("/usr/lib/file/magic.mgc", "/usr/share/file/magic.mgc", "/usr/share/misc/magic.mgc"):
        if Path(magic).exists():
            env.setdefault("MAGIC", magic)
            break
    out = HERE / "library" / "sos-test-noindex.zim"
    if out.exists():
        out.unlink()
    subprocess.run([
        "zimwriterfs", "--welcome=index.html", "--illustration=icon.png", "--language=eng",
        "--title=SOS test (no index)", "--description=Fixture ZIM without a full-text index",
        "--creator=SOS", "--publisher=SOS", "--name=sos-test-noindex", "--withoutFTIndex",
        str(HERE / "pages"), str(out),
    ], check=True, env=env, capture_output=True, text=True)
    return True


def write_sums() -> None:
    lib = HERE / "library"
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(lib.glob("*.zim"))]
    (lib / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    (HERE / "docs").mkdir(exist_ok=True)
    (HERE / "pages").mkdir(exist_ok=True)
    write_places(HERE / "places.csv")
    make_pdf(HERE / "docs" / "sos-test.pdf", [
        ["PAGE ONE Operation SOS test document", "Boil water for one minute before drinking it.",
         "Call 105 to report a power cut in England, Scotland or Wales."],
        ["PAGE TWO Severe bleeding", "Press hard on the wound and call 999.", "Do not remove the first dressing."],
    ])
    make_png(HERE / "pages" / "icon.png")
    build_noindex_zim()
    write_sums()
    shutil.copy(REPO / "manifest" / "schema.json", HERE / "manifest" / "schema.json")
    from tests import broken_cases

    broken_cases.write_all()
    print("fixtures regenerated")


if __name__ == "__main__":
    main()
