"""
Tests for the security-hardening + power-feature additions to
:class:`WorkflowExecutor.execute_workflow`.

Everything runs fully headless: ``ex.engine`` is replaced with a ``MagicMock``
so no real automation engine (and thus no GUI dependency) is ever touched.
``wait_before``/``wait_after`` are pinned to 0 on every step so tests never
sleep.
"""

import json
from unittest.mock import MagicMock

from ai_rpa_system import WorkflowExecutor, Workflow, ActionStep


def _zero_wait(step: ActionStep) -> ActionStep:
    """Force a step's waits to 0 so tests never sleep."""
    step.wait_before = 0
    step.wait_after = 0
    return step


def _make_executor() -> WorkflowExecutor:
    """A headless executor whose engine is a MagicMock."""
    ex = WorkflowExecutor()
    ex.engine = MagicMock()
    return ex


def _open_cmd_workflow() -> Workflow:
    """A workflow that launches 'cmd' -- a critical shell-launch finding."""
    return Workflow(
        name="open_cmd_wf",
        description="opens the Windows command shell",
        steps=[
            _zero_wait(ActionStep(
                action="open_application",
                description="Open the command prompt",
                target="cmd",
            )),
        ],
        retry_on_failure=False,
    )


def _benign_type_workflow() -> Workflow:
    """A harmless type workflow that should always execute."""
    return Workflow(
        name="benign_wf",
        description="type a friendly greeting",
        steps=[
            _zero_wait(ActionStep(
                action="type",
                description="Type a greeting",
                text="hello world",
            )),
        ],
        retry_on_failure=False,
    )


# ---------------------------------------------------------------------------
# (1) Secure by default: opening 'cmd' is blocked, engine untouched.
# ---------------------------------------------------------------------------

def test_secure_by_default_blocks_cmd_launch():
    ex = _make_executor()
    wf = _open_cmd_workflow()

    result = ex.execute_workflow(wf)

    assert result.success is False
    assert result.steps_completed == 0
    assert result.total_steps == len(wf.steps)
    assert result.execution_time == 0.0
    assert result.errors
    assert any("critical" in err.lower() for err in result.errors)

    # No step was executed: the engine was never touched.
    assert ex.engine.mock_calls == []
    ex.engine.open_application.assert_not_called()


# ---------------------------------------------------------------------------
# (2) allow_unsafe=True lets the blocked workflow through.
# ---------------------------------------------------------------------------

def test_allow_unsafe_bypasses_block():
    ex = _make_executor()
    ex.engine.open_application.return_value = True
    wf = _open_cmd_workflow()

    result = ex.execute_workflow(wf, allow_unsafe=True)

    assert result.success is True
    assert result.steps_completed == len(wf.steps)
    ex.engine.open_application.assert_called_once_with("cmd")


# ---------------------------------------------------------------------------
# (3) safe=False also bypasses the scan.
# ---------------------------------------------------------------------------

def test_safe_false_bypasses_scan():
    ex = _make_executor()
    ex.engine.open_application.return_value = True
    wf = _open_cmd_workflow()

    result = ex.execute_workflow(wf, safe=False)

    assert result.success is True
    assert result.steps_completed == len(wf.steps)
    ex.engine.open_application.assert_called_once_with("cmd")


# ---------------------------------------------------------------------------
# (4) A benign workflow still executes normally under defaults.
# ---------------------------------------------------------------------------

def test_benign_workflow_executes_under_defaults():
    ex = _make_executor()
    ex.engine.type_text.return_value = True
    wf = _benign_type_workflow()

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.steps_completed == len(wf.steps)
    assert result.errors == []
    ex.engine.type_text.assert_called_once_with("hello world")


# ---------------------------------------------------------------------------
# (5) repeat=3 on a type step calls engine.type_text three times.
# ---------------------------------------------------------------------------

