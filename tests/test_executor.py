"""
Tests for WorkflowExecutor using a mocked AutomationEngine.

The real engine lazily imports pyautogui/pynput; these tests NEVER touch the
real engine. After constructing a WorkflowExecutor we replace ``ex.engine`` with
a MagicMock and drive each dispatch path via return values / side effects.

Run with: python -m pytest tests/test_executor.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure the project root (parent of ai_rpa_system) is importable even if no
# conftest is present.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_rpa_system import (  # noqa: E402
    ActionStep,
    Workflow,
    WorkflowExecutor,
    WorkflowManager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_executor(tmp_path):
    """Construct an executor with a tmp-dir manager and a mocked engine."""
    manager = WorkflowManager(storage_dir=str(tmp_path / "workflows"))
    ex = WorkflowExecutor(workflow_manager=manager)
    ex.engine = MagicMock()
    return ex


def fast_step(**kwargs):
    """ActionStep with zero waits so executor tests run instantly."""
    kwargs.setdefault("wait_before", 0)
    kwargs.setdefault("wait_after", 0)
    return ActionStep(**kwargs)


def make_workflow(steps, retry_on_failure=False, max_retries=3, **kwargs):
    return Workflow(
        name=kwargs.pop("name", "test_wf"),
        description=kwargs.pop("description", "test workflow"),
        steps=steps,
        retry_on_failure=retry_on_failure,
        max_retries=max_retries,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# (1) Happy path: type / press_key / hotkey / click(with coordinates)
# ---------------------------------------------------------------------------

def test_happy_path_workflow_all_success(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.type_text.return_value = True
    ex.engine.press_key.return_value = True
    ex.engine.hotkey.return_value = True
    ex.engine.click.return_value = True

    steps = [
        fast_step(action="type", description="type hello", text="hello"),
        fast_step(action="press_key", description="press enter", key="enter"),
        fast_step(action="hotkey", description="select all", keys=["ctrl", "a"]),
        fast_step(action="click", description="click button", coordinates=[10, 20]),
    ]
    wf = make_workflow(steps)

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.steps_completed == result.total_steps == 4
    assert result.errors == []

    ex.engine.type_text.assert_called_once_with("hello")
    ex.engine.press_key.assert_called_once_with("enter")
    ex.engine.hotkey.assert_called_once_with("ctrl", "a")
    ex.engine.click.assert_called_once_with(10, 20)


# ---------------------------------------------------------------------------
# (2) _substitute_variables behavior
# ---------------------------------------------------------------------------

def test_substitute_variables_known_and_unknown(tmp_path):
    ex = make_executor(tmp_path)
    assert ex._substitute_variables("hi {{name}}", {"name": "bob"}) == "hi bob"
    # Unknown variable left as-is.
    assert ex._substitute_variables("hi {{name}}", {}) == "hi {{name}}"
    assert ex._substitute_variables(
        "{{a}} and {{b}}", {"a": "x"}
    ) == "x and {{b}}"


# ---------------------------------------------------------------------------
# (3) End-to-end variable substitution in a type step
# ---------------------------------------------------------------------------

def test_variable_substitution_end_to_end(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.type_text.return_value = True

    steps = [fast_step(action="type", description="greet", text="hi {{name}}")]
    wf = make_workflow(steps)

    result = ex.execute_workflow(wf, variables={"name": "bob"})

    assert result.success is True
    ex.engine.type_text.assert_called_once_with("hi bob")


# ---------------------------------------------------------------------------
# (4) Drag dispatch
# ---------------------------------------------------------------------------

def test_drag_dispatch_with_coordinates(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.drag.return_value = True

    step = fast_step(
        action="drag",
        description="drag thing",
        coordinates=[10, 20],
        end_coordinates=[100, 200],
    )
    result = ex._execute_step(step, {})

    assert result["success"] is True
    ex.engine.drag.assert_called_once_with(10, 20, 100, 200)


# ---------------------------------------------------------------------------
# (5) open_application uses step.target
# ---------------------------------------------------------------------------

def test_open_application_uses_target(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.open_application.return_value = True

    step = fast_step(
        action="open_application",
        description="open notepad",
        target="notepad",
    )
    result = ex._execute_step(step, {})

    assert result["success"] is True
    ex.engine.open_application.assert_called_once_with("notepad")


# ---------------------------------------------------------------------------
# (6) find_element success and failure paths
# ---------------------------------------------------------------------------

def test_find_element_success_sets_location(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.find_image_on_screen.return_value = (100, 200)

    step = fast_step(
        action="find_element",
        description="find button",
        image_path="button.png",
    )
    result = ex._execute_step(step, {})

    assert result["success"] is True
    assert result["location"] == [100, 200]
    ex.engine.find_image_on_screen.assert_called_once_with("button.png", step.confidence)


def test_find_element_failure_when_not_found(tmp_path):
    ex = make_executor(tmp_path)
    ex.engine.find_image_on_screen.return_value = None

    step = fast_step(
        action="find_element",
        description="find missing button",
        image_path="missing.png",
    )
    result = ex._execute_step(step, {})

    assert result["success"] is False
    assert result["error"]
    assert "missing.png" in result["error"]
    assert "location" not in result


# ---------------------------------------------------------------------------
# (7) Missing data: click with no coordinates and no image_path
# ---------------------------------------------------------------------------

def test_click_without_coords_or_image_fails(tmp_path):
    ex = make_executor(tmp_path)

    step = fast_step(action="click", description="click nothing")
    result = ex._execute_step(step, {})

    assert result["success"] is False
    assert result["error"]
    ex.engine.click.assert_not_called()


# ---------------------------------------------------------------------------
# (8) execute_workflow_by_name for a missing workflow
# ---------------------------------------------------------------------------

def test_execute_workflow_by_name_not_found(tmp_path):
    ex = make_executor(tmp_path)

    result = ex.execute_workflow_by_name("nope")

    assert result.success is False
    assert result.steps_completed == 0
    assert any("not found" in e.lower() for e in result.errors)


# ---------------------------------------------------------------------------
# (9) Retry logic: fail first then succeed -> counted as completed
# ---------------------------------------------------------------------------

def test_retry_succeeds_on_second_attempt(tmp_path, monkeypatch):
    # Avoid the 1s sleep between retries.
    monkeypatch.setattr("ai_rpa_system.executor.time.sleep", lambda *a, **k: None)

    ex = make_executor(tmp_path)
    # First call returns False, second returns True.
    ex.engine.type_text.side_effect = [False, True]

    steps = [fast_step(action="type", description="type with retry", text="hello")]
    wf = make_workflow(steps, retry_on_failure=True, max_retries=2)

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.steps_completed == 1
    assert result.errors == []
    assert ex.engine.type_text.call_count == 2
