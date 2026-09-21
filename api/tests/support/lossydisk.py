"""Build and replay tests/support/lossydisk.c: the disk that loses power."""
from __future__ import annotations

import os
import shutil
import struct
import subprocess
from pathlib import Path

SOURCE = Path(__file__).with_name("lossydisk.c")


def build(out_dir: Path) -> Path | None:
    cc = shutil.which("gcc") or shutil.which("cc")
    if cc is None:
        return None
    so = out_dir / "lossydisk.so"
    proc = subprocess.run([cc, "-shared", "-fPIC", "-O1", "-o", str(so), str(SOURCE), "-ldl"], capture_output=True, text=True)
    return so if proc.returncode == 0 else None


def env_for(so: Path, prefix: Path, log: Path) -> dict[str, str]:
    return {"LD_PRELOAD": str(so), "LOSSY_PREFIX": str(prefix), "LOSSY_LOG": str(log)}


def power_cut(log: Path) -> int:
    """Undo every write that was not followed by a sync of its file; returns how many writes were lost."""
    data = log.read_bytes() if log.exists() else b""
    pending: dict[str, list[tuple[int, int, bytes, str]]] = {}
    pos = 0
    while pos + 3 <= len(data):
        kind = chr(data[pos])
        (plen,) = struct.unpack_from("<H", data, pos + 1)
        head = pos + 3 + plen + 8 + 8 + 4
        if head > len(data):
            break
        path = data[pos + 3:pos + 3 + plen].decode()
        off, old_size, old_len = struct.unpack_from("<QQI", data, pos + 3 + plen)
        if head + old_len > len(data):
            break  # the record the kill cut short: its write never started
        old = data[head:head + old_len]
        pos = head + old_len
        if kind == "S":
            pending[path] = []
        else:
            pending.setdefault(path, []).append((off, old_size, old, kind))
    lost = 0
    for path, records in pending.items():
        if not os.path.exists(path):
            continue
        with open(path, "r+b") as f:
            for off, old_size, old, kind in reversed(records):
                lost += 1
                if kind == "T":
                    f.truncate(old_size)      # a truncate is undone by growing back...
                    f.seek(off)
                    f.write(old)              # ...and putting back what it cut off
                else:
                    f.truncate(old_size) if os.fstat(f.fileno()).st_size > old_size else None
                    f.seek(off)
                    f.write(old)
    return lost
