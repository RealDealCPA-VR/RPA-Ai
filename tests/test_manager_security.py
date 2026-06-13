"""
Security tests for WorkflowManager on-disk persistence.

These tests verify that WorkflowManager refuses path-traversal / absolute /
drive-letter workflow names on every disk-touching entry point
(save/load/delete), that a successful save lands exactly inside the configured
storage directory, and that the atomic save leaves no leftover temp files and
always produces valid JSON. They use pytest's tmp_path for isolation and never
touch live recording (which would require pynput / a display).
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure the project root (which contains the ai_rpa_system package) is on
# sys.path even if a conftest.py is not present. The tests/ dir is a sibling
# of the ai_rpa_system package, so the project root is one level up.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai_rpa_system import ActionStep, Workflow, WorkflowManager  # noqa: E402


# Names that must be rejected as traversal / escape attempts on every
# disk-touching entry point.
MALICIOUS_NAMES = [
    "../evil",
    "..\\evil",
    "/etc/passwd",
    "C:\\Windows\\x",
    "a/b",
    "a\\b",
]


def _make_workflow(name="sample_workflow"):
    """Build a small but non-trivial Workflow for persistence tests."""
    return Workflow(
        name=name,
        description="A sample workflow used in security tests",
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
        ],
        tags=["demo", "security"],
    )


@pytest.fixture
def manager(tmp_path):
    """A WorkflowManager rooted in an isolated temp directory."""
    return WorkflowManager(str(tmp_path))


# --------------------------------------------------------------------------- #
# Baseline: a normal name still works end-to-end.
# --------------------------------------------------------------------------- #


def test_normal_name_saves_and_loads(manager):
    wf = _make_workflow("normal_workflow")

    path = manager.save_workflow(wf)
    assert isinstance(path, str)
    assert Path(path).exists()

    loaded = manager.load_workflow("normal_workflow")
    assert loaded is not None
    assert isinstance(loaded, Workflow)
    assert loaded.name == "normal_workflow"
    assert len(loaded.steps) == len(wf.steps)


# --------------------------------------------------------------------------- #
# Traversal names are rejected on every disk-touching entry point.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("bad_name", MALICIOUS_NAMES)
def test_save_workflow_rejects_traversal(manager, bad_name):
    wf = _make_workflow(bad_name)
    with pytest.raises(ValueError):
        manager.save_workflow(wf)


@pytest.mark.parametrize("bad_name", MALICIOUS_NAMES)
def test_load_workflow_rejects_traversal(manager, bad_name):
    with pytest.raises(ValueError):
        manager.load_workflow(bad_name)


@pytest.mark.parametrize("bad_name", MALICIOUS_NAMES)
def test_delete_workflow_rejects_traversal(manager, bad_name):
    with pytest.raises(ValueError):
        manager.delete_workflow(bad_name)


def test_traversal_does_not_write_outside_storage(manager, tmp_path):
    """A rejected save must not create any file anywhere on disk."""
    # Snapshot of the storage dir and its parent before the attempt.
    before_storage = set(tmp_path.iterdir())

    wf = _make_workflow("../escaped")
    with pytest.raises(ValueError):
        manager.save_workflow(wf)

    # No file appeared inside the storage dir, and crucially nothing named
    # 'escaped.json' leaked into the parent (tmp_path's parent).
    assert set(tmp_path.iterdir()) == before_storage
    assert not (tmp_path.parent / "escaped.json").exists()


# --------------------------------------------------------------------------- #
# A successful save lands exactly inside the storage directory.
# --------------------------------------------------------------------------- #


def test_saved_file_is_inside_storage_dir(manager, tmp_path):
    wf = _make_workflow("inside_check")
    path = Path(manager.save_workflow(wf))

    storage = tmp_path.resolve()
    assert path.resolve().parent == storage
    assert path.name == "inside_check.json"
    # The file is genuinely a child of the storage directory.
    assert path.resolve().is_relative_to(storage)


# --------------------------------------------------------------------------- #
# Atomic save: overwriting leaves valid JSON and no temp-file litter.
# --------------------------------------------------------------------------- #


def test_atomic_overwrite_leaves_valid_json_no_temp_files(manager, tmp_path):
    wf = _make_workflow("atomic")
    manager.save_workflow(wf)

    # Overwrite the same workflow (now with a different shape) several times.
    wf.description = "Updated description after overwrite"
    wf.steps.append(
        ActionStep(action="screenshot", description="Capture final state")
    )
    final_path = Path(manager.save_workflow(wf))
    manager.save_workflow(wf)

    # The on-disk file is valid, parseable JSON reflecting the latest write.
    assert final_path.exists()
    raw = final_path.read_text()
    data = json.loads(raw)
    assert data["name"] == "atomic"
    assert data["description"] == "Updated description after overwrite"

    # And it round-trips back through the manager into a real Workflow.
    reloaded = manager.load_workflow("atomic")
    assert reloaded is not None
    assert reloaded.description == "Updated description after overwrite"
    assert len(reloaded.steps) == 3

    # No leftover temp files of any kind in the storage directory.
    leftover_tmp = list(tmp_path.glob("*.tmp")) + list(tmp_path.glob(".*.tmp"))
    assert leftover_tmp == []

    # Exactly one JSON artifact remains: the workflow itself.
    json_files = list(tmp_path.glob("*.json"))
    assert json_files == [final_path]
