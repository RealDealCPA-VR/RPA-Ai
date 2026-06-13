"""
Exception hierarchy for the AI-powered RPA system.

All custom errors derive from :class:`RPAError` so callers can catch the
whole family with a single ``except RPAError``.
"""


class RPAError(Exception):
    """Base class for all errors raised by the AI RPA system."""


class SafetyError(RPAError):
    """Raised when a workflow is blocked by the safety policy."""


class WorkflowValidationError(RPAError):
    """Raised when a workflow fails structural or semantic validation."""


class ExecutionError(RPAError):
    """Raised when a workflow step fails during execution."""
