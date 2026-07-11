# tests/test_sync.py
"""Tests for the remote dashboard: generation, encryption, deploy, wizard."""

from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from timetrack.core.dashboard import DashboardManager
from timetrack.core.deploy import VercelBackend, get_backend
from timetrack.core.facade import TimeTracker
from timetrack.cli import main
from timetrack.models import SyncConfig

_FAKE_DIR = Path("/tmp/none")


def _patch_data(monkeypatch, temp_data_dir):
    """Redirect all data paths to a temp dir (mirrors conftest guidance)."""
    monkeypatch.setattr("timetrack.core.constants.DATA_DIR", temp_data_dir)
    monkeypatch.setattr("timetrack.core.constants.DASHBOARD_DIR", temp_data_dir / "dashboard")
    monkeypatch.setattr("timetrack.core.storage.DATA_DIR", temp_data_dir)
    monkeypatch.setattr("timetrack.core.storage.STATE_FILE", temp_data_dir / "state.json")
    monkeypatch.setattr("timetrack.core.storage.LOG_FILE", temp_data_dir / "timelog.json")
    monkeypatch.setattr("timetrack.core.storage.CONFIG_FILE", temp_data_dir / "config.json")
    monkeypatch.setattr("timetrack.core.storage.MEMOS_FILE", temp_data_dir / "memos.json")


def test_dashboard_plaintext_self_contained(storage, temp_data_dir, sample_entries):
    dm = DashboardManager(storage)
    ok, path = dm.generate(temp_data_dir / "out", days=30)
    assert ok
    html = (temp_data_dir / "out" / "index.html").read_text()
    assert "const DATA =" in html
    assert "cdn.jsdelivr" not in html
    assert "http://" not in html
    assert "https://" not in html
    assert "coding" in html


def test_dashboard_passphrase_encrypted(storage, temp_data_dir, sample_entries):
    dm = DashboardManager(storage)
    ok, path = dm.generate(temp_data_dir / "out", days=30, passphrase="secret")
    assert ok
    html = (temp_data_dir / "out" / "index.html").read_text()
    assert "const ENC =" in html
    assert "crypto.subtle.decrypt" in html
    assert "const DATA =" not in html
    assert "secret" not in html


def test_vercel_backend_no_cli(monkeypatch):
    monkeypatch.setattr("timetrack.core.deploy.shutil.which", lambda x: None)
    b = VercelBackend(project="track-dash")
    ok, msg = b.deploy(_FAKE_DIR, prod=True)
    assert ok is False
    assert "vercel" in msg.lower()


def test_vercel_backend_deploy(monkeypatch):
    out = "https://track-dash.vercel.app\nInspect: x\n"
    monkeypatch.setattr("timetrack.core.deploy.shutil.which", lambda x: "/usr/bin/vercel")
    with mock.patch("timetrack.core.deploy.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout=out, stderr="")
        b = VercelBackend(project="track-dash", token="t", domain=None)
        ok, url = b.deploy(_FAKE_DIR, prod=True)
    assert ok
    assert url == "https://track-dash.vercel.app"
    args = run.call_args[0][0]
    assert "deploy" in args and "--prod" in args and "--name" in args


def test_vercel_backend_deploy_with_domain(monkeypatch):
    out = "Deployed to https://x.vercel.app\n"
    monkeypatch.setattr("timetrack.core.deploy.shutil.which", lambda x: "/usr/bin/vercel")
    with mock.patch("timetrack.core.deploy.subprocess.run") as run:
        run.return_value = mock.Mock(returncode=0, stdout=out, stderr="")
        b = VercelBackend(project="track-dash", token="t", domain="track.example.com")
        ok, url = b.deploy(_FAKE_DIR, prod=True)
    assert ok
    cmds = [c.args[0] for c in run.call_args_list]
    assert any("domains" in c for c in cmds)
    assert url in ("https://track.example.com", "https://x.vercel.app")


def test_get_backend_unsupported():
    import pytest

    with pytest.raises(ValueError):
        get_backend(SyncConfig(host="netlify"))


def test_sync_not_configured(monkeypatch, temp_data_dir):
    _patch_data(monkeypatch, temp_data_dir)
    t = TimeTracker()
    ok, msg = t.sync()
    assert ok is False
    assert "not set up" in msg.lower()


def test_generate_and_sync(monkeypatch, temp_data_dir, sample_entries):
    _patch_data(monkeypatch, temp_data_dir)
    t = TimeTracker()
    t.configure_sync(configured=True, host="vercel", project="track-dash", token="t")
    ok, msg = t.generate_dashboard(days=30)
    assert ok
    with mock.patch("timetrack.core.facade.get_backend") as gb:
        gb.return_value.deploy.return_value = (True, "https://track-dash.vercel.app")
        ok, msg = t.sync()
    assert ok
    assert "track-dash.vercel.app" in msg


def test_sync_wizard_saves_config(monkeypatch, temp_data_dir, sample_entries):
    _patch_data(monkeypatch, temp_data_dir)
    monkeypatch.setattr("timetrack.core.deploy.shutil.which", lambda x: "/usr/bin/vercel")
    with mock.patch("timetrack.core.deploy.subprocess.run") as run:
        run.return_value = mock.Mock(
            returncode=0, stdout="https://track-dash.vercel.app\n", stderr=""
        )
        runner = CliRunner()
        # continue=y, token=(empty), project=(default), domain=(empty), protect=n
        answers = "\n".join(["y", "", "", "", "n"]) + "\n"
        result = runner.invoke(main, ["sync"], input=answers)
    assert result.exit_code == 0
    assert "live at" in result.output
    t = TimeTracker()
    assert t.get_sync_config().configured is True
    assert t.get_sync_config().passphrase_protected is False


def test_sync_preflight_blocks_without_vercel(monkeypatch, temp_data_dir):
    _patch_data(monkeypatch, temp_data_dir)
    monkeypatch.setattr("timetrack.core.deploy.shutil.which", lambda x: None)
    runner = CliRunner()
    answers = "\n".join(["y", "", "", "", "n"]) + "\n"
    result = runner.invoke(main, ["sync"], input=answers)
    # Pre-flight blocks before the wizard: clear message, no config saved.
    assert result.exit_code == 0
    assert "vercel" in result.output.lower()
    assert "Sync configuration saved" not in result.output
    t = TimeTracker()
    assert t.get_sync_config().configured is False