def test_repeat_runs_step_n_times():
    ex = _make_executor()
    ex.engine.type_text.return_value = True
    wf = Workflow(
        name="repeat_wf",
        description="type the same text three times",
        steps=[
            _zero_wait(ActionStep(
                action="type",
                description="Type repeatedly",
                text="tick",
                repeat=3,
            )),
        ],
        retry_on_failure=False,
    )

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert ex.engine.type_text.call_count == 3
    ex.engine.type_text.assert_called_with("tick")


# ---------------------------------------------------------------------------
# (6) optional=True step that fails -> warning, not error; success stays True.
# ---------------------------------------------------------------------------

def test_optional_step_failure_is_a_warning():
    ex = _make_executor()
    # The engine reports failure for this step.
    ex.engine.type_text.return_value = False
    wf = Workflow(
        name="optional_wf",
        description="an optional step that fails",
        steps=[
            _zero_wait(ActionStep(
                action="type",
                description="Optionally type",
                text="maybe",
                optional=True,
            )),
        ],
        retry_on_failure=False,
    )

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.errors == []
    assert result.warnings
    assert any("optional" in w.lower() for w in result.warnings)
    ex.engine.type_text.assert_called_once_with("maybe")


# ---------------------------------------------------------------------------
# (7) wait_for_element: hit returns location; miss is a step failure.
# ---------------------------------------------------------------------------

def test_wait_for_element_success_returns_location():
    ex = _make_executor()
    ex.engine.wait_for_image.return_value = (10, 20)
    wf = Workflow(
        name="wait_hit_wf",
        description="wait for an element that appears",
        steps=[
            _zero_wait(ActionStep(
                action="wait_for_element",
                description="Wait for the button",
                image_path="button.png",
            )),
        ],
        retry_on_failure=False,
    )

    result = ex.execute_workflow(wf)

    assert result.success is True
    assert result.steps_completed == 1
    assert result.step_results[0]["success"] is True
    assert result.step_results[0]["location"] == [10, 20]
    ex.engine.wait_for_image.assert_called_once()


def test_wait_for_element_miss_is_failure():
    ex = _make_executor()
    ex.engine.wait_for_image.return_value = None
    wf = Workflow(
        name="wait_miss_wf",
        description="wait for an element that never appears",
        steps=[
            _zero_wait(ActionStep(
                action="wait_for_element",
                description="Wait for the missing button",
                image_path="missing.png",
            )),
        ],
        retry_on_failure=False,
    )

    result = ex.execute_workflow(wf)

    assert result.success is False
    assert result.steps_completed == 0
    assert result.errors
    assert result.step_results[0]["success"] is False


# ---------------------------------------------------------------------------
# (8) audit_log: one JSON line per executed step; sensitive text redacted.
# ---------------------------------------------------------------------------

def test_audit_log_writes_lines_and_redacts_sensitive(tmp_path):
    ex = _make_executor()
    ex.engine.type_text.return_value = True
    ex.engine.click.return_value = True

    audit_file = tmp_path / "audit.log"

    wf = Workflow(
        name="audit_wf",
        description="a sensitive type plus a click",
        steps=[
            _zero_wait(ActionStep(
                action="type",
                description="Type a secret password",
                text="hunter2-super-secret",
                sensitive=True,
            )),
            _zero_wait(ActionStep(
                action="click",
                description="Click somewhere",
                coordinates=[5, 5],
            )),
        ],
        retry_on_failure=False,
    )

    result = ex.execute_workflow(wf, audit_log=str(audit_file))

    assert result.success is True
    assert audit_file.exists()

    lines = [ln for ln in audit_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == len(wf.steps)

    records = [json.loads(ln) for ln in lines]
    for rec in records:
        assert "step" in rec
        assert "action" in rec
        assert "success" in rec
        assert "dry_run" in rec
        assert "ts_monotonic" in rec

    # The sensitive step's text is redacted -- the raw secret never appears.
    raw = audit_file.read_text(encoding="utf-8")
    assert "hunter2-super-secret" not in raw
    assert "[REDACTED]" in raw

    # The sensitive flag was passed through to the engine.
    ex.engine.type_text.assert_called_once_with("hunter2-super-secret", sensitive=True)
