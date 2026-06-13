"""
Tests for the static security scanner (``ai_rpa_system.security``).

These tests exercise :func:`scan_workflow` against the SafetyPolicy contract:

* benign workflows produce NO critical findings,
* genuinely destructive / shell-launch operations DO produce critical findings,
* ordinary prose that merely *mentions* a scary word (e.g. "delete") is NOT
  flagged as critical (no false positives),
* workflow-level and per-step thresholds (length, wait/timeout) trip critical,
* risky-but-recoverable issues (off-screen / negative coordinates) are MAJOR,
  not critical.

Everything here is pure-python and headless-safe; no GUI deps are imported.
"""

from ai_rpa_system import (
    scan_workflow,
    SafetyPolicy,
    SecurityFinding,
    Workflow,
    ActionStep,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _criticals(findings):
    return [f for f in findings if f.severity == "critical"]


def _majors(findings):
    return [f for f in findings if f.severity == "major"]


def _wf(*steps, name="test_wf", description="a test workflow"):
    return Workflow(name=name, description=description, steps=list(steps))


# ---------------------------------------------------------------------------
# Benign workflow -> no critical findings
# ---------------------------------------------------------------------------

def test_benign_workflow_has_no_critical_findings():
    wf = _wf(
        ActionStep(action="click", description="Click the OK button", coordinates=[100, 200]),
        ActionStep(action="type", description="Type a greeting", text="hello"),
        ActionStep(action="hotkey", description="Copy selection", keys=["ctrl", "c"]),
    )

    findings = scan_workflow(wf)

    assert _criticals(findings) == []
    # All returned findings must be valid SecurityFinding objects.
    assert all(isinstance(f, SecurityFinding) for f in findings)


def test_scan_returns_list_of_security_findings():
    wf = _wf(
        ActionStep(action="open_application", description="Launch a shell", target="cmd"),
    )
    findings = scan_workflow(wf)
    assert isinstance(findings, list)
    assert all(isinstance(f, SecurityFinding) for f in findings)
    assert all(f.severity in {"critical", "major", "minor"} for f in findings)


# ---------------------------------------------------------------------------
# Shell / script launch via open_application -> CRITICAL
# ---------------------------------------------------------------------------

def test_open_application_cmd_is_critical():
    wf = _wf(
        ActionStep(action="open_application", description="Open a terminal", target="cmd"),
    )
    crit = _criticals(scan_workflow(wf))

    assert len(crit) >= 1
    finding = crit[0]
    assert finding.severity == "critical"
    # The finding must point at the offending (1-based) step.
    assert finding.step_index == 1


def test_open_application_powershell_is_critical():
    wf = _wf(
        ActionStep(action="click", description="Innocuous click first", coordinates=[5, 5]),
        ActionStep(action="open_application", description="Open PowerShell", target="powershell"),
    )
    crit = _criticals(scan_workflow(wf))

    assert any(f.step_index == 2 for f in crit)
    assert all(f.severity == "critical" for f in crit)


# ---------------------------------------------------------------------------
# Destructive command-shaped text -> CRITICAL
# ---------------------------------------------------------------------------

def test_type_rm_rf_root_is_critical():
    wf = _wf(
        ActionStep(action="type", description="Type a command", text="rm -rf /"),
    )
    crit = _criticals(scan_workflow(wf))

    assert len(crit) >= 1
    assert crit[0].step_index == 1
    assert crit[0].severity == "critical"


def test_type_format_c_is_critical():
    wf = _wf(
        ActionStep(action="type", description="Type a command", text="format c:"),
    )
    crit = _criticals(scan_workflow(wf))

    assert len(crit) >= 1
    assert crit[0].step_index == 1


def test_type_shutdown_is_critical():
    wf = _wf(
        ActionStep(action="type", description="Type a command", text="shutdown /s"),
    )
    crit = _criticals(scan_workflow(wf))

    assert len(crit) >= 1
    assert crit[0].step_index == 1


# ---------------------------------------------------------------------------
# False-positive guard: ordinary prose must NOT be critical
# ---------------------------------------------------------------------------

def test_ordinary_delete_sentence_is_not_critical():
    wf = _wf(
        ActionStep(
            action="type",
            description="Compose a friendly message",
            text="delete the message",
        ),
    )
    crit = _criticals(scan_workflow(wf))

    assert crit == []


def test_prose_with_delete_word_is_not_critical():
    # Several prose sentences that merely contain the word "delete" (but are not
    # shaped like a destructive shell command) must NOT trip a critical finding.
    for sentence in (
        "delete the message",
        "Please delete the old draft when you have a moment.",
        "I will delete that paragraph later.",
    ):
        wf = _wf(
            ActionStep(action="type", description="Compose text", text=sentence),
        )
        assert _criticals(scan_workflow(wf)) == [], sentence


# ---------------------------------------------------------------------------
# Workflow length threshold -> CRITICAL
# ---------------------------------------------------------------------------

def test_workflow_exceeding_max_steps_is_critical():
    policy = SafetyPolicy()
    steps = [
        ActionStep(action="click", description="Click", coordinates=[1, 2])
        for _ in range(policy.max_steps + 1)
    ]
    wf = _wf(*steps)

    crit = _criticals(scan_workflow(wf, policy))

    assert len(crit) >= 1
    assert any(f.category == "workflow_too_long" for f in crit)


def test_workflow_at_max_steps_is_not_too_long():
    policy = SafetyPolicy(max_steps=3)
    steps = [
        ActionStep(action="click", description="Click", coordinates=[1, 2])
        for _ in range(policy.max_steps)
    ]
    wf = _wf(*steps)

    crit = _criticals(scan_workflow(wf, policy))

    assert not any(f.category == "workflow_too_long" for f in crit)


# ---------------------------------------------------------------------------
# Excessive wait / timeout -> CRITICAL
# ---------------------------------------------------------------------------

def test_timeout_exceeding_max_wait_is_critical():
    policy = SafetyPolicy()
    wf = _wf(
        ActionStep(
            action="wait_for_element",
            description="Wait for an element",
            image_path="button.png",
            timeout=policy.max_wait_seconds + 1.0,
        ),
    )
    crit = _criticals(scan_workflow(wf, policy))

    assert len(crit) >= 1
    finding = next(f for f in crit if f.category == "excessive_wait")
    assert finding.step_index == 1
    assert finding.severity == "critical"


def test_poll_interval_within_limit_is_not_critical():
    wf = _wf(
        ActionStep(
            action="wait_for_element",
            description="Wait for an element",
            image_path="button.png",
            timeout=10.0,
            poll_interval=0.5,
        ),
    )
    crit = _criticals(scan_workflow(wf))

    assert crit == []


# ---------------------------------------------------------------------------
# Off-screen / negative coordinates -> MAJOR (not critical)
# ---------------------------------------------------------------------------

def test_negative_coordinates_are_major_not_critical():
    wf = _wf(
        ActionStep(action="click", description="Click off-screen", coordinates=[-5, -9]),
    )
    findings = scan_workflow(wf)

    assert _criticals(findings) == []

    majors = _majors(findings)
    coord_majors = [f for f in majors if f.category == "suspicious_coordinates"]
    assert len(coord_majors) >= 1
    assert coord_majors[0].step_index == 1
    assert coord_majors[0].severity == "major"


def test_negative_end_coordinates_for_drag_are_major():
    wf = _wf(
        ActionStep(
            action="drag",
            description="Drag to an off-screen point",
            coordinates=[10, 10],
            end_coordinates=[-100, 50],
        ),
    )
    findings = scan_workflow(wf)

    assert _criticals(findings) == []
    assert any(
        f.severity == "major" and f.step_index == 1 for f in findings
    )


# ---------------------------------------------------------------------------
# Findings carry the offending step index
# ---------------------------------------------------------------------------

def test_critical_finding_reports_correct_step_index():
    wf = _wf(
        ActionStep(action="click", description="Benign click", coordinates=[10, 10]),
        ActionStep(action="type", description="Benign typing", text="hello world"),
        ActionStep(action="open_application", description="Open shell", target="powershell"),
    )
    crit = _criticals(scan_workflow(wf))

    assert len(crit) >= 1
    # The destructive step is the 3rd (1-based) step.
    assert any(f.step_index == 3 for f in crit)


def test_default_policy_is_a_safety_policy_instance():
    from ai_rpa_system.security import DEFAULT_POLICY

    assert isinstance(DEFAULT_POLICY, SafetyPolicy)
    # scan_workflow with no policy must behave like the default policy.
    wf = _wf(ActionStep(action="type", description="Greet", text="hello"))
    assert _criticals(scan_workflow(wf)) == _criticals(scan_workflow(wf, DEFAULT_POLICY))
