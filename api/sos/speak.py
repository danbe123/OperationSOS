"""Read aloud (spec section 6): Piper turns a briefing into speech so the box can be listened to in the dark.

Piper is a small offline neural synthesiser; it and one British voice are manifest items in the `ai` category
(`piper`, a directory of binaries, and `piper-voice-en_GB`, the .onnx model and its .json). Neither is required:
without them `POST /api/speak` answers 503 and the screen keeps its text.

The binary is run as a subprocess with a timeout, reading the text on stdin and writing a WAV to a temporary file
(Piper's own `--output_file`), which is then returned whole. The runner is an argument so tests never touch it."""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from sos.config import Settings

log = logging.getLogger(__name__)
MAX_CHARS = 4000
Runner = Callable[[list[str], str, Path, float], None]


class SpeakError(RuntimeError):
    """Piper is not installed, or it ran and produced nothing."""


def installed(settings: Settings) -> dict:
    """What is present, for `/status` and for the 503 message."""
    binary, voice = Path(settings.piper_bin), Path(settings.piper_voice_path)
    return {"binary": str(binary), "voice": str(voice), "voice_id": settings.piper_voice,
            "binary_present": binary.is_file() and os.access(binary, os.X_OK), "voice_present": voice.is_file()}


def available(settings: Settings) -> bool:
    state = installed(settings)
    return bool(state["binary_present"] and state["voice_present"])


def run_piper(args: list[str], text: str, out: Path, timeout: float) -> None:
    """The real runner: Piper reads the line on stdin and writes the WAV to `out`."""
    env = dict(os.environ)
    lib = str(Path(args[0]).parent)                 # the release tarball keeps its shared objects beside the binary
    env["LD_LIBRARY_PATH"] = f"{lib}:{env['LD_LIBRARY_PATH']}" if env.get("LD_LIBRARY_PATH") else lib
    proc = subprocess.run(args, input=text, capture_output=True, text=True, timeout=timeout, check=False, env=env)
    if proc.returncode != 0 and not out.exists():
        raise SpeakError(f"piper exited {proc.returncode}: {(proc.stderr or '').strip().splitlines()[-1:] or ''}")


def clean(text: str) -> str:
    """One line of plain prose: Piper reads stdin a line at a time, and control characters upset it."""
    collapsed = " ".join((text or "").split())
    return collapsed[:MAX_CHARS]


def synthesise(settings: Settings, text: str, runner: Optional[Runner] = None) -> bytes:
    """The WAV bytes for one piece of text. Raises SpeakError when Piper is missing or produced nothing."""
    line = clean(text)
    if not line:
        raise ValueError("Nothing to say")
    state = installed(settings)
    if not state["binary_present"] or not state["voice_present"]:
        missing = [name for name, key in (("piper", "binary_present"), ("piper-voice-en_GB", "voice_present"))
                   if not state[key]]
        raise SpeakError(f"Read aloud needs the manifest item{'s' if len(missing) > 1 else ''} "
                         f"{' and '.join(missing)}: install {', '.join(missing)} on the box.")
    runner = runner or run_piper
    with tempfile.TemporaryDirectory(prefix="sos-speak-") as work:
        out = Path(work) / "speech.wav"
        args = [str(settings.piper_bin), "--model", str(settings.piper_voice_path),
                "--output_file", str(out), "--quiet"]
        espeak = Path(settings.piper_bin).parent / "espeak-ng-data"
        if espeak.is_dir():                         # the tarball ships its own; the Pi has no system copy
            args += ["--espeak_data", str(espeak)]
        runner(args, line + "\n", out, float(settings.speak_timeout_s))
        if not out.is_file() or out.stat().st_size == 0:
            raise SpeakError("Piper produced no audio")
        return out.read_bytes()
