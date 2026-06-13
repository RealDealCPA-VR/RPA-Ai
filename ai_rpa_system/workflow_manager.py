"""
Workflow recording, storage, and management system.
"""

import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import Workflow, ActionStep
import logging

logger = logging.getLogger(__name__)

# Cached, lazily-imported pynput modules. Importing pynput at module load time
# requires an input backend (and a display on Linux), so it is deferred until a
# recording actually starts. This keeps the package importable on headless or
# GUI-less environments.
_mouse = None
_keyboard = None


def _get_pynput():
    """Import and cache pynput's mouse and keyboard modules on first use."""
    global _mouse, _keyboard
    if _mouse is None or _keyboard is None:
        try:
            from pynput import mouse, keyboard  # noqa: WPS433 (lazy import)
        except Exception as exc:  # pragma: no cover - environment dependent
            raise ImportError(
                "pynput is required for workflow recording but is not "
                "installed. Install the GUI extras with "
                "'pip install ai-rpa-system[gui]' or 'pip install pynput'."
            ) from exc
        _mouse, _keyboard = mouse, keyboard
    return _mouse, _keyboard


class WorkflowRecorder:
    """
    Records user desktop actions and converts them into reusable workflows.
    """
    
    def __init__(self):
        self.is_recording = False
        self.recorded_steps: List[ActionStep] = []
        self.start_time: Optional[float] = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_action_time: float = 0
    
    def start_recording(self, workflow_name: str, description: str = ""):
        """
        Start recording desktop actions.
        
        Args:
            workflow_name: Name for the workflow being recorded
            description: Optional description of what the workflow does
        """
        if self.is_recording:
            logger.warning("Already recording. Stop current recording first.")
            return
        
        logger.info(f"Starting workflow recording: {workflow_name}")
        self.is_recording = True
        self.recorded_steps = []
        self.start_time = time.time()
        self.last_action_time = self.start_time
        self.workflow_name = workflow_name
        self.workflow_description = description

        # Start listeners (pynput imported lazily here).
        mouse, keyboard = _get_pynput()
        self.mouse_listener = mouse.Listener(
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press
        )
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
        logger.info("Recording started. Perform your actions...")
    
    def stop_recording(self) -> Workflow:
        """
        Stop recording and return the recorded workflow.
        
        Returns:
            Workflow object containing all recorded steps
        """
        if not self.is_recording:
            logger.warning("Not currently recording.")
            return None
        
        logger.info("Stopping workflow recording...")
        self.is_recording = False
        
        # Stop listeners
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        # Create workflow
        workflow = Workflow(
            name=self.workflow_name,
            description=self.workflow_description or f"Recorded workflow: {self.workflow_name}",
            steps=self.recorded_steps,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info(f"Recording stopped. Captured {len(self.recorded_steps)} steps.")
        return workflow
    
    def _on_click(self, x: int, y: int, button, pressed: bool):
        """Handle mouse click events."""
        if not self.is_recording or not pressed:
            return
        
        current_time = time.time()
        wait_before = current_time - self.last_action_time
        
        mouse, _ = _get_pynput()
        action_type = "click"
        if button == mouse.Button.right:
            action_type = "right_click"
        
        step = ActionStep(
            action=action_type,
            description=f"{action_type.replace('_', ' ').title()} at ({x}, {y})",
            coordinates=[x, y],
            wait_before=round(wait_before, 2),
            timestamp=datetime.now()
        )
        
        self.recorded_steps.append(step)
        self.last_action_time = current_time
        logger.info(f"Recorded: {step.description}")
    
    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        """Handle mouse scroll events."""
        if not self.is_recording:
            return
        
        current_time = time.time()
        wait_before = current_time - self.last_action_time
        
        step = ActionStep(
            action="scroll",
            description=f"Scroll {'up' if dy > 0 else 'down'} at ({x}, {y})",
            coordinates=[x, y],
            wait_before=round(wait_before, 2),
            notes=f"Scroll amount: {dy}",
            timestamp=datetime.now()
        )
        
        self.recorded_steps.append(step)
        self.last_action_time = current_time
        logger.info(f"Recorded: {step.description}")
    
    def _on_key_press(self, key):
        """Handle keyboard press events."""
        if not self.is_recording:
            return
        
        current_time = time.time()
        wait_before = current_time - self.last_action_time
        
        try:
            # Handle regular character keys
            if hasattr(key, 'char') and key.char:
                # SECURITY: never log the actual typed character (could be a
                # password or other secret). The character is still captured in
                # the step's text field for replay, but the human-readable
                # description and the log line below are redacted.
                step = ActionStep(
                    action="type",
                    description="Type character",
                    text=key.char,
                    sensitive=True,
                    wait_before=round(wait_before, 2),
                    timestamp=datetime.now()
                )
            else:
                # Handle special keys
                key_name = str(key).replace('Key.', '')
                step = ActionStep(
                    action="press_key",
                    description=f"Press {key_name} key",
                    key=key_name,
                    wait_before=round(wait_before, 2),
                    timestamp=datetime.now()
                )
            
            self.recorded_steps.append(step)
            self.last_action_time = current_time
            logger.info(f"Recorded: {step.description}")
        
        except Exception as e:
            logger.error(f"Error recording key press: {e}")


class WorkflowManager:
    """
    Manages workflow storage, retrieval, and organization.
    """
    
    # Allowed workflow-name charset: letters, digits, dash, underscore, dot.
    # Anything else (path separators, drive letters, whitespace, etc.) is
    # rejected outright.
    _NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

    def __init__(self, storage_dir: str = "workflows"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"Workflow storage directory: {self.storage_dir}")

    def _safe_path(self, workflow_name: str) -> Path:
        """
        Resolve a workflow name to a safe path inside the storage directory.

        Rejects path-traversal and absolute/drive-letter inputs, restricts the
        name to a sane charset, and verifies the resolved file actually lives
        inside ``self.storage_dir``.

        Args:
            workflow_name: The bare workflow name (no extension, no path).

        Returns:
            Resolved ``Path`` to ``<storage_dir>/<name>.json``.

        Raises:
            ValueError: If the name is empty, contains path separators, '..',
                a drive letter, is absolute, uses a disallowed character, or
                would escape the storage directory.
        """
        if not isinstance(workflow_name, str) or not workflow_name.strip():
            raise ValueError("Workflow name must be a non-empty string.")

        name = workflow_name

        # Explicit, friendly rejections for the obvious attack shapes.
        if "/" in name or "\\" in name:
            raise ValueError(
                f"Invalid workflow name {workflow_name!r}: path separators "
                "are not allowed."
            )
        if ".." in name:
            raise ValueError(
                f"Invalid workflow name {workflow_name!r}: '..' is not allowed."
            )
        if os.path.isabs(name) or (len(name) >= 2 and name[1] == ":"):
            raise ValueError(
                f"Invalid workflow name {workflow_name!r}: absolute paths and "
                "drive letters are not allowed."
            )
        if not self._NAME_RE.match(name):
            raise ValueError(
                f"Invalid workflow name {workflow_name!r}: only letters, "
                "digits, '.', '-' and '_' are allowed (and it may not start "
                "with '.', '-' or '_')."
            )

        candidate = (self.storage_dir / f"{name}.json").resolve()
        base = self.storage_dir.resolve()

        # Final defense-in-depth: the resolved file must live directly inside
        # the storage directory.
        if candidate.parent != base:
            raise ValueError(
                f"Invalid workflow name {workflow_name!r}: resolved path "
                f"{candidate} is outside the storage directory {base}."
            )

        return candidate

    def save_workflow(self, workflow: Workflow) -> str:
        """
        Save a workflow to disk.
        
        Args:
            workflow: Workflow to save
        
        Returns:
            Path to saved workflow file
        """
        file_path = self._safe_path(workflow.name)

        workflow.updated_at = datetime.now()

        payload = workflow.model_dump_json(indent=2)

        # Atomic save: write to a temp file in the same directory, then
        # os.replace() it onto the final path. A crash mid-write therefore can
        # never corrupt an existing workflow file (the replace is atomic on the
        # same filesystem).
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.storage_dir),
            prefix=f".{file_path.stem}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(payload)
            os.replace(tmp_name, file_path)
        except BaseException:
            # Clean up the temp file on any failure so we don't litter the dir.
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        logger.info(f"Workflow saved: {file_path}")
        return str(file_path)
    
    def load_workflow(self, workflow_name: str) -> Optional[Workflow]:
        """
        Load a workflow from disk.
        
        Args:
            workflow_name: Name of the workflow to load
        
        Returns:
            Workflow object, or None if not found
        """
        file_path = self._safe_path(workflow_name)

        if not file_path.exists():
            logger.error(f"Workflow not found: {workflow_name}")
            return None

        with open(file_path, 'r') as f:
            workflow_data = json.load(f)

        workflow = Workflow(**workflow_data)
        logger.info(f"Workflow loaded: {workflow_name}")
        return workflow
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all available workflows.
        
        Returns:
            List of workflow metadata dictionaries
        """
        workflows = []
        
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    workflow_data = json.load(f)
                
                workflows.append({
                    "name": workflow_data.get("name"),
                    "description": workflow_data.get("description"),
                    "steps": len(workflow_data.get("steps", [])),
                    "created_at": workflow_data.get("created_at"),
                    "tags": workflow_data.get("tags", [])
                })
            except Exception as e:
                logger.error(f"Error reading workflow {file_path}: {e}")
        
        return workflows
    
    def delete_workflow(self, workflow_name: str) -> bool:
        """
        Delete a workflow from disk.
        
        Args:
            workflow_name: Name of the workflow to delete
        
        Returns:
            True if deleted successfully, False otherwise
        """
        file_path = self._safe_path(workflow_name)

        if not file_path.exists():
            logger.error(f"Workflow not found: {workflow_name}")
            return False

        file_path.unlink()
        logger.info(f"Workflow deleted: {workflow_name}")
        return True
    
    def export_workflow_for_llm(self, workflow_name: str) -> str:
        """
        Export workflow in LLM-friendly format with detailed descriptions.
        
        Args:
            workflow_name: Name of the workflow to export
        
        Returns:
            Formatted string representation suitable for LLM consumption
        """
        # Validate the name up front (also guards against traversal even though
        # load_workflow re-validates via _safe_path).
        self._safe_path(workflow_name)

        workflow = self.load_workflow(workflow_name)
        if not workflow:
            return f"Workflow '{workflow_name}' not found."
        
        output = f"# Workflow: {workflow.name}\n\n"
        output += f"**Description:** {workflow.description}\n\n"
        output += f"**Total Steps:** {len(workflow.steps)}\n\n"
        
        if workflow.variables:
            output += "**Variables:**\n"
            for key, value in workflow.variables.items():
                output += f"  - {key}: {value}\n"
            output += "\n"
        
        output += "**Steps:**\n\n"
        for i, step in enumerate(workflow.steps, 1):
            output += f"{i}. **{step.action.upper()}**\n"
            output += f"   - Description: {step.description}\n"
            if step.target:
                output += f"   - Target: {step.target}\n"
            if step.coordinates:
                output += f"   - Coordinates: {step.coordinates}\n"
            if step.text:
                output += f"   - Text: {step.text}\n"
            if step.key:
                output += f"   - Key: {step.key}\n"
            output += f"   - Wait before: {step.wait_before}s\n"
            output += f"   - Wait after: {step.wait_after}s\n"
            output += "\n"
        
        return output
