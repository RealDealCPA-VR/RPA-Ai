"""
Tests for the WorkflowExecutor additions: dry-run mode and the validate hook.

These tests run fully headless: no real engine is ever invoked. We replace
``executor.engine`` with a ``MagicMock`` and assert that, in the covered
scenarios, none of its methods are called.
"""

from unittest.mock import MagicMock

import pytest

from ai_rpa_system import WorkflowExecutor, Workflow, ActionStep


def _zero_wait(step: ActionStep) -> ActionStep:
    """Force a step's waits to 0 so tests never sleep."""
    step.wait_before = 0
    step.wait_after = 0
    return step


def _dry_run_workflow() -> Workflow:
    """A valid workflow whose steps would otherwise require a real engine."""
    return Workflow(
        name="dry_run_wf",
        description="click, type and hotkey that need a real engine",
        steps=[
            _zero_wait(ActionStep(
                action="click",
                description="Click at a point",
                coordinates=[100, 200],
            )),
            _zero_wait(ActionStep(
                action="type",
                description="Type some text",
                text="hello world",
            )),
            _zero_wait(ActionStep(
                action="hotkey",
                description="Press Ctrl+C",
                keys=["ctrl", "c"],
            )),
        ],
        retry_on_failure=False,
    )


def _invalid_workflow() -> Workflow:
    """An invalid workflow: a click with neither coordinates nor image_path."""
    return Workflow(
        name="invalid_wf",
        description="click missing coordinates",
        steps=[
            _zero_wait(ActionStep(
                action="click",
                description="Click with no target",
            )),
        ],
        retry_on_failure=False,
    )


def test_dry_run_simulates_without_calling_engine():
    """DRY-RUN: supported actions succeed and the engine is never touched."""
    ex = WorkflowExecutor(dry_run=True)
    ex.engine = MagicMock()

    wf = _dry_run_workflow()
    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.steps_completed == result.total_steps == len(wf.steps)
    assert result.errors == []

    # Every step was simulated, not executed.
    assert len(result.step_results) == len(wf.steps)
    for step_result in result.step_results:
        assert step_result.get("dry_run") is True
        assert step_result["success"] is True

    # The engine MagicMock recorded no method calls at all.
    assert ex.engine.mock_calls == []
    ex.engine.click.assert_not_called()
    ex.engine.type_text.assert_not_called()
    ex.engine.hotkey.assert_not_called()


def test_validate_hook_blocks_invalid_workflow():
    """VALIDATE HOOK: an invalid workflow fails up-front and runs nothing."""
    ex = WorkflowExecutor()
    ex.engine = MagicMock()

    wf = _invalid_workflow()
    result = ex.execute_workflow(wf, validate=True)

    assert result.success is False
    assert result.steps_completed == 0
    assert result.total_steps == len(wf.steps)
    assert result.execution_time == 0.0
    # Errors come straight from the validator (non-empty list of issues).
    assert result.errors
    assert any("1" in err for err in result.errors)

    # Nothing was executed: the engine MagicMock was never called.
    assert ex.engine.mock_calls == []


def test_validate_hook_passes_valid_dry_run_workflow():
    """A valid workflow passes validation and then succeeds under dry-run."""
    ex = WorkflowExecutor(dry_run=True)
    ex.engine = MagicMock()

    wf = _dry_run_workflow()
    result = ex.execute_workflow(wf, validate=True)

    assert result.success is True
    assert result.steps_completed == result.total_steps == len(wf.steps)
    assert result.errors == []
    for step_result in result.step_results:
        assert step_result.get("dry_run") is True

    # Still fully headless.
    assert ex.engine.mock_calls == []
