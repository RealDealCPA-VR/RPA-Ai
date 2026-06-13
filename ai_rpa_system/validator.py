"""
Workflow validation for the AI-powered RPA system.

Provides :func:`validate_workflow`, which statically checks a
:class:`~ai_rpa_system.models.Workflow` for structural problems before it is
executed. Validation is intentionally dependency-free and headless-safe.
"""

from typing import List

from .models import Workflow, ActionStep


# The known action types (must match models.ActionStep.action Literal).
KNOWN_ACTIONS = {
    "click", "double_click", "right_click",
    "type", "press_key", "hotkey",
    "move_mouse", "scroll", "drag",
    "wait", "screenshot", "find_element",
    "open_application", "close_application",
    "wait_for_element",
}

# Actions for which an image_path is an acceptable target.
_IMAGE_OK_ACTIONS = {"click", "find_element"}


def _is_coord_pair(value) -> bool:
    """True if ``value`` is a list of exactly 2 ints (bools excluded)."""
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(c, int) and not isinstance(c, bool) for c in value)
    )


def _count_numbers(text: str) -> int:
    """Count integer/decimal numbers found in a free-text string."""
    import re
    return len(re.findall(r"-?\d+(?:\.\d+)?", text or ""))


def validate_workflow(workflow: Workflow) -> List[str]:
    """
    Validate a workflow and return a list of human-readable problem messages.

    An empty list means the workflow is valid. Each message includes the
    1-based step index so problems can be located easily.
    """
    issues: List[str] = []

    steps: List[ActionStep] = list(getattr(workflow, "steps", []) or [])

    for idx, step in enumerate(steps, start=1):
        action = step.action
        coords = step.coordinates
        end_coords = step.end_coordinates
        image_path = step.image_path

        # Coordinate / end-coordinate shape checks (when present).
        if coords is not None and not _is_coord_pair(coords):
            issues.append(
                f"Step {idx} ({action}): coordinates must be a list of exactly 2 ints."
            )
        if end_coords is not None and not _is_coord_pair(end_coords):
            issues.append(
                f"Step {idx} ({action}): end_coordinates must be a list of exactly 2 ints."
            )

        # Confidence range check.
        if not (0.0 <= step.confidence <= 1.0):
            issues.append(
                f"Step {idx} ({action}): confidence must be within [0.0, 1.0]."
            )

        # repeat must be an int >= 1 (bools excluded). Uses getattr so the
        # validator stays robust even against older models lacking the field.
        repeat = getattr(step, "repeat", 1)
        if not (isinstance(repeat, int) and not isinstance(repeat, bool) and repeat >= 1):
            issues.append(
                f"Step {idx} ({action}): repeat must be an integer >= 1."
            )

        # timeout / poll_interval, when set, must be non-negative numbers.
        timeout = getattr(step, "timeout", None)
        if timeout is not None and not (
            isinstance(timeout, (int, float))
            and not isinstance(timeout, bool)
            and timeout >= 0
        ):
            issues.append(
                f"Step {idx} ({action}): timeout must be >= 0 when set."
            )

        poll_interval = getattr(step, "poll_interval", None)
        if poll_interval is not None and not (
            isinstance(poll_interval, (int, float))
            and not isinstance(poll_interval, bool)
            and poll_interval >= 0
        ):
            issues.append(
                f"Step {idx} ({action}): poll_interval must be >= 0 when set."
            )

        # Action must be known.
        if action not in KNOWN_ACTIONS:
            issues.append(
                f"Step {idx}: unknown action type '{action}'. "
                f"Must be one of the 14 known action types."
            )
            # Skip action-specific checks for an unknown action.
            continue

        has_coords = _is_coord_pair(coords)
        has_end_coords = _is_coord_pair(end_coords)
        has_image = bool(image_path)

        if action in ("click", "double_click", "right_click"):
            # image_path only valid for click/find_element.
            image_allowed = action in _IMAGE_OK_ACTIONS
            if has_coords:
                pass
            elif image_allowed and has_image:
                pass
            else:
                if image_allowed:
                    issues.append(
                        f"Step {idx} ({action}): requires coordinates (2 ints) "
                        f"or image_path."
                    )
                else:
                    issues.append(
                        f"Step {idx} ({action}): requires coordinates (2 ints) "
                        f"(image_path is only valid for click/find_element)."
                    )

        elif action == "move_mouse":
            if not has_coords:
                issues.append(
                    f"Step {idx} (move_mouse): requires coordinates (2 ints)."
                )

        elif action == "drag":
            if not has_coords:
                issues.append(
                    f"Step {idx} (drag): requires coordinates (2 ints)."
                )
            note_has_two = _count_numbers(step.notes or "") >= 2
            if not (has_end_coords or note_has_two):
                issues.append(
                    f"Step {idx} (drag): requires end_coordinates (2 ints) "
                    f"or a note containing two numbers."
                )

        elif action == "type":
            if not (step.text and step.text.strip()):
                issues.append(
                    f"Step {idx} (type): requires non-empty text."
                )

        elif action == "press_key":
            if not step.key:
                issues.append(
                    f"Step {idx} (press_key): requires key."
                )

        elif action == "hotkey":
            if not step.keys or len(step.keys) < 2:
                issues.append(
                    f"Step {idx} (hotkey): requires keys with at least 2 entries."
                )

        elif action in ("open_application", "close_application"):
            if not (step.target or step.text):
                issues.append(
                    f"Step {idx} ({action}): requires target or text."
                )

        elif action == "find_element":
            if not has_image:
                issues.append(
                    f"Step {idx} (find_element): requires image_path."
                )

        elif action == "wait_for_element":
            if not has_image:
                issues.append(
                    f"Step {idx} (wait_for_element): requires image_path."
                )

        # wait / screenshot / scroll: always ok.

    return issues
