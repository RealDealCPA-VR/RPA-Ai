"""Smoke tests: the package and its public API import and core engines construct.

Dependency-free: no pyautogui / GUI libs are imported here. Construction of
AutomationEngine and WorkflowExecutor must not require pyautogui at import or
__init__ time (GUI deps are expected to be lazily loaded).
"""

PUBLIC_NAMES = (
    "Workflow",
    "ActionStep",
    "PromptAction",
    "ExecutionResult",
    "AutomationEngine",
    "PromptParser",
    "WorkflowRecorder",
    "WorkflowManager",
    "WorkflowExecutor",
)


def test_import_package():
    import ai_rpa_system  # noqa: F401


def test_public_names_importable():
    import ai_rpa_system

    for name in PUBLIC_NAMES:
        assert hasattr(ai_rpa_system, name), f"missing public name: {name}"
        assert getattr(ai_rpa_system, name) is not None, f"public name is None: {name}"


def test_public_names_via_from_import():
    from ai_rpa_system import (  # noqa: F401
        Workflow,
        ActionStep,
        PromptAction,
        ExecutionResult,
        AutomationEngine,
        PromptParser,
        WorkflowRecorder,
        WorkflowManager,
        WorkflowExecutor,
    )

    # Each imported symbol must be a real, bound class/object.
    for obj in (
        Workflow,
        ActionStep,
        PromptAction,
        ExecutionResult,
        AutomationEngine,
        PromptParser,
        WorkflowRecorder,
        WorkflowManager,
        WorkflowExecutor,
    ):
        assert obj is not None


def test_automation_engine_constructs_without_gui_deps():
    from ai_rpa_system import AutomationEngine

    # Constructing must not raise (e.g. on a missing pyautogui) — GUI deps lazy.
    engine = AutomationEngine()
    assert engine is not None
    assert isinstance(engine, AutomationEngine)


def test_workflow_executor_constructs_without_gui_deps():
    from ai_rpa_system import WorkflowExecutor

    executor = WorkflowExecutor()
    assert executor is not None
    assert isinstance(executor, WorkflowExecutor)
