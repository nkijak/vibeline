# pipeline_framework/models.py
import logging
from typing import Callable, Any, Dict
from dataclasses import dataclass, field

# Keep logger definition if Step methods use it, otherwise remove
# logger = logging.getLogger(__name__)
# Or import the specific logger if needed later

@dataclass
class PipelineRunContext:
    """Holds context information for a single pipeline run."""
    run_id: str
    pipeline_name: str
    results: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Step:
    """Represents a single step in a pipeline."""
    name: str
    func: Callable[..., Any]

    def execute(self, context: PipelineRunContext) -> Any:
        """Executes the step's function."""
        # Get logger within the method or ensure it's configured globally
        logger = logging.getLogger(__name__)
        logger.info(f"Executing step: {self.name}")
        try:
            # Assuming function expects context as the first argument for now
            result = self.func(context)
            logger.info(f"Step '{self.name}' completed successfully.")
            context.results[self.name] = result
            return result
        except Exception as e:
            logger.error(f"Step '{self.name}' failed: {e}", exc_info=True)
            from .errors import StepExecutionError
            raise StepExecutionError(self.name, e) from e

