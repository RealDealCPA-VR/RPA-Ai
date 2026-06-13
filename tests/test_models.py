"""
Tests for the pydantic data models in ai_rpa_system.models.

These tests construct the models directly and verify field defaults,
validation of the constrained ``action`` field, JSON round-tripping,
and the ``ExecutionResult.to_llm_summary()`` rendering.

No GUI dependencies (pyautogui / pynput) are imported or exercised here.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Ensure the project root (containing the ai_rpa_system package) is importable
# even if no conftest.py is present.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_rpa_system.models import (  # noqa: E402
    ActionStep,
    Workflow,
    PromptAction,
    ExecutionResult,
)


# ---------------------------------------------------------------------------
# ActionStep
# ---------------------------------------------------------------------------

def test_action_step_required_fields_and_defaults():
    step = ActionStep(action="click", description="Click the login button")

    # Required fields preserved.
    assert step.action == "click"
    assert step.description == "Click the login button"

    # Optional fields default to None.
    assert step.target is None
    assert step.coordinates is None
    assert step.end_coordinates is None
    assert step.text is None
    assert step.key is None
    assert step.keys is None
    assert step.image_path is None
    assert step.timestamp is None
    assert step.notes is None

    # Scalar defaults.
    assert step.wait_before == 0.5
    assert step.wait_after == 0.5
    assert step.confidence == 0.8


def test_action_step_missing_required_raises():
    # description is required.
    with pytest.raises(ValidationError):
        ActionStep(action="click")

    # action is required.
    with pytest.raises(ValidationError):
        ActionStep(description="no action provided")


def test_action_step_invalid_action_raises():
    with pytest.raises(ValidationError):
        ActionStep(action="teleport", description="not a valid action")


@pytest.mark.parametrize(
    "action",
    [
        "click", "double_click", "right_click",
        "type", "press_key", "hotkey",
        "move_mouse", "scroll", "drag",
        "wait", "screenshot", "find_element",
        "open_application", "close_application",
    ],
)
def test_action_step_accepts_all_literal_actions(action):
    step = ActionStep(action=action, description=f"do {action}")
    assert step.action == action


def test_action_step_accepts_end_coordinates():
    step = ActionStep(
        action="drag",
        description="Drag from A to B",
        coordinates=[10, 20],
        end_coordinates=[100, 200],
    )
    assert step.coordinates == [10, 20]
    assert step.end_coordinates == [100, 200]


def test_action_step_accepts_optional_metadata():
    now = datetime.now()
    step = ActionStep(
        action="hotkey",
        description="Copy",
        keys=["ctrl", "c"],
        timestamp=now,
        notes="amount: -3",
    )
    assert step.keys == ["ctrl", "c"]
    assert step.timestamp == now
    assert step.notes == "amount: -3"


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

def test_workflow_defaults():
    wf = Workflow(name="login", description="Log into the app")

    assert wf.name == "login"
    assert wf.description == "Log into the app"

    # Collection defaults are independent empties.
    assert wf.steps == []
    assert wf.variables == {}
    assert wf.tags == []

    # Execution settings.
    assert wf.retry_on_failure is True
    assert wf.max_retries == 3

    # Auto timestamps.
    assert isinstance(wf.created_at, datetime)
    assert isinstance(wf.updated_at, datetime)

    # author optional.
    assert wf.author is None


def test_workflow_missing_required_raises():
    with pytest.raises(ValidationError):
        Workflow(name="only_name")

    with pytest.raises(ValidationError):
        Workflow(description="only_description")


def test_workflow_default_collections_are_isolated():
    wf1 = Workflow(name="a", description="a")
    wf2 = Workflow(name="b", description="b")
    wf1.steps.append(ActionStep(action="wait", description="wait"))
    wf1.tags.append("x")
    wf1.variables["k"] = "v"
    # Mutating wf1 must not bleed into wf2.
    assert wf2.steps == []
    assert wf2.tags == []
    assert wf2.variables == {}


def test_workflow_with_steps():
    wf = Workflow(
        name="multi",
        description="two step workflow",
        steps=[
            ActionStep(action="click", description="click field", coordinates=[1, 2]),
            ActionStep(action="type", description="type text", text="hello"),
        ],
    )
    assert len(wf.steps) == 2
    assert wf.steps[0].action == "click"
    assert wf.steps[1].text == "hello"


def test_workflow_json_round_trip():
    wf = Workflow(
        name="round_trip",
        description="serialize then rebuild",
        steps=[
            ActionStep(action="click", description="step one", coordinates=[5, 6]),
            ActionStep(action="type", description="step two", text="{{user}}"),
            ActionStep(action="wait", description="step three"),
        ],
        variables={"user": "alice"},
        tags=["t1", "t2"],
    )

    as_json = wf.model_dump_json(indent=2)
    data = json.loads(as_json)
    rebuilt = Workflow(**data)

    assert rebuilt.name == wf.name
    assert rebuilt.description == wf.description
    assert len(rebuilt.steps) == len(wf.steps) == 3
    assert rebuilt.steps[0].action == "click"
    assert rebuilt.steps[1].text == "{{user}}"
    assert rebuilt.variables == {"user": "alice"}
    assert rebuilt.tags == ["t1", "t2"]


def test_workflow_model_dump_is_dict():
    wf = Workflow(name="d", description="dump")
    dumped = wf.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["name"] == "d"
    assert dumped["retry_on_failure"] is True
    assert dumped["max_retries"] == 3


# ---------------------------------------------------------------------------
# PromptAction
# ---------------------------------------------------------------------------

def test_prompt_action_construction_and_defaults():
    pa = PromptAction(intent="open", confidence=0.9)
    assert pa.intent == "open"
    assert pa.confidence == 0.9
    assert pa.entities == {}
    assert pa.suggested_steps == []


def test_prompt_action_with_entities_and_steps():
    pa = PromptAction(
        intent="open_and_navigate",
        entities={"application": "chrome", "url": "https://example.com"},
        confidence=0.95,
        suggested_steps=[ActionStep(action="open_application", description="open chrome")],
    )
    assert pa.entities["application"] == "chrome"
    assert pa.entities["url"] == "https://example.com"
    assert len(pa.suggested_steps) == 1
    assert pa.suggested_steps[0].action == "open_application"


def test_prompt_action_missing_required_raises():
    # confidence is required.
    with pytest.raises(ValidationError):
        PromptAction(intent="open")

    # intent is required.
    with pytest.raises(ValidationError):
        PromptAction(confidence=0.5)


# ---------------------------------------------------------------------------
# ExecutionResult
# ---------------------------------------------------------------------------

def _make_result(success: bool) -> ExecutionResult:
    return ExecutionResult(
        workflow_name="my_workflow",
        success=success,
        steps_completed=2 if success else 1,
        total_steps=2,
        execution_time=1.234,
        errors=[] if success else ["boom"],
    )


def test_execution_result_defaults():
    result = ExecutionResult(
        workflow_name="w",
        success=True,
        steps_completed=0,
        total_steps=0,
        execution_time=0.0,
    )
    assert result.errors == []
    assert result.warnings == []
    assert result.step_results == []
    assert result.screenshots == []
    assert isinstance(result.timestamp, datetime)


def test_to_llm_summary_success():
    summary = _make_result(success=True).to_llm_summary()
    assert "my_workflow" in summary
    assert "Success" in summary
    assert "Failed" not in summary
    assert "2/2 steps" in summary


def test_to_llm_summary_failure():
    summary = _make_result(success=False).to_llm_summary()
    assert "my_workflow" in summary
    assert "Failed" in summary
    assert "Errors:" in summary
    assert "boom" in summary


def test_to_llm_summary_includes_warnings():
    result = ExecutionResult(
        workflow_name="warny",
        success=True,
        steps_completed=1,
        total_steps=1,
        execution_time=0.5,
        warnings=["slow step"],
    )
    summary = result.to_llm_summary()
    assert "Warnings:" in summary
    assert "slow step" in summary


def test_execution_result_json_round_trip():
    result = _make_result(success=False)
    data = json.loads(result.model_dump_json(indent=2))
    rebuilt = ExecutionResult(**data)
    assert rebuilt.workflow_name == "my_workflow"
    assert rebuilt.success is False
    assert rebuilt.errors == ["boom"]
    assert rebuilt.total_steps == 2
