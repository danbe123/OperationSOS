"""Read aloud: Piper's arguments, its absence, and `POST /api/speak`. The subprocess is faked throughout."""
import wave

import pytest

from sos import speak

SAMPLE = b"\x00\x01" * 2205                      # a tenth of a second of nonsense, enough to be a real WAV


@pytest.fixture
def installed(env):
    """A box with Piper and the voice in place, both as empty files: nothing here ever executes them."""
    binary = env.core / "bin" / "piper" / "piper"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"#!/bin/false\n")
    binary.chmod(0o755)
    (binary.parent / "espeak-ng-data").mkdir()
    voice = env.core / "models" / "piper" / f"{env.piper_voice}.onnx"
    voice.parent.mkdir(parents=True)
    voice.write_bytes(b"onnx")
    return env


class FakePiper:
    """Writes a WAV where Piper would have and remembers the command line and the text on stdin."""

    def __init__(self, write: bool = True):
        self.write, self.calls = write, []

    def __call__(self, args, text, out, timeout):
        self.calls.append({"args": list(args), "text": text, "timeout": timeout})
        if self.write:
            with wave.open(str(out), "wb") as fh:
                fh.setnchannels(1)
                fh.setsampwidth(2)
                fh.setframerate(22050)
                fh.writeframes(SAMPLE)


def test_clean_makes_one_line_and_caps_the_length():
    assert speak.clean("  Fill the bath\n now.  ") == "Fill the bath now."
    assert len(speak.clean("a " * 5000)) == speak.MAX_CHARS
    assert speak.clean("   ") == ""


def test_not_installed_is_reported_by_name(env):
    assert speak.available(env) is False
    with pytest.raises(speak.SpeakError) as exc:
        speak.synthesise(env, "Hello")
    assert "piper" in str(exc.value) and "piper-voice-en_GB" in str(exc.value)


def test_a_missing_voice_alone_is_reported(installed):
    installed.piper_voice_path.unlink()
    with pytest.raises(speak.SpeakError) as exc:
        speak.synthesise(installed, "Hello")
    assert "piper-voice-en_GB" in str(exc.value) and "items" not in str(exc.value)


def test_synthesise_runs_piper_with_the_voice_and_returns_the_wav(installed):
    piper = FakePiper()
    audio = speak.synthesise(installed, "Mains power is off.\nFill the bath.", runner=piper)
    assert audio[:4] == b"RIFF" and audio[8:12] == b"WAVE" and len(audio) > len(SAMPLE)
    call = piper.calls[0]
    assert call["args"][0] == str(installed.piper_bin)
    assert call["args"][call["args"].index("--model") + 1] == str(installed.piper_voice_path)
    assert "--espeak_data" in call["args"] and "--quiet" in call["args"]
    assert call["text"] == "Mains power is off. Fill the bath.\n"       # one line, as Piper reads stdin
    assert call["timeout"] == installed.speak_timeout_s


def test_piper_producing_nothing_is_an_error_not_an_empty_file(installed):
    with pytest.raises(speak.SpeakError):
        speak.synthesise(installed, "Hello", runner=FakePiper(write=False))


def test_empty_text_is_refused(installed):
    with pytest.raises(ValueError):
        speak.synthesise(installed, "   \n ", runner=FakePiper())


# --- the endpoint ------------------------------------------------------------------------------------------

def test_speak_endpoint_503s_when_piper_is_not_installed(client):
    response = client.post("/api/speak", json={"text": "Fill the bath now."})
    assert response.status_code == 503 and "piper" in response.json()["detail"]


def test_speak_endpoint_returns_a_wav(installed, client, monkeypatch):
    monkeypatch.setattr(speak, "run_piper", FakePiper())
    response = client.post("/api/speak", json={"text": "Fill the bath now."})
    assert response.status_code == 200 and response.headers["content-type"] == "audio/wav"
    assert response.content[:4] == b"RIFF"
    assert client.post("/api/speak", json={"text": "  "}).status_code == 422


def test_the_sensors_endpoint_reports_whether_piper_is_there(installed, client):
    assert client.get("/api/sensors").json()["drivers"]["piper"] is True
