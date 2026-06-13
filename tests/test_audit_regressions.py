"""
Regression tests for issues surfaced by the adversarial audit and fixed:

1. 'press <modifier>+<key>' / 'press the <k> key' / 'hit the <k> key' must NOT be
   swallowed by the generic 'click' intent.
2. The press_key/hit-key branch must preserve the actual key (not fall back to 'enter').
3. A 'screenshot' intent exists and produces a screenshot step.
4. double_click / right_click / close intents are reachable from natural language.
5. scroll honours an explicit count and direction.
6. A 'wait' action does not double-apply its delay in the executor.
7. Models use pydantic v2 ConfigDict (no class-based Config deprecation).
"""

from unittest.mock import MagicMock

import pytest
from pydantic import ConfigDict

from ai_rpa_system import PromptParser, Workflow, ActionStep, WorkflowExecutor


@pytest.fixture
def parser():
    return PromptParser()


def _first_step(parser, prompt):
    action = parser.parse(prompt)
    assert action.suggested_steps, f"no steps generated for {prompt!r} (intent={action.intent})"
    return action, action.suggested_steps[0]


def test_press_modifier_combo_is_hotkey(parser):
    action, step = _first_step(parser, "Press Ctrl+C")
    assert action.intent == "hotkey"
    assert step.action == "hotkey"
    assert step.keys == ["ctrl", "c"]


def test_press_named_key_is_press_key(parser):
    action, step = _first_step(parser, "press the enter key")
    assert action.intent == "press_key"
    assert step.action == "press_key"
    assert step.key == "enter"


def test_hit_named_key_preserves_key(parser):
    # Previously fell back to 'enter' because the extraction regex only matched 'press'.
    action, step = _first_step(parser, "hit the tab key")
    assert action.intent == "press_key"
    assert step.key == "tab"


def test_take_screenshot_intent(parser):
    action, step = _first_step(parser, "take a screenshot")
    assert action.intent == "screenshot"
    assert step.action == "screenshot"


def test_double_click_intent(parser):
    action, step = _first_step(parser, "double-click on the start button")
    assert action.intent == "double_click"
    assert step.action == "double_click"
    assert "start button" in (step.target or "")


def test_right_click_intent(parser):
    action, step = _first_step(parser, "right-click on the file")
    assert action.intent == "right_click"
    assert step.action == "right_click"


def test_close_application_intent(parser):
    action, step = _first_step(parser, "close notepad")
    assert action.intent == "close"
    assert step.action == "close_application"
    assert step.target == "notepad"


def test_scroll_with_count_and_direction(parser):
    _, step_down = _first_step(parser, "scroll down 3")
    assert step_down.action == "scroll"
    assert "amount: -3" in (step_down.notes or "")

    _, step_up = _first_step(parser, "scroll up 4")
    assert "amount: 4" in (step_up.notes or "")


def test_multistep_wait_then_screenshot_both_produce_steps(parser):
    actions = parser.parse_multi_step("Wait 2 seconds then take a screenshot")
    assert len(actions) == 2
    assert all(a.suggested_steps for a in actions), "both halves must produce a step"
    assert actions[0].suggested_steps[0].action == "wait"
    assert actions[1].suggested_steps[0].action == "screenshot"


def test_wait_action_not_double_delayed(monkeypatch):
    """The main loop must not sleep wait_after again for a 'wait' action."""
    import ai_rpa_system.executor as executor_mod

    sleep_calls = []
    monkeypatch.setattr(executor_mod.time, "sleep", lambda s: sleep_calls.append(s))

    ex = WorkflowExecutor()
    ex.engine = MagicMock()
    ex.engine.wait.return_value = True

    wf = Workflow(
        name="wait_wf",
        description="single wait",
        retry_on_failure=False,
        steps=[ActionStep(action="wait", description="wait", wait_before=0.0, wait_after=5.0)],
    )
    result = ex.execute_workflow(wf)

    assert result.success
    # The loop's own time.sleep must NOT have been invoked for the wait step's
    # wait_after (engine.wait is mocked and records nothing here).
    assert sleep_calls == [], f"unexpected loop sleeps: {sleep_calls}"
    ex.engine.wait.assert_called_once_with(5.0)


def test_malformed_coordinates_give_clean_error():
    """A 1-element coordinates list must produce a clear error, not IndexError."""
    ex = WorkflowExecutor()
    ex.engine = MagicMock()
    step = ActionStep(action="click", description="bad click", coordinates=[100],
                      wait_before=0, wait_after=0)
    res = ex._execute_step(step, {})
    assert res["success"] is False
    assert "Invalid coordinates" in (res["error"] or "")
    ex.engine.click.assert_not_called()

    # Drag with a malformed end_coordinates is also guarded.
    step2 = ActionStep(action="drag", description="bad drag", coordinates=[1, 2],
                       end_coordinates=[5], wait_before=0, wait_after=0)
    res2 = ex._execute_step(step2, {})
    assert res2["success"] is False
    assert "Invalid end_coordinates" in (res2["error"] or "")


def test_models_use_configdict():
    """Models migrated off the deprecated class-based Config."""
    for model in (ActionStep, Workflow):
        assert isinstance(model.model_config, dict) or isinstance(model.model_config, ConfigDict.__mro__[0]) \
            or hasattr(model, "model_config")
        # No legacy inner Config class should remain.
        assert getattr(model, "Config", None) is None
