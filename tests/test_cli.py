"""
Tests for the AI-Powered RPA command-line interface (``ai_rpa_system.cli``).

All cases are headless: no real GUI actions are performed. ``capsys`` captures
stdout/stderr and ``tmp_path`` provides isolated storage / file locations.
"""

import json

import pytest

from ai_rpa_system import __version__
from ai_rpa_system.cli import main


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #

def _good_workflow_dict():
    """A structurally valid workflow (passes validate_workflow)."""
    return {
        "name": "good_wf",
        "description": "A valid workflow.",
        "steps": [
            {
                "action": "click",
                "description": "Click the login button",
                "coordinates": [100, 200],
            },
            {
                "action": "type",
                "description": "Type a username",
                "text": "hello",
            },
            {
                "action": "wait",
                "description": "Pause briefly",
                "wait_before": 1.0,
            },
        ],
    }


def _bad_workflow_dict():
    """A structurally invalid workflow (fails validate_workflow):
    a click with no coordinates / image_path, and a type with empty text."""
    return {
        "name": "bad_wf",
        "description": "An invalid workflow.",
        "steps": [
            {
                "action": "click",
                "description": "Click nothing (no coords / no image)",
            },
            {
                "action": "type",
                "description": "Type empty text",
                "text": "",
            },
        ],
    }


def _write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


# --------------------------------------------------------------------------- #
# version
# --------------------------------------------------------------------------- #

def test_version_returns_zero_and_prints_version(capsys):
    rc = main(["version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert __version__ in out


# --------------------------------------------------------------------------- #
# parse
# --------------------------------------------------------------------------- #

def test_parse_returns_zero_and_prints_valid_json(capsys):
    rc = main(["parse", "click the login button"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list)
    assert data, "parse should emit at least one PromptAction"
    # Each entry should look like a serialized PromptAction.
    for entry in data:
        assert "intent" in entry
        assert "confidence" in entry


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #

def test_validate_good_file_returns_zero(tmp_path, capsys):
    good = _write_json(tmp_path / "good.json", _good_workflow_dict())
    rc = main(["validate", "--file", good])
    assert rc == 0
    out = capsys.readouterr().out
    assert "valid" in out.lower()


def test_validate_bad_file_returns_one(tmp_path, capsys):
    bad = _write_json(tmp_path / "bad.json", _bad_workflow_dict())
    rc = main(["validate", "--file", bad])
    assert rc == 1
    out = capsys.readouterr().out
    assert "invalid" in out.lower()


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #

def test_list_empty_dir_returns_zero(tmp_path):
    empty = tmp_path / "empty_workflows"
    rc = main(["list", "--dir", str(empty)])
    assert rc == 0


# --------------------------------------------------------------------------- #
# run-prompt (dry-run, no real actions)
# --------------------------------------------------------------------------- #

def test_run_prompt_dry_run_returns_zero(capsys):
    rc = main(["run-prompt", "wait 1 second", "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.strip(), "run-prompt should print an execution summary"


# --------------------------------------------------------------------------- #
# bad input / unknown subcommand never raises
# --------------------------------------------------------------------------- #

def test_unknown_subcommand_returns_nonzero_without_raising():
    rc = main(["definitely-not-a-command"])
    assert rc != 0


def test_bad_args_returns_nonzero_without_raising():
    # 'parse' requires a positional prompt argument; omitting it is a usage error.
    rc = main(["parse"])
    assert rc != 0


def test_no_subcommand_returns_nonzero(capsys):
    rc = main([])
    assert rc != 0
