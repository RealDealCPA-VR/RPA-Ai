"""
Regression tests for the screenshot-action arbitrary-file-write fix.

The 'screenshot' action takes step.notes as a desired filename. Before the fix,
that raw, LLM/JSON-supplied string was passed straight to PIL Image.save(),
allowing a workflow to overwrite any file on disk. _safe_screenshot_path now
confines every path to the executor's screenshot_dir.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_rpa_system import WorkflowExecutor, Workflow, ActionStep


@pytest.fixture
def executor(tmp_path, monkeypatch):
    # Run from an isolated cwd so the default 'screenshots' dir lands in tmp.
    monkeypatch.chdir(tmp_path)
    return WorkflowExecutor()


ESCAPING = [
    "C:/Users/VR/.claude/settings.json",
    "../../evil.png",
    "/etc/passwd",
    "\\\\server\\share\\x.png",   # UNC
    "~/.bashrc",
    "..\\..\\win.ini",
]


@pytest.mark.parametrize("malicious", ESCAPING)
def test_escaping_paths_fall_back_inside_screenshot_dir(executor, malicious):
    base = executor.screenshot_dir.resolve()
    result = executor._safe_screenshot_path(malicious)
    resolved = Path(result).resolve()
    # Must stay strictly inside the screenshot directory.
    assert resolved == base or base in resolved.parents, (
        f"{malicious!r} resolved to {resolved}, which escapes {base}"
    )
    # And must NOT point at the literal attacker target.
    assert resolved != Path(malicious.lstrip("/\\~")).resolve()


def test_confined_relative_subpath_is_kept(executor):
    base = executor.screenshot_dir.resolve()
    result = Path(executor._safe_screenshot_path("subdir/ok.png")).resolve()
    assert base in result.parents
    assert result.name == "ok.png"


def test_empty_notes_autogenerates_in_dir(executor):
    base = executor.screenshot_dir.resolve()
    for notes in (None, "", "   "):
        result = Path(executor._safe_screenshot_path(notes)).resolve()
        assert result.parent == base


def test_screenshot_action_never_writes_outside_dir(executor):
    """End-to-end: a malicious screenshot workflow must hand the engine a
    save_path confined to the screenshot dir."""
    base = executor.screenshot_dir.resolve()
    executor.engine = MagicMock()
    captured = {}

    def fake_screenshot(save_path=None, region=None):
        captured["save_path"] = save_path
        return save_path

    executor.engine.screenshot.side_effect = fake_screenshot

    wf = Workflow(
        name="evil_shot",
        description="attempt arbitrary write",
        retry_on_failure=False,
        steps=[ActionStep(
            action="screenshot",
            description="malicious",
            notes="C:/Users/VR/.claude/settings.json",
            wait_before=0,
            wait_after=0,
        )],
    )
    result = executor.execute_workflow(wf)
    assert result.success
    resolved = Path(captured["save_path"]).resolve()
    assert resolved == base or base in resolved.parents
