# pipeline_framework/core.py
import logging
from typing import Callable, Any, Dict, Optional, Set, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__) # Use module-specific logger

# Simple context for now, will be expanded later (e.g., for persistence)
@dataclass
class PipelineRunContext:
    """Holds context information for a single pipeline run."""
    run_id: str
    pipeline_name: str
    # Later: add storage for step results, parameters, etc.
    results: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict) # For trigger payloads etc.

@dataclass
class Step:
    """Represents a single step in a pipeline."""
    name: str
    func: Callable[[PipelineRunContext], Any] # Step function takes context, returns result
    # Later: add config like retry logic, conditional execution flags

    def execute(self, context: PipelineRunContext) -> Any:
        """Executes the step's function."""
        logger.info(f"Executing step: {self.name}")
        try:
            result = self.func(context)
            logger.info(f"Step '{self.name}' completed successfully.")
            # Store result in context (basic version for now)
            context.results[self.name] = result
            return result
        except Exception as e:
            logger.error(f"Step '{self.name}' failed: {e}", exc_info=True)
            # Re-raise as a specific framework error if desired (Subtask 1.6)
            # from .errors import StepExecutionError
            # raise StepExecutionError(self.name, e) from e
            raise # Re-raise the original exception for now (simple fail fast)

class Pipeline:
    """Defines a pipeline as a collection of steps and their dependencies."""
    def __init__(self, name: str):
        self.name = name
        self._steps: Dict[str, Step] = {}
        # Adjacency list representation of the DAG: step_name -> set of dependent step names
        self._dependencies: Dict[str, Set[str]] = {}
        # Reverse dependencies: step_name -> set of steps that depend on it
        self._reverse_dependencies: Dict[str, Set[str]] = {}

    def add_step(self, step: Step, depends_on: Optional[List[str]] = None):
        """Adds a step to the pipeline, optionally specifying dependencies."""
        if step.name in self._steps:
            raise ValueError(f"Step with name '{step.name}' already exists in pipeline '{self.name}'.")

        logger.debug(f"Adding step '{step.name}' to pipeline '{self.name}'")
        self._steps[step.name] = step
        self._dependencies[step.name] = set(depends_on) if depends_on else set()
        self._reverse_dependencies.setdefault(step.name, set()) # Ensure entry exists

        # Validate dependencies and update reverse dependencies
        if depends_on:
            for dep_name in depends_on:
                if dep_name not in self._steps:
                    # Allow defining dependencies before the step is added?
                    # For now, require dependencies to exist when adding dependents.
                     raise ValueError(f"Dependency '{dep_name}' for step '{step.name}' not found in pipeline.")
                self._reverse_dependencies.setdefault(dep_name, set()).add(step.name)

    def get_step(self, name: str) -> Step:
        """Retrieves a step by its name."""
        if name not in self._steps:
            raise ValueError(f"Step '{name}' not found in pipeline '{self.name}'.")
        return self._steps[name]

    @property
    def steps(self) -> Dict[str, Step]:
        """Returns the dictionary of steps in the pipeline."""
        return self._steps

    @property
    def dependencies(self) -> Dict[str, Set[str]]:
        """Returns the dependency graph."""
        return self._dependencies

    def __repr__(self) -> str:
        return f"<Pipeline(name='{self.name}', steps={len(self._steps)})>"

