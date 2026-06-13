"""
Tests for WorkflowManager (ai_rpa_system.workflow_manager).

These tests exercise on-disk persistence only: save/load/list/delete and the
LLM export helper. They use pytest's tmp_path for an isolated storage_dir and
do NOT touch live recording (which would require pynput/a display).
"""

import sys
from pathlib import Path

import pytest

# Ensure the project root (which contains the ai_rpa_system package) is on
# sys.path even if a conftest.py is not present. The tests/ dir is a sibling
# of the ai_rpa_system package, so the project root is one level up.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai_rpa_system import Workflow, ActionStep, WorkflowManager  # noqa: E402


def _make_workflow(name="sample_workflow"):
    """Build a small but non-trivial Workflow for persistence tests."""
    return Workflow(
        name=name,
        description="A sample workflow used in tests",
        steps=[
            ActionStep(
                action="open_application",
                description="Open the calculator app",
                target="calculator",
            ),
            ActionStep(
                action="type",
                description="Type a number",
                text="42",
            ),
            ActionStep(
                action="screenshot",
                description="Capture the result",
            ),
        ],
        tags=["demo", "math"],
    )


@pytest.fixture
def manager(tmp_path):
    """A WorkflowManager rooted in an isolated temp directory."""
    return WorkflowManager(str(tmp_path))


def test_init_creates_storage_dir(tmp_path):
    target = tmp_path / "wf_store"
    assert not target.exists()
    mgr = WorkflowManager(str(target))
    assert target.exists()
    assert mgr.storage_dir == target


def test_save_workflow_returns_existing_path(manager):
    wf = _make_workflow()
    path = manager.save_workflow(wf)

    assert isinstance(path, str)
    saved = Path(path)
    assert saved.exists()
    assert saved.name == "sample_workflow.json"


def test_load_workflow_roundtrip(manager):
    wf = _make_workflow()
    manager.save_workflow(wf)

    loaded = manager.load_workflow("sample_workflow")

    assert loaded is not None
    assert isinstance(loaded, Workflow)
    assert loaded.name == wf.name
    assert loaded.description == wf.description
    assert len(loaded.steps) == len(wf.steps)
    # Step content survives the round-trip.
    assert loaded.steps[0].action == "open_application"
    assert loaded.steps[0].target == "calculator"
    assert loaded.tags == ["demo", "math"]


def test_load_workflow_missing_returns_none(manager):
    assert manager.load_workflow("does_not_exist") is None


def test_list_workflows_returns_metadata(manager):
    manager.save_workflow(_make_workflow("alpha"))

    entries = manager.list_workflows()

    assert len(entries) == 1
    entry = entries[0]
    for key in ("name", "description", "steps", "created_at", "tags"):
        assert key in entry
    assert entry["name"] == "alpha"
    assert entry["description"] == "A sample workflow used in tests"
    assert entry["steps"] == 3
    assert entry["tags"] == ["demo", "math"]


def test_list_workflows_multiple(manager):
    manager.save_workflow(_make_workflow("one"))
    manager.save_workflow(_make_workflow("two"))

    entries = manager.list_workflows()

    assert len(entries) == 2
    names = {e["name"] for e in entries}
    assert names == {"one", "two"}
    # Every entry reports the correct step count.
    assert all(e["steps"] == 3 for e in entries)


def test_list_workflows_empty(manager):
    assert manager.list_workflows() == []


def test_delete_workflow_removes_file(manager):
    wf = _make_workflow("to_delete")
    path = Path(manager.save_workflow(wf))
    assert path.exists()

    result = manager.delete_workflow("to_delete")

    assert result is True
    assert not path.exists()
    assert manager.load_workflow("to_delete") is None


def test_delete_workflow_missing_returns_false(manager):
    assert manager.delete_workflow("never_existed") is False


def test_export_workflow_for_llm_contains_name_and_steps(manager):
    wf = _make_workflow("exportable")
    manager.save_workflow(wf)

    exported = manager.export_workflow_for_llm("exportable")

    assert isinstance(exported, str)
    assert "exportable" in exported
    # Markdown-ish structure plus each step description.
    assert "# Workflow:" in exported
    for step in wf.steps:
        assert step.description in exported


def test_export_workflow_for_llm_missing(manager):
    exported = manager.export_workflow_for_llm("missing_one")
    assert "not found" in exported.lower()
    assert "missing_one" in exported
