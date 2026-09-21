"""A writer for the crash tests: one note per transaction, its number printed only once the commit has returned
(that is the acknowledgement). Killed at random moments by the test. Usage: crash_writer.py DB MODE   (MODE: normal | durable)."""
from __future__ import annotations

import sys

from sos import db

path, mode = sys.argv[1], sys.argv[2]
conn = db.connect(path, durable=(mode == "durable"))
i = 0
while True:
    i += 1
    conn.execute("INSERT INTO notes(kind, title, body, updated_at) VALUES ('note', ?, ?, ?)", (f"n{i}", "x" * 300, db.now_iso()))
    conn.commit()
    sys.stdout.write(f"{i}\n")
    sys.stdout.flush()
