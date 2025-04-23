# pipeline_framework/errors.py
"""Custom exception classes for the pipeline framework."""

class PipelineError(Exception):
    """Base exception for pipeline-related errors."""
    pass

class StepExecutionError(PipelineError):
    """Raised when a step fails during execution."""
    def __init__(self, step_name, original_exception):
        self.step_name = step_name
        self.original_exception = original_exception
        super().__init__(f"Error executing step '{step_name}': {original_exception}")

class CyclicDependencyError(PipelineError):
    """Raised when a cycle is detected in pipeline dependencies."""
    pass
