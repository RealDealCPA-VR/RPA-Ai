"""
Tests for ai_rpa_system.validator.validate_workflow.

These tests construct Workflow/ActionStep models directly and assert that a
fully-valid workflow yields no issues, while each rule violation produces a
clear message that references the offending 1-based step index.

The package is exercised entirely headless: no GUI dependencies
(pyautogui / pynput) are imported here, and all step waits are pinned to 0.
"""

import sys
from pathlib import Path

import pytest

# Ensure the project root (containing the ai_rpa_system package) is importable
# even if no conftest.py is present.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_rpa_system import validate_workflow, Workflow, ActionStep  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_step(action, description=None, **kwargs):
    """Build an ActionStep with waits pinned to 0 and a default description."""
    kwargs.setdefault("wait_before", 0)
    kwargs.setdefault("wait_after", 0)
    if description is None:
        description = f"{action} step"
    return ActionStep(action=action, description=description, **kwargs)


def make_workflow(*steps, name="wf", description="a workflow"):
    """Build a Workflow from the given steps."""
    return Workflow(name=name, description=description, steps=list(steps))


def mentions_step(issues, index):
    """True if any issue message references the given 1-based step index."""
    token = f"Step {index}"
    return any(token in msg for msg in issues)


# ---------------------------------------------------------------------------
# Fully-valid workflow
# ---------------------------------------------------------------------------

def test_fully_valid_workflow_returns_empty_list():
    wf = make_workflow(
        make_step("click", coordinates=[10, 20]),
        make_step("double_click", coordinates=[30, 40]),
        make_step("right_click", coordinates=[50, 60]),
        make_step("click", image_path="button.png"),
        make_step("move_mouse", coordinates=[1, 2]),
        make_step("drag", coordinates=[1, 2], end_coordinates=[3, 4]),
        make_step("drag", coordinates=[1, 2], notes="from 1 to 99"),
        make_step("type", text="hello"),
        make_step("press_key", key="enter"),
        make_step("hotkey", keys=["ctrl", "c"]),
        make_step("open_application", target="notepad"),
        make_step("close_application", text="notepad"),
        make_step("find_element", image_path="icon.png"),
        make_step("wait", wait_before=0, wait_after=0),
        make_step("screenshot"),
        make_step("scroll"),
    )
    assert validate_workflow(wf) == []


def test_empty_workflow_is_valid():
    assert validate_workflow(make_workflow()) == []


# ---------------------------------------------------------------------------
# Click / double_click / right_click
# ---------------------------------------------------------------------------

def test_click_without_coordinates_or_image_is_invalid():
    wf = make_workflow(make_step("click"))
    issues = validate_workflow(wf)
    assert issues
    assert mentions_step(issues, 1)


def test_click_with_image_path_is_valid():
    wf = make_workflow(make_step("click", image_path="ok.png"))
    assert validate_workflow(wf) == []


def test_double_click_without_coordinates_is_invalid():
    wf = make_workflow(make_step("double_click"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_right_click_image_path_not_accepted_without_coordinates():
    # image_path is only valid for click/find_element, not right_click.
    wf = make_workflow(make_step("right_click", image_path="x.png"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# move_mouse
# ---------------------------------------------------------------------------

def test_move_mouse_requires_coordinates():
    wf = make_workflow(make_step("move_mouse"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# drag
# ---------------------------------------------------------------------------

def test_drag_missing_end_is_invalid():
    wf = make_workflow(make_step("drag", coordinates=[1, 2]))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_drag_missing_start_coordinates_is_invalid():
    wf = make_workflow(make_step("drag", end_coordinates=[3, 4]))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_drag_with_two_numbers_in_notes_is_valid():
    wf = make_workflow(make_step("drag", coordinates=[1, 2], notes="go to 100 200"))
    assert validate_workflow(wf) == []


# ---------------------------------------------------------------------------
# type / press_key / hotkey
# ---------------------------------------------------------------------------

def test_type_without_text_is_invalid():
    wf = make_workflow(make_step("type"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_type_with_whitespace_only_text_is_invalid():
    wf = make_workflow(make_step("type", text="   "))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_press_key_without_key_is_invalid():
    wf = make_workflow(make_step("press_key"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_hotkey_with_fewer_than_two_keys_is_invalid():
    wf = make_workflow(make_step("hotkey", keys=["ctrl"]))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_hotkey_without_keys_is_invalid():
    wf = make_workflow(make_step("hotkey"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# open_application / close_application
# ---------------------------------------------------------------------------

def test_open_application_missing_target_and_text_is_invalid():
    wf = make_workflow(make_step("open_application"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_close_application_missing_target_and_text_is_invalid():
    wf = make_workflow(make_step("close_application"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_open_application_with_text_is_valid():
    wf = make_workflow(make_step("open_application", text="notepad"))
    assert validate_workflow(wf) == []


# ---------------------------------------------------------------------------
# find_element
# ---------------------------------------------------------------------------

def test_find_element_requires_image_path():
    wf = make_workflow(make_step("find_element"))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# wait / screenshot / scroll always ok
# ---------------------------------------------------------------------------

def test_wait_screenshot_scroll_are_always_ok():
    wf = make_workflow(
        make_step("wait"),
        make_step("screenshot"),
        make_step("scroll"),
    )
    assert validate_workflow(wf) == []


# ---------------------------------------------------------------------------
# Coordinate shape checks
# ---------------------------------------------------------------------------

def test_coordinates_of_wrong_length_is_invalid():
    wf = make_workflow(make_step("click", coordinates=[1, 2, 3]))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_end_coordinates_of_wrong_length_is_invalid():
    wf = make_workflow(
        make_step("drag", coordinates=[1, 2], end_coordinates=[3])
    )
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# Confidence range
# ---------------------------------------------------------------------------

def test_confidence_above_one_is_invalid():
    wf = make_workflow(make_step("click", coordinates=[1, 2], confidence=1.5))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


def test_confidence_below_zero_is_invalid():
    wf = make_workflow(make_step("click", coordinates=[1, 2], confidence=-0.1))
    issues = validate_workflow(wf)
    assert mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# Step-index reporting across multiple steps
# ---------------------------------------------------------------------------

def test_issue_reports_correct_step_index_for_later_step():
    wf = make_workflow(
        make_step("click", coordinates=[1, 2]),   # valid step 1
        make_step("type"),                          # invalid step 2
    )
    issues = validate_workflow(wf)
    assert mentions_step(issues, 2)
    assert not mentions_step(issues, 1)


# ---------------------------------------------------------------------------
# Workflow.validate_steps() delegation
# ---------------------------------------------------------------------------

def test_validate_steps_delegates_to_validate_workflow():
    valid = make_workflow(make_step("click", coordinates=[1, 2]))
    assert valid.validate_steps() == validate_workflow(valid)
    assert valid.validate_steps() == []

    invalid = make_workflow(make_step("type"))
    assert invalid.validate_steps() == validate_workflow(invalid)
    assert invalid.validate_steps()  # non-empty
    assert mentions_step(invalid.validate_steps(), 1)
