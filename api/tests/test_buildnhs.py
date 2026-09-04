import subprocess
from pathlib import Path

from sos import buildnhs


def test_build_command_has_every_section_and_exclusions(tmp_path):
    cmd = buildnhs.build_command(tmp_path, "2026-09-03")
    assert cmd[0] == "zimit"
    seeds = cmd[cmd.index("--seeds") + 1]
    for section in ("conditions", "symptoms", "medicines", "mental-health", "tests-and-treatments", "pregnancy", "live-well"):
        assert f"https://www.nhs.uk/{section}/" in seeds
    assert cmd[cmd.index("--lang") + 1] == "eng"
    assert "brightcove" in cmd[cmd.index("--exclude") + 1]
    assert "as at 2026-09-03" in cmd[cmd.index("--title") + 1]
    assert cmd[cmd.index("--zim-file") + 1] == "nhs_uk.zim"


def _fake_zimdump(entries, date="2026-09-03", title="NHS conditions and medicines (as at 2026-09-03)", article_html="<html><body><p>ok</p></body></html>"):
    def run(cmd, **kwargs):
        if cmd[1] == "list":
            return subprocess.CompletedProcess(cmd, 0, stdout="\n".join(entries) + "\n", stderr="")
        if cmd[1] == "show" and cmd[3] == "M/Date":
            return subprocess.CompletedProcess(cmd, 0, stdout=date, stderr="")
        if cmd[1] == "show" and cmd[3] == "M/Title":
            return subprocess.CompletedProcess(cmd, 0, stdout=title, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout=article_html, stderr="")
    return run


GOOD = [f"www.nhs.uk/conditions/condition-{i}/" for i in range(2800)] + ["static/nhsuk/css/main.css"]


def test_verify_passes_on_good_zim(tmp_path):
    assert buildnhs.verify(tmp_path / "nhs_uk.zim", "2026-09-03", run=_fake_zimdump(GOOD)) == []


def test_verify_reports_each_failure(tmp_path):
    errors = buildnhs.verify(tmp_path / "nhs_uk.zim", "2026-09-03",
                             run=_fake_zimdump(GOOD[:100] + ["players.brightcove.net/x.js"], date="2026-09-01", title="NHS",
                                               article_html='<html><script src="https://assets.nhs.uk/login.js"></script><video src="https://cdn/x.mp4"></video></html>'))
    joined = "\n".join(errors)
    assert "brightcove" in joined
    assert "only 100 articles" in joined
    assert "Date is 2026-09-01" in joined
    assert "Title" in joined
    assert "external <script src>" in joined and "<video>" in joined


def test_main_without_zimit(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildnhs.shutil, "which", lambda name: None)
    assert buildnhs.main(str(tmp_path)) == 2
    assert "zimit" in capsys.readouterr().err
