"""
Security and power-feature tests for :class:`AutomationEngine`.

These tests run fully headless. The lazy ``pyautogui`` import is replaced with a
``MagicMock`` via ``ai_rpa_system.automation_engine._get_pyautogui`` so that no
real GUI / display is ever required. Each test covers a specific hardening
guarantee:

  * ``open_application`` never shells out (no ``shell=True``); on Windows it uses
    ``os.startfile`` with the literal app name, on POSIX it ``Popen``s a list.
  * ``type_text(sensitive=True)`` never leaks the raw secret into the logs.
  * ``wait_for_image`` polls ``find_image_on_screen`` until a hit or timeout.
"""

import logging
from unittest.mock import MagicMock

import pytest

import ai_rpa_system.automation_engine as automation_engine
from ai_rpa_system.automation_engine import AutomationEngine


@pytest.fixture
def mock_pyautogui(monkeypatch):
    """Replace the lazily-imported pyautogui with a MagicMock."""
    fake = MagicMock(name="pyautogui")
    monkeypatch.setattr(automation_engine, "_get_pyautogui", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# (1) open_application must NOT use a shell.
# ---------------------------------------------------------------------------

def test_open_application_windows_uses_startfile_no_shell(mock_pyautogui, monkeypatch):
    """On Windows, open_application uses os.startfile with the literal name."""
    fake_startfile = MagicMock(name="startfile")
    monkeypatch.setattr(automation_engine.os, "startfile", fake_startfile, raising=False)
    # Guard against any accidental subprocess shell-out.
    fake_popen = MagicMock(name="Popen")
    monkeypatch.setattr(automation_engine.subprocess, "Popen", fake_popen)

    engine = AutomationEngine()
    engine.platform = "Windows"

    assert engine.open_application("notepad") is True

    # The literal app name was handed to os.startfile, with no shell anywhere.
    fake_startfile.assert_called_once_with("notepad")
    fake_popen.assert_not_called()


def test_open_application_posix_uses_popen_list_no_shell(mock_pyautogui, monkeypatch):
    """On POSIX, open_application calls subprocess.Popen with a list (no shell)."""
    fake_popen = MagicMock(name="Popen")
    monkeypatch.setattr(automation_engine.subprocess, "Popen", fake_popen)
    # Make path resolution deterministic and non-shell.
    monkeypatch.setattr(automation_engine.shutil, "which", lambda name: "/usr/bin/" + name)

    engine = AutomationEngine()
    engine.platform = "Linux"

    assert engine.open_application("firefox") is True

    fake_popen.assert_called_once()
    args, kwargs = fake_popen.call_args
    # First positional arg is a discrete-argument list, never a shell string.
    assert isinstance(args[0], list)
    assert "firefox" in args[0][0]
    # shell=True must never be passed.
    assert kwargs.get("shell", False) is False


# ---------------------------------------------------------------------------
# (2) type_text(sensitive=True) must redact the secret from logs.
# ---------------------------------------------------------------------------

def test_type_text_sensitive_redacts_logs(mock_pyautogui, caplog):
    """A sensitive secret is never written verbatim to the logs."""
    secret = "hunter2-SuperSecret-Token"

    engine = AutomationEngine()
    with caplog.at_level(logging.INFO, logger=automation_engine.logger.name):
        assert engine.type_text(secret, interval=0, sensitive=True) is True

    # The secret was actually typed via pyautogui...
    mock_pyautogui.write.assert_called_once_with(secret, interval=0)
    # ...but never appears in any log record.
    assert secret not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_type_text_non_sensitive_logs_short_text(mock_pyautogui, caplog):
    """Sanity check: a short, non-sensitive value is still logged plainly."""
    engine = AutomationEngine()
    with caplog.at_level(logging.INFO, logger=automation_engine.logger.name):
        assert engine.type_text("hello", interval=0, sensitive=False) is True

    assert "hello" in caplog.text


# ---------------------------------------------------------------------------
# (3) wait_for_image polls find_image_on_screen until a hit or timeout.
# ---------------------------------------------------------------------------

def test_wait_for_image_returns_location_after_polling(mock_pyautogui, monkeypatch):
    """wait_for_image keeps polling and returns the first non-None location."""
    engine = AutomationEngine()
    finder = MagicMock(side_effect=[None, None, (5, 5)])
    monkeypatch.setattr(engine, "find_image_on_screen", finder)
    # Never actually sleep.
    monkeypatch.setattr(automation_engine.time, "sleep", lambda s: None)

    location = engine.wait_for_image("button.png", timeout=10.0, interval=0.01)

    assert location == (5, 5)
    assert finder.call_count == 3


def test_wait_for_image_returns_none_on_timeout(mock_pyautogui, monkeypatch):
    """wait_for_image returns None when the image never appears in time."""
    engine = AutomationEngine()
    finder = MagicMock(return_value=None)
    monkeypatch.setattr(engine, "find_image_on_screen", finder)
    monkeypatch.setattr(automation_engine.time, "sleep", lambda s: None)

    # A tiny/zero timeout means the deadline is hit immediately after one poll.
    location = engine.wait_for_image("missing.png", timeout=0.0, interval=0.01)

    assert location is None
    assert finder.called
