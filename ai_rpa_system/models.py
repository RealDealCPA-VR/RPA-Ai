"""
Data models for AI-powered RPA system.
These models are designed to be easily parseable by LLMs.
"""

from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class ActionStep(BaseModel):
    """
    Represents a single automation action step.
    Designed to be LLM-friendly with clear descriptions.
    """
    action: Literal[
        "click", "double_click", "right_click",
        "type", "press_key", "hotkey",
        "move_mouse", "scroll", "drag",
        "wait", "screenshot", "find_element",
        "open_application", "close_application",
        "wait_for_element"
    ] = Field(description="Type of action to perform")

    description: str = Field(description="Human-readable description of what this step does")

    # Target information
    target: Optional[str] = Field(None, description="Description of the target element (e.g., 'Login button', 'Username field')")
    coordinates: Optional[List[int]] = Field(None, description="[x, y] coordinates for the action (start point for a drag)")
    end_coordinates: Optional[List[int]] = Field(None, description="[x, y] end coordinates for a drag action")

    # Action-specific parameters
    text: Optional[str] = Field(None, description="Text to type (supports {{variable}} substitution)")
    key: Optional[str] = Field(None, description="Key to press (e.g., 'enter', 'tab', 'escape')")
    keys: Optional[List[str]] = Field(None, description="Keys for hotkey combination (e.g., ['ctrl', 'c'])")

    # Timing and conditions
    wait_before: float = Field(0.5, description="Seconds to wait before executing this step")
    wait_after: float = Field(0.5, description="Seconds to wait after executing this step")

    # Element recognition
    image_path: Optional[str] = Field(None, description="Path to image for visual element matching")
    confidence: float = Field(0.8, description="Confidence threshold for image matching (0.0-1.0)")

    # Metadata
    timestamp: Optional[datetime] = Field(None, description="When this step was recorded")
    notes: Optional[str] = Field(None, description="Additional notes or context")

    # Security and control flow
    sensitive: bool = Field(False, description="Redact this step's text in logs/audit output")
    repeat: int = Field(1, ge=1, description="Execute this step N times (must be >= 1)")
    optional: bool = Field(False, description="If the step fails, record a warning instead of failing the workflow")
    timeout: Optional[float] = Field(None, description="Seconds; for wait_for_element, default 10.0 when None")
    poll_interval: Optional[float] = Field(None, description="Seconds; for wait_for_element, default 0.5 when None")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "action": "click",
                "description": "Click the login button",
                "target": "Login button",
                "coordinates": [500, 300],
                "wait_before": 0.5,
                "wait_after": 1.0
            }
        }
    )


class Workflow(BaseModel):
    """
    Represents a complete automation workflow.
    LLM-friendly structure with clear metadata and steps.
    """
    name: str = Field(description="Unique identifier for this workflow")
    description: str = Field(description="What this workflow accomplishes")

    steps: List[ActionStep] = Field(default_factory=list, description="Ordered list of actions to perform")

    # Variables and parameters
    variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Variables that can be substituted in steps (e.g., {'username': 'user@example.com'})"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Execution settings
    retry_on_failure: bool = Field(True, description="Whether to retry failed steps")
    max_retries: int = Field(3, description="Maximum number of retries per step")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "login_workflow",
                "description": "Logs into the application with provided credentials",
                "steps": [
                    {
                        "action": "click",
                        "description": "Click username field",
                        "target": "Username input",
                        "coordinates": [400, 200]
                    },
                    {
                        "action": "type",
                        "description": "Enter username",
                        "text": "{{username}}"
                    }
                ],
                "variables": {
                    "username": "user@example.com",
                    "password": "secure_password"
                },
                "tags": ["login", "authentication"]
            }
        }
    )

    def validate_steps(self) -> List[str]:
        """
        Validate this workflow's steps and return a list of problem messages.

        An empty list means the workflow is valid. The validator is imported
        lazily here to avoid a circular import between models and validator.
        """
        from .validator import validate_workflow
        return validate_workflow(self)


class PromptAction(BaseModel):
    """
    Represents a parsed natural language prompt.
    Intermediate format between prompt and workflow.
    """
    intent: str = Field(description="The main intent of the prompt (e.g., 'open_application', 'fill_form')")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities from the prompt")
    confidence: float = Field(description="Confidence score of the parsing (0.0-1.0)")
    suggested_steps: List[ActionStep] = Field(default_factory=list, description="Suggested action steps")

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "intent": "open_browser_and_navigate",
                "entities": {
                    "application": "Chrome",
                    "url": "https://example.com"
                },
                "confidence": 0.95,
                "suggested_steps": []
            }
        }
    )


class ExecutionResult(BaseModel):
    """
    Result of workflow execution.
    Provides detailed feedback for LLM analysis.
    """
    workflow_name: str
    success: bool
    steps_completed: int
    total_steps: int
    execution_time: float = Field(description="Total execution time in seconds")

    errors: List[str] = Field(default_factory=list, description="List of errors encountered")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")

    step_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed results for each step"
    )

    screenshots: List[str] = Field(
        default_factory=list,
        description="Paths to screenshots taken during execution"
    )

    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(extra="forbid")

    def to_llm_summary(self) -> str:
        """Generate a human-readable summary for LLM consumption."""
        status = "✓ Success" if self.success else "✗ Failed"
        summary = f"{status}: Workflow '{self.workflow_name}'\n"
        summary += f"Completed {self.steps_completed}/{self.total_steps} steps in {self.execution_time:.2f}s\n"

        if self.errors:
            summary += "\nErrors:\n" + "\n".join(f"  - {e}" for e in self.errors)

        if self.warnings:
            summary += "\nWarnings:\n" + "\n".join(f"  - {w}" for w in self.warnings)

        return summary
