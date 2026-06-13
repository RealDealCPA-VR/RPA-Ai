"""
Workflow executor with LLM integration capabilities.
Executes workflows and provides detailed feedback for LLM analysis.
"""

import json
import time
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from .models import Workflow, ActionStep, ExecutionResult
from .automation_engine import AutomationEngine
from .workflow_manager import WorkflowManager
from .prompt_parser import PromptParser
from .validator import validate_workflow
from .security import scan_workflow
import logging

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Executes workflows with support for variable substitution and LLM integration.
    """

    # The 14 known/supported action types handled by _execute_step.
    SUPPORTED_ACTIONS = frozenset({
        "click", "double_click", "right_click", "type", "press_key", "hotkey",
        "move_mouse", "drag", "open_application", "close_application",
        "find_element", "scroll", "wait", "screenshot", "wait_for_element",
    })

    def __init__(self, workflow_manager: Optional[WorkflowManager] = None,
                 dry_run: bool = False):
        self.engine = AutomationEngine()
        self.dry_run = dry_run
        self.workflow_manager = workflow_manager or WorkflowManager()
        self.parser = PromptParser()
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def execute_workflow(self, workflow: Workflow,
                        variables: Optional[Dict[str, str]] = None,
                        take_screenshots: bool = False,
                        validate: bool = False,
                        extra_warnings: Optional[List[str]] = None,
                        safe: bool = True,
                        allow_unsafe: bool = False,
                        policy: Optional[Any] = None,
                        audit_log: Optional[str] = None) -> ExecutionResult:
        """
        Execute a complete workflow.

        Args:
            workflow: Workflow to execute
            variables: Optional variables for substitution
            take_screenshots: Whether to take screenshots during execution
            validate: If True, validate the workflow first and return a failed
                result (without executing any step) when issues are found
            extra_warnings: Optional warnings to prepend to the result's warnings
            safe: When True (default), run a security scan before executing and
                refuse to run workflows that contain CRITICAL findings.
            allow_unsafe: When True, bypass the CRITICAL-finding block entirely
                (the scan is skipped). Use only for trusted/explicit overrides.
            policy: Optional SafetyPolicy controlling the security scan. When
                None, the module DEFAULT_POLICY is used by scan_workflow.
            audit_log: Optional path. When provided, one JSON line is appended
                per executed step with keys {step, action, success, dry_run,
                ts_monotonic}. Text is never written; sensitive steps are noted
                as redacted.

        Returns:
            ExecutionResult with detailed execution information

        Note:
            Retry-on-failure applies to step-level failures (a step returning
            success=False). Exceptions raised around a step (e.g. in the
            wait_before sleep or screenshot capture) are recorded as a single
            step error and are not retried.
        """
        logger.info(f"Executing workflow: {workflow.name}")

        # Validate first if requested; bail out without executing on any issue.
        if validate:
            issues = validate_workflow(workflow)
            if issues:
                logger.error(f"Workflow validation failed: {issues}")
                return ExecutionResult(
                    workflow_name=workflow.name,
                    success=False,
                    steps_completed=0,
                    total_steps=len(workflow.steps),
                    execution_time=0.0,
                    errors=issues,
                    warnings=list(extra_warnings) if extra_warnings else [],
                    timestamp=datetime.now()
                )

        # Security scan. When enabled and not explicitly overridden, a CRITICAL
        # finding blocks the entire workflow (nothing is executed). Non-critical
        # findings are surfaced as warnings on the eventual result. A benign
        # workflow produces no findings, so default calls behave identically.
        scan_warnings: List[str] = []
        if safe and not allow_unsafe:
            findings = scan_workflow(workflow, policy)
            critical = [f for f in findings if f.severity == "critical"]
            if critical:
                logger.error(
                    f"Workflow blocked by security scan: "
                    f"{len(critical)} critical finding(s)"
                )
                return ExecutionResult(
                    workflow_name=workflow.name,
                    success=False,
                    steps_completed=0,
                    total_steps=len(workflow.steps),
                    execution_time=0.0,
                    errors=[str(f) for f in critical],
                    warnings=list(extra_warnings) if extra_warnings else [],
                    timestamp=datetime.now()
                )
            scan_warnings = [str(f) for f in findings if f.severity != "critical"]

        start_time = time.time()

        # Merge provided variables with workflow defaults
        execution_variables = {**workflow.variables, **(variables or {})}

        # Initialize result tracking
        steps_completed = 0
        errors = []
        warnings = list(extra_warnings) if extra_warnings else []
        warnings.extend(scan_warnings)
        step_results = []
        screenshots = []

        # Execute each step
        for i, step in enumerate(workflow.steps, 1):
            logger.info(f"Executing step {i}/{len(workflow.steps)}: {step.description}")

            try:
                # Wait before executing
                if step.wait_before > 0 and not self.dry_run:
                    time.sleep(step.wait_before)

                # Execute the step, honouring step.repeat (run the dispatch N
                # times; any failure within is a step failure). repeat defaults
                # to 1, so single-execution behaviour is unchanged.
                step_result = self._execute_repeated(step, execution_variables)
                step_results.append(step_result)

                if step_result["success"]:
                    steps_completed += 1
                else:
                    # An optional step that fails is tolerated: it records a
                    # warning instead of an error and does not flip success.
                    if step.optional:
                        warn_msg = (
                            f"Step {i} (optional) failed: "
                            f"{step_result.get('error', 'Unknown error')}"
                        )
                        warnings.append(warn_msg)
                        logger.warning(warn_msg)
                    else:
                        error_msg = f"Step {i} failed: {step_result.get('error', 'Unknown error')}"
                        errors.append(error_msg)
                        logger.error(error_msg)

                        # Retry logic
                        if workflow.retry_on_failure:
                            for retry in range(workflow.max_retries):
                                logger.info(f"Retrying step {i} (attempt {retry + 1}/{workflow.max_retries})")
                                if not self.dry_run:
                                    time.sleep(1)
                                step_result = self._execute_repeated(step, execution_variables)
                                if step_result["success"]:
                                    steps_completed += 1
                                    errors.pop()  # Remove the error
                                    step_results[-1] = step_result
                                    break

                # Audit log: one JSON line per executed step (after any retry).
                self._append_audit(audit_log, i, step, step_result)

                # Wait after executing. A 'wait' action already consumes its
                # duration inside _execute_step, so don't double-count wait_after
                # for it.
                if step.action != "wait" and step.wait_after > 0 and not self.dry_run:
                    time.sleep(step.wait_after)

                # Take screenshot if requested
                if take_screenshots and not self.dry_run:
                    screenshot_path = self.engine.screenshot(
                        save_path=str(self.screenshot_dir / f"step_{i}_{int(time.time())}.png")
                    )
                    if screenshot_path:
                        screenshots.append(screenshot_path)

            except Exception as e:
                # An optional step whose surrounding machinery raised is also
                # tolerated as a warning rather than a hard error.
                if step.optional:
                    warn_msg = f"Step {i} (optional) exception: {str(e)}"
                    warnings.append(warn_msg)
                    logger.warning(warn_msg)
                else:
                    error_msg = f"Step {i} exception: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

                exc_result = {
                    "step": i,
                    "action": step.action,
                    "success": False,
                    "error": str(e)
                }
                step_results.append(exc_result)
                self._append_audit(audit_log, i, step, exc_result)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Create result
        result = ExecutionResult(
            workflow_name=workflow.name,
            success=len(errors) == 0,
            steps_completed=steps_completed,
            total_steps=len(workflow.steps),
            execution_time=execution_time,
            errors=errors,
            warnings=warnings,
            step_results=step_results,
            screenshots=screenshots,
            timestamp=datetime.now()
        )
        
        logger.info(f"Workflow execution completed: {result.to_llm_summary()}")
        return result
    
    def execute_prompt(self, prompt: str, 
                      variables: Optional[Dict[str, str]] = None,
                      save_workflow: bool = False) -> ExecutionResult:
        """
        Execute a natural language prompt directly.
        
        Args:
            prompt: Natural language description of automation task
            variables: Optional variables for substitution
            save_workflow: Whether to save the generated workflow
        
        Returns:
            ExecutionResult with detailed execution information
        """
        logger.info(f"Executing prompt: {prompt}")
        
        # Parse prompt into workflow
        if any(sep in prompt.lower() for sep in ["then", "and then", "next", "after that"]):
            prompt_actions = self.parser.parse_multi_step(prompt)
        else:
            prompt_actions = [self.parser.parse(prompt)]
        
        # Combine all steps
        all_steps = []
        for action in prompt_actions:
            all_steps.extend(action.suggested_steps)

        # Detect low-confidence parses or empty results and surface as warnings.
        extra_warnings: List[str] = []
        low_conf = [a for a in prompt_actions if a.confidence < 0.3]
        if low_conf:
            lowest = min(a.confidence for a in low_conf)
            extra_warnings.append(
                f"Low parse confidence (lowest {lowest:.2f}); the generated "
                f"workflow may not accurately reflect the prompt: {prompt!r}"
            )
        if not all_steps:
            extra_warnings.append(
                f"No actionable steps were generated from the prompt: {prompt!r}"
            )

        # Create temporary workflow
        workflow = Workflow(
            name=f"prompt_workflow_{int(time.time())}",
            description=prompt,
            steps=all_steps,
            variables=variables or {}
        )

        # Save if requested
        if save_workflow:
            self.workflow_manager.save_workflow(workflow)

        # Execute the workflow
        return self.execute_workflow(workflow, variables,
                                     extra_warnings=extra_warnings or None)
    
    def execute_workflow_by_name(self, workflow_name: str,
                                 variables: Optional[Dict[str, str]] = None,
                                 take_screenshots: bool = False) -> ExecutionResult:
        """
        Load and execute a saved workflow by name.
        
        Args:
            workflow_name: Name of the workflow to execute
            variables: Optional variables for substitution
            take_screenshots: Whether to take screenshots during execution
        
        Returns:
            ExecutionResult with detailed execution information
        """
        workflow = self.workflow_manager.load_workflow(workflow_name)
        if not workflow:
            return ExecutionResult(
                workflow_name=workflow_name,
                success=False,
                steps_completed=0,
                total_steps=0,
                execution_time=0,
                errors=[f"Workflow '{workflow_name}' not found"],
                timestamp=datetime.now()
            )
        
        return self.execute_workflow(workflow, variables, take_screenshots)
    
    def _execute_step(self, step: ActionStep, variables: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a single action step.
        
        Args:
            step: ActionStep to execute
            variables: Variables for substitution
        
        Returns:
            Dictionary with execution result details
        """
        result = {
            "action": step.action,
            "description": step.description,
            "success": False,
            "error": None
        }
        
        try:
            # Substitute variables in text fields
            text = self._substitute_variables(step.text, variables) if step.text else None

            # Dry-run: simulate supported actions without touching the engine.
            # An unknown action still falls through to the real dispatch so it
            # produces the standard "Unknown action type" failure.
            if self.dry_run and step.action in self.SUPPORTED_ACTIONS:
                result["success"] = True
                result["dry_run"] = True
                result["simulated"] = f"Simulated '{step.action}' action (dry run; no engine call made)"
                return result

            # Guard coordinate shape before indexing so a malformed list (e.g.
            # [100]) yields a clean error rather than a cryptic IndexError.
            for field_name in ("coordinates", "end_coordinates"):
                value = getattr(step, field_name)
                if value is not None and (not isinstance(value, list) or len(value) != 2):
                    result["error"] = (
                        f"Invalid {field_name} {value!r}: expected [x, y] (a list of 2 ints)"
                    )
                    return result

            # Execute based on action type
            if step.action == "click":
                if step.coordinates:
                    success = self.engine.click(step.coordinates[0], step.coordinates[1])
                elif step.image_path:
                    location = self.engine.find_image_on_screen(step.image_path, step.confidence)
                    if location:
                        success = self.engine.click(location[0], location[1])
                    else:
                        result["error"] = f"Image not found: {step.image_path}"
                        return result
                else:
                    result["error"] = "No coordinates or image provided for click action"
                    return result
            
            elif step.action == "double_click":
                if step.coordinates:
                    success = self.engine.double_click(step.coordinates[0], step.coordinates[1])
                else:
                    result["error"] = "No coordinates provided for double_click action"
                    return result
            
            elif step.action == "right_click":
                if step.coordinates:
                    success = self.engine.right_click(step.coordinates[0], step.coordinates[1])
                else:
                    result["error"] = "No coordinates provided for right_click action"
                    return result
            
            elif step.action == "type":
                if text:
                    # Pass sensitivity through to the engine so secrets are
                    # redacted in its logs. Only forward the kwarg when the step
                    # is actually marked sensitive so benign workflows keep the
                    # exact pre-existing call shape type_text(text).
                    if step.sensitive:
                        success = self.engine.type_text(text, sensitive=True)
                    else:
                        success = self.engine.type_text(text)
                else:
                    result["error"] = "No text provided for type action"
                    return result
            
            elif step.action == "press_key":
                if step.key:
                    success = self.engine.press_key(step.key)
                else:
                    result["error"] = "No key provided for press_key action"
                    return result
            
            elif step.action == "hotkey":
                if step.keys:
                    success = self.engine.hotkey(*step.keys)
                else:
                    result["error"] = "No keys provided for hotkey action"
                    return result
            
            elif step.action == "move_mouse":
                if step.coordinates:
                    success = self.engine.move_mouse(step.coordinates[0], step.coordinates[1])
                else:
                    result["error"] = "No coordinates provided for move_mouse action"
                    return result

            elif step.action == "drag":
                end = step.end_coordinates or self._parse_drag_target(step.notes)
                if step.coordinates and end:
                    success = self.engine.drag(
                        step.coordinates[0], step.coordinates[1], end[0], end[1]
                    )
                else:
                    result["error"] = (
                        "Drag requires 'coordinates' (start) and 'end_coordinates' "
                        "(or an 'end'/'to [x, y]' note)"
                    )
                    return result

            elif step.action == "open_application":
                app = step.target or text
                if app:
                    success = self.engine.open_application(app)
                else:
                    result["error"] = "No target/application name provided for open_application"
                    return result

            elif step.action == "close_application":
                app = step.target or text
                if app:
                    success = self.engine.close_application(app)
                else:
                    result["error"] = "No target/application name provided for close_application"
                    return result

            elif step.action == "find_element":
                if step.image_path:
                    location = self.engine.find_image_on_screen(step.image_path, step.confidence)
                    if location:
                        success = True
                        result["location"] = [location[0], location[1]]
                    else:
                        result["error"] = f"Element/image not found: {step.image_path}"
                        return result
                else:
                    result["error"] = "No image_path provided for find_element action"
                    return result

            elif step.action == "scroll":
                # Extract scroll amount from notes or use default
                clicks = -5  # Default scroll down
                if step.notes and "amount:" in step.notes.lower():
                    match = re.search(r'amount:\s*(-?\d+)', step.notes, re.IGNORECASE)
                    if match:
                        clicks = int(match.group(1))
                
                if step.coordinates:
                    success = self.engine.scroll(clicks, step.coordinates[0], step.coordinates[1])
                else:
                    success = self.engine.scroll(clicks)
            
            elif step.action == "wait":
                wait_time = step.wait_after if step.wait_after > 0 else 1.0
                success = self.engine.wait(wait_time)

            elif step.action == "wait_for_element":
                if step.image_path:
                    location = self.engine.wait_for_image(
                        step.image_path,
                        timeout=step.timeout or 10.0,
                        interval=step.poll_interval or 0.5,
                        confidence=step.confidence,
                    )
                    if location:
                        success = True
                        result["location"] = [location[0], location[1]]
                    else:
                        result["error"] = (
                            f"Element/image did not appear within timeout: {step.image_path}"
                        )
                        return result
                else:
                    result["error"] = "No image_path provided for wait_for_element action"
                    return result

            elif step.action == "screenshot":
                save_path = self._safe_screenshot_path(step.notes)
                screenshot_path = self.engine.screenshot(save_path=save_path)
                success = screenshot_path is not None
                result["screenshot_path"] = screenshot_path
            
            else:
                result["error"] = f"Unknown action type: {step.action}"
                return result
            
            result["success"] = success
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error executing step: {e}")
        
        return result
    
    def _execute_repeated(self, step: ActionStep, variables: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a step, honouring ``step.repeat``.

        Runs ``_execute_step`` ``repeat`` times. The step succeeds only if every
        iteration succeeds; on the first failing iteration the failing result is
        returned immediately. With the default ``repeat == 1`` this is identical
        to a single ``_execute_step`` call, so existing behaviour is preserved.
        """
        repeat = getattr(step, "repeat", 1) or 1
        result = self._execute_step(step, variables)
        if repeat <= 1 or not result.get("success"):
            return result

        last = result
        for n in range(2, repeat + 1):
            last = self._execute_step(step, variables)
            if not last.get("success"):
                last["repeat_iteration"] = n
                return last
        last["repeat_count"] = repeat
        return last

    def _append_audit(self, audit_log: Optional[str], step_index: int,
                      step: ActionStep, step_result: Dict[str, Any]) -> None:
        """
        Append one JSON line describing an executed step to ``audit_log``.

        The raw step text is NEVER written. When ``step.sensitive`` is True the
        record explicitly notes ``"[REDACTED]"``. Audit failures must never
        break execution, so any I/O error is swallowed (logged at debug level).
        """
        if not audit_log:
            return
        entry = {
            "step": step_index,
            "action": step.action,
            "success": bool(step_result.get("success")),
            "dry_run": bool(step_result.get("dry_run", False)),
            "ts_monotonic": time.monotonic(),
        }
        if getattr(step, "sensitive", False):
            entry["text"] = "[REDACTED]"
        try:
            with open(audit_log, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        except Exception as e:  # pragma: no cover - audit must never break a run
            logger.debug(f"Failed to write audit log line: {e}")

    def _safe_screenshot_path(self, notes: Optional[str]) -> str:
        """
        Resolve a safe screenshot save path confined to ``self.screenshot_dir``.

        ``step.notes`` is treated as a desired filename. Absolute paths, parent
        traversal (``..``) and any path that would escape the screenshot
        directory are rejected; in those cases (or when no usable name is given)
        an auto-generated name inside ``screenshot_dir`` is used instead.
        """
        base = self.screenshot_dir.resolve()

        def _auto() -> str:
            return str(base / f"screenshot_{int(time.time() * 1000)}.png")

        if not notes or not notes.strip():
            return _auto()

        candidate = notes.strip()
        # Reject anything that is not a plain confined relative path. A leading
        # '~' is treated like an absolute path (no home expansion) so it can't
        # create a surprising '~' subdirectory.
        if (Path(candidate).is_absolute()
                or candidate.startswith(("/", "\\", "~"))):
            return _auto()
        if ".." in Path(candidate).parts or ":" in candidate:
            return _auto()

        target = (base / candidate)
        try:
            resolved = target.resolve()
        except (OSError, ValueError):
            return _auto()
        # Final containment check: resolved path must stay under screenshot_dir.
        if resolved != base and base not in resolved.parents:
            return _auto()

        resolved.parent.mkdir(parents=True, exist_ok=True)
        return str(resolved)

    @staticmethod
    def _parse_drag_target(notes: Optional[str]) -> Optional[List[int]]:
        """Parse drag end coordinates from a free-text note like 'Drag to [600, 450]'."""
        if not notes:
            return None
        match = re.search(r'\[?\s*(\d+)\s*,\s*(\d+)\s*\]?', notes)
        if match:
            return [int(match.group(1)), int(match.group(2))]
        return None

    def _substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """
        Substitute variables in text using {{variable_name}} syntax.
        
        Args:
            text: Text containing variable placeholders
            variables: Dictionary of variable values
        
        Returns:
            Text with variables substituted
        """
        if not text:
            return text
        
        # Find all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        
        def replace_var(match):
            var_name = match.group(1)
            return variables.get(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, text)
    
    def get_llm_friendly_result(self, result: ExecutionResult) -> str:
        """
        Convert execution result to LLM-friendly format.
        
        Args:
            result: ExecutionResult to convert
        
        Returns:
            Formatted string suitable for LLM consumption
        """
        return result.to_llm_summary()
