"""
Static security scanning for RPA workflows.

This module performs a pure-python (GUI-free) analysis of a :class:`Workflow`
before it is executed. The goal is to be *secure by default* while remaining
*narrow* about what counts as CRITICAL: only genuinely destructive,
command-shaped operations (or shell-launch application targets) trip a critical
finding. Risky-but-recoverable patterns are reported as MAJOR, and stylistic
concerns as MINOR.

No ``pyautogui`` / ``pynput`` (or any GUI) imports here -- safe to import and
run headless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Workflow, ActionStep


# ---------------------------------------------------------------------------
# Finding + policy data structures
# ---------------------------------------------------------------------------

@dataclass
class SecurityFinding:
    """A single issue discovered while scanning a workflow.

    ``severity`` is one of ``'critical'``, ``'major'`` or ``'minor'``.
    ``step_index`` is 1-based for per-step findings, or 0 for workflow-level
    findings that are not tied to a specific step.
    """

    severity: str
    category: str
    step_index: int
    message: str

    def __str__(self) -> str:
        loc = f"step {self.step_index}" if self.step_index else "workflow"
        return f"[{self.severity.upper()}] {self.category} ({loc}): {self.message}"


@dataclass
class SafetyPolicy:
    """Thresholds and blocklists that drive :func:`scan_workflow`."""

    mode: str = "standard"
    max_steps: int = 200
    max_wait_seconds: float = 300
    max_text_length: int = 5000

    # Application names whose *launch* is considered a shell/script egress.
    blocked_app_substrings: tuple = (
        "cmd",
        "powershell",
        "pwsh",
        "bash",
        "sh",
        "zsh",
        "cmd.exe",
        "regedit",
        "reg",
        "wscript",
        "cscript",
        "mshta",
        "rundll32",
    )

    # Command-shaped, destructive text patterns (regex, matched case-insensitively
    # against step text/target/notes). These are intentionally anchored to
    # command syntax so that prose such as "please delete the old file" does NOT
    # match -- only things shaped like real shell commands do.
    critical_command_patterns: tuple = (
        # POSIX recursive/forced removal of root, home or wildcards.
        r"\brm\s+(?:-[a-z]*\s+)*-[a-z]*[rf][a-z]*\s+(?:-[a-z]+\s+)*(?:/|~|\*|\$HOME|\.\s*$)",
        r"\brm\s+-[rf]{1,2}\s",
        # Windows del/erase with force/quiet/recurse switches.
        r"\bdel\s+(?:/[a-z]\s+)*/[fqs]\b",
        r"\bdel\s+/[fqs]",
        r"\berase\s+/[fqs]",
        # rmdir / rd recursive.
        r"\brmdir\s+/s\b",
        r"\brd\s+/s\b",
        r"\bRemove-Item\b.*-Recurse",
        r"\bRemove-Item\b.*-Force",
        r"\bri\s+.*-Recurse",
        # Disk / filesystem formatting + partitioning.
        r"\bformat\s+[a-z]:",
        r"\bmkfs(?:\.[a-z0-9]+)?\b",
        r"\bdiskpart\b",
        r"\bcipher\s+/w",
        r"\bdd\s+if=.*of=/dev/",
        r">\s*/dev/sd[a-z]",
        # System power state.
        r"\bshutdown\b(?:\s+[-/]\w+)?",
        r"\breboot\b",
        r"\bhalt\b",
        r"\bpoweroff\b",
        r"\binit\s+0\b",
        # Registry destruction.
        r"\breg\s+delete\b",
        r"\bReg-Delete\b",
        r"\bRemove-Item\b.*HK(?:LM|CU|CR|U|CC):",
        # Classic fork bomb.
        r":\(\)\s*\{",
        r":\(\)\{",
        # Privilege / ownership wipes and overwrites.
        r"\bchmod\s+-R\s+000\b",
        r"\bchown\s+-R\b.*\s/\b",
        r"\bshred\b",
        r"\bwipefs\b",
        r"\bfdisk\b",
        # Recursive force delete via find.
        r"\bfind\s+/.*-delete\b",
        r"\bfind\s+.*-exec\s+rm\b",
        # Curl/wget piped straight into a shell (remote code execution).
        r"\b(?:curl|wget)\b[^|]*\|\s*(?:sudo\s+)?(?:bash|sh|zsh|pwsh|powershell)\b",
        # Drop all tables / database destruction.
        r"\bdrop\s+(?:database|table)\b",
        r"\btruncate\s+table\b",
    )

    # Hotkey component combos that are risky (e.g. alt+F4, alt+del style).
    risky_hotkey_tokens: tuple = ("del", "f4")


DEFAULT_POLICY = SafetyPolicy()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compile_patterns(patterns: tuple) -> List[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _step_texts(step: "ActionStep") -> List[tuple]:
    """Yield (field_name, value) for the free-text fields worth scanning."""
    out: List[tuple] = []
    for fname in ("text", "target", "notes", "description"):
        val = getattr(step, fname, None)
        if isinstance(val, str) and val:
            out.append((fname, val))
    return out


def _contains_blocked_app(value: str, blocked: tuple) -> Optional[str]:
    """Return the blocked substring that a launch target matches, else None.

    Matching is token-aware so that, e.g., ``"notepad"`` does not match
    ``"reg"`` and ``"shell"`` does not match ``"sh"`` -- we look at the basename
    of the target and its whitespace/path-delimited tokens.
    """
    lowered = value.strip().lower()
    if not lowered:
        return None

    # Build a set of candidate tokens: the whole string, the basename, and each
    # token split on path separators / whitespace, with any extension stripped.
    raw_tokens = re.split(r"[\s/\\]+", lowered)
    candidates = set()
    for tok in raw_tokens:
        tok = tok.strip().strip("\"'")
        if not tok:
            continue
        candidates.add(tok)
        # strip a trailing extension (cmd.exe -> cmd) but keep the full form too.
        base = tok.rsplit(".", 1)[0] if "." in tok else tok
        candidates.add(base)

    for blocked_name in blocked:
        bn = blocked_name.lower()
        if bn in candidates:
            return blocked_name
    return None


def _coords_problem(coords) -> Optional[str]:
    if not coords:
        return None
    try:
        for c in coords:
            if c is None:
                continue
            if c < 0:
                return "negative coordinate"
    except TypeError:
        return None
    return None


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

def scan_workflow(
    workflow: "Workflow",
    policy: Optional[SafetyPolicy] = None,
) -> List[SecurityFinding]:
    """Statically analyse ``workflow`` and return a list of findings.

    The list may contain ``critical``, ``major`` and ``minor`` findings. The
    caller (the executor) decides what to do with them; this function never
    raises for benign workflows and performs no I/O.
    """
    policy = policy or DEFAULT_POLICY
    findings: List[SecurityFinding] = []

    steps = list(getattr(workflow, "steps", []) or [])
    crit_patterns = _compile_patterns(policy.critical_command_patterns)

    # (c) Workflow length.
    if len(steps) > policy.max_steps:
        findings.append(
            SecurityFinding(
                severity="critical",
                category="workflow_too_long",
                step_index=0,
                message=(
                    f"Workflow has {len(steps)} steps, exceeding the maximum of "
                    f"{policy.max_steps}."
                ),
            )
        )

    for idx, step in enumerate(steps, start=1):
        action = getattr(step, "action", "") or ""
        texts = _step_texts(step)

        # (a) Shell/script launch via open/close application.
        if action in ("open_application", "close_application"):
            launch_value = getattr(step, "target", None) or getattr(step, "text", None) or ""
            if launch_value:
                blocked = _contains_blocked_app(launch_value, policy.blocked_app_substrings)
                if blocked:
                    findings.append(
                        SecurityFinding(
                            severity="critical",
                            category="shell_launch",
                            step_index=idx,
                            message=(
                                f"{action} targets a blocked shell/script host "
                                f"'{blocked}' (value: {launch_value!r})."
                            ),
                        )
                    )

        # (b) Destructive command-shaped text in any free-text field or notes.
        for fname, value in texts:
            matched_pattern = None
            for pat in crit_patterns:
                if pat.search(value):
                    matched_pattern = pat.pattern
                    break
            if matched_pattern is not None:
                findings.append(
                    SecurityFinding(
                        severity="critical",
                        category="destructive_command",
                        step_index=idx,
                        message=(
                            f"{fname!r} matches a destructive command pattern "
                            f"({matched_pattern!r})."
                        ),
                    )
                )

        # (d) Excessive wait / poll / timeout.
        for wfield in ("wait_before", "wait_after", "timeout", "poll_interval"):
            wval = getattr(step, wfield, None)
            if isinstance(wval, (int, float)) and wval > policy.max_wait_seconds:
                findings.append(
                    SecurityFinding(
                        severity="critical",
                        category="excessive_wait",
                        step_index=idx,
                        message=(
                            f"{wfield}={wval}s exceeds max_wait_seconds="
                            f"{policy.max_wait_seconds}s."
                        ),
                    )
                )

        # ---- MAJOR findings -------------------------------------------------

        # Off-screen / negative coordinates.
        for cfield in ("coordinates", "end_coordinates"):
            problem = _coords_problem(getattr(step, cfield, None))
            if problem:
                findings.append(
                    SecurityFinding(
                        severity="major",
                        category="suspicious_coordinates",
                        step_index=idx,
                        message=f"{cfield} has a {problem}.",
                    )
                )

        # Over-long text payloads.
        text_val = getattr(step, "text", None)
        if isinstance(text_val, str) and len(text_val) > policy.max_text_length:
            findings.append(
                SecurityFinding(
                    severity="major",
                    category="oversized_text",
                    step_index=idx,
                    message=(
                        f"text length {len(text_val)} exceeds max_text_length="
                        f"{policy.max_text_length}."
                    ),
                )
            )

        # Risky hotkey combos: alt + (del / f4).
        if action == "hotkey":
            keys = getattr(step, "keys", None) or []
            lowered_keys = {str(k).strip().lower() for k in keys}
            if "alt" in lowered_keys and lowered_keys.intersection(policy.risky_hotkey_tokens):
                findings.append(
                    SecurityFinding(
                        severity="major",
                        category="risky_hotkey",
                        step_index=idx,
                        message=(
                            f"hotkey combines 'alt' with a risky key "
                            f"({sorted(lowered_keys)})."
                        ),
                    )
                )

        # ---- MINOR findings -------------------------------------------------

        # Style: missing human-readable description.
        desc = getattr(step, "description", None)
        if not (isinstance(desc, str) and desc.strip()):
            findings.append(
                SecurityFinding(
                    severity="minor",
                    category="style",
                    step_index=idx,
                    message="step has no human-readable description.",
                )
            )

    return findings
