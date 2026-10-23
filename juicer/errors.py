"""Core exceptions."""


class JuicerError(Exception):
    """Base error for Juicer core operations."""


class ValidationError(JuicerError):
    """Record failed schema/invariant validation."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


class StaleRevisionError(JuicerError):
    """Write rejected because the stored revision moved on."""


class InvalidTransitionError(JuicerError):
    """Status transition not allowed by the state machine."""


class GateBlockedError(JuicerError):
    """Technical or human gate does not allow the operation."""

    def __init__(self, message, gate_status=None):
        self.gate_status = gate_status
        super().__init__(message)


class ScopeViolationError(JuicerError):
    """Execution produced changes outside the task scope."""


class PathConfinementError(JuicerError):
    """Attempted to read/write outside the allowed root."""
