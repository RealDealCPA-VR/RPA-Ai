"""
Tests for PromptParser (ai_rpa_system/prompt_parser.py).

These tests only exercise the pure natural-language parsing layer. They never
import pyautogui/pynput, never construct an engine, and never perform real
input. Importing the package and constructing PromptParser must work headless.
"""

import json

import pytest

from ai_rpa_system import PromptParser, PromptAction, ActionStep


@pytest.fixture
def parser():
    return PromptParser()


def test_construct_parser_headless():
    """Constructing PromptParser must not require a display or GUI deps."""
    p = PromptParser()
    assert isinstance(p, PromptParser)


def test_parse_open_chrome(parser):
    action = parser.parse("open chrome")
    assert isinstance(action, PromptAction)
    assert action.intent == "open"
    assert action.entities.get("application") == "chrome"
    assert len(action.suggested_steps) >= 1
    assert isinstance(action.suggested_steps[0], ActionStep)


def test_parse_navigate_captures_url(parser):
    action = parser.parse("go to https://example.com")
    assert action.entities.get("url") == "https://example.com"


def test_parse_quoted_text_produces_type_step(parser):
    action = parser.parse("type 'hello world'")
    assert action.entities.get("text") == "hello world"
    type_steps = [s for s in action.suggested_steps if s.action == "type"]
    assert len(type_steps) >= 1
    assert type_steps[0].text == "hello world"


def test_parse_wait_produces_wait_step(parser):
    action = parser.parse("wait 3 seconds")
    assert action.intent == "wait"
    wait_steps = [s for s in action.suggested_steps if s.action == "wait"]
    assert len(wait_steps) >= 1
    # 3 seconds should be captured as a number entity
    assert 3.0 in action.entities.get("numbers", [])


def test_parse_multi_step_returns_multiple_actions(parser):
    actions = parser.parse_multi_step('type "a" then wait 2 seconds then type "b"')
    assert isinstance(actions, list)
    assert len(actions) >= 3
    assert all(isinstance(a, PromptAction) for a in actions)


def test_prompt_to_workflow_json_is_valid_workflow(parser):
    result = parser.prompt_to_workflow_json("open chrome")
    assert isinstance(result, str)
    data = json.loads(result)
    assert isinstance(data, dict)
    assert "name" in data
    assert "description" in data
    assert "steps" in data
    assert isinstance(data["steps"], list)


def test_prompt_to_workflow_json_custom_name(parser):
    result = parser.prompt_to_workflow_json("open chrome", workflow_name="my_flow")
    data = json.loads(result)
    assert data["name"] == "my_flow"


@pytest.mark.parametrize(
    "prompt",
    [
        "open chrome",
        "go to https://example.com",
        "type 'hello world'",
        "wait 3 seconds",
        "asdfghjkl qwertyuiop",
    ],
)
def test_confidence_in_unit_range(parser, prompt):
    action = parser.parse(prompt)
    assert isinstance(action.confidence, float)
    assert 0.0 <= action.confidence <= 1.0


def test_gibberish_yields_unknown_intent(parser):
    action = parser.parse("asdfghjkl qwertyuiop")
    assert action.intent == "unknown"
    assert action.confidence == 0.0
    assert action.suggested_steps == []
