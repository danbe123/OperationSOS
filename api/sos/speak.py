"""Read aloud (spec section 6): Piper turns a briefing, a page or a book into speech so the box can be listened
to in the dark.

Piper is a small offline neural synthesiser; it and one British voice are manifest items in the `ai` category
(`piper`, a directory of binaries, and `piper-voice-en_GB`, the .onnx model and its .json). Neither is required:
without them `POST /api/speak` answers 503 and the screen keeps its text. More voices are single-file `model`
items fetched with their `.onnx.json` beside them; `voices()` lists whatever is in the models directory and
`synthesise()` reads with any of them, at a speed, with a breath between sentences.

The binary is run as a subprocess with a timeout, reading the text on stdin and writing a WAV to a temporary file
(Piper's own `--output_file`), which is then returned whole. The runner is an argument so tests never touch it."""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from sos.config import Settings

log = logging.getLogger(__name__)
MAX_CHARS = 4000
SPEED_MIN, SPEED_MAX = 0.7, 1.4
SENTENCE_SILENCE_S = 0.3
Runner = Callable[[list[str], str, Path, float], None]
_VOICE_ID = re.compile(r"^[A-Za-z0-9_\-]+$")

# The name a person would use for a Piper dataset. Anything else is the dataset, capitalised.
NAMES = {
    "alba": "Alba", "alan": "Alan", "aru": "Aru", "cori": "Cori", "jenny_dioco": "Jenny",
    "northern_english_male": "Northern English man", "southern_english_female": "Southern English woman", "semaine": "Semaine",
}


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


def voices(settings: Settings) -> list[dict]:
    """The voices on the box: every `<id>.onnx` in the models directory, the box's default first, single-speaker
    models only (a multi-speaker model needs a speaker chosen, which the reader does not offer)."""
    folder = Path(settings.piper_voice_path).parent
    found: list[dict] = []
    for path in sorted(folder.glob("*.onnx")) if folder.is_dir() else []:
        meta: dict = {}
        try:
            meta = json.loads(path.with_name(path.name + ".json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        if int(meta.get("num_speakers", 1) or 1) > 1:
            continue
        dataset = str(meta.get("dataset") or path.stem.split("-")[1] if "-" in path.stem else path.stem)
        found.append({"id": path.stem, "name": NAMES.get(dataset, dataset.replace("_", " ").capitalize()),
                      "quality": str(meta.get("audio", {}).get("quality") or ""), "language": str(meta.get("language", {}).get("code") or "")})
    found.sort(key=lambda v: (v["id"] != settings.piper_voice, v["name"]))
    return found


def voice_path(settings: Settings, voice: Optional[str]) -> Path:
    """The model file for a voice id, the box's default when none is asked for. A name that is not an id, or a
    voice that is not on the box, is a `LookupError`."""
    if not voice or voice == settings.piper_voice:
        return Path(settings.piper_voice_path)
    if not _VOICE_ID.match(voice):
        raise LookupError(f"No such voice: {voice!r}")
    path = Path(settings.piper_voice_path).with_name(f"{voice}.onnx")
    if not path.is_file():
        raise LookupError(f"The voice {voice} is not on this box")
    return path


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


def synthesise(settings: Settings, text: str, runner: Optional[Runner] = None, voice: Optional[str] = None,
               speed: float = 1.0) -> bytes:
    """The WAV bytes for one piece of text, in `voice` at `speed` (1.0 is Piper's own pace; 1.2 is a fifth
    quicker). Raises SpeakError when Piper is missing or produced nothing, LookupError for a voice that is not
    on the box, ValueError for nothing to say."""
    line = clean(text)
    if not line:
        raise ValueError("Nothing to say")
    state = installed(settings)
    if not state["binary_present"] or not state["voice_present"]:
        missing = [name for name, key in (("piper", "binary_present"), ("piper-voice-en_GB", "voice_present"))
                   if not state[key]]
        raise SpeakError(f"Read aloud needs the manifest item{'s' if len(missing) > 1 else ''} "
                         f"{' and '.join(missing)}: install {', '.join(missing)} on the box.")
    model = voice_path(settings, voice)
    pace = min(SPEED_MAX, max(SPEED_MIN, float(speed or 1.0)))
    runner = runner or run_piper
    with tempfile.TemporaryDirectory(prefix="sos-speak-") as work:
        out = Path(work) / "speech.wav"
        args = [str(settings.piper_bin), "--model", str(model), "--output_file", str(out), "--quiet",
                "--length_scale", f"{1 / pace:.3f}", "--sentence_silence", f"{SENTENCE_SILENCE_S:.2f}"]
        espeak = Path(settings.piper_bin).parent / "espeak-ng-data"
        if espeak.is_dir():                         # the tarball ships its own; the Pi has no system copy
            args += ["--espeak_data", str(espeak)]
        runner(args, line + "\n", out, float(settings.speak_timeout_s))
        if not out.is_file() or out.stat().st_size == 0:
            raise SpeakError("Piper produced no audio")
        return out.read_bytes()
