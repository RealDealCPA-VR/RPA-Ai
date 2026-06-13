"""
AI-Powered RPA System
Automate desktop activities using natural language prompts.
"""

import logging

from .models import Workflow, ActionStep, PromptAction, ExecutionResult
from .automation_engine import AutomationEngine
from .prompt_parser import PromptParser
from .workflow_manager import WorkflowRecorder, WorkflowManager
from .executor import WorkflowExecutor
from .validator import validate_workflow
from .security import scan_workflow, SafetyPolicy, SecurityFinding
from .exceptions import (
    RPAError,
    SafetyError,
    WorkflowValidationError,
    ExecutionError,
)

# A library must not configure the root logger; attach a NullHandler so that
# log records from this package are silently dropped unless the host app
# configures logging itself.
logging.getLogger("ai_rpa_system").addHandler(logging.NullHandler())

__version__ = "1.0.0"
__all__ = [
    "Workflow",
    "ActionStep",
    "PromptAction",
    "ExecutionResult",
    "AutomationEngine",
    "PromptParser",
    "WorkflowRecorder",
    "WorkflowManager",
    "WorkflowExecutor",
    "validate_workflow",
    "scan_workflow",
    "SafetyPolicy",
    "SecurityFinding",
    "RPAError",
    "SafetyError",
    "WorkflowValidationError",
    "ExecutionError",
]
