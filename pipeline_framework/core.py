# pipeline_framework/core.py
import logging
from typing import Callable, Any, Dict, Optional, Set, List, Union
from dataclasses import dataclass, field

from .decorators import get_step_from_decorated_func
from .models import Step

logger = logging.getLogger(__name__) # Use module-specific logger


class Pipeline:
    """Defines a pipeline as a collection of steps and their dependencies."""
    def __init__(self, name: str):
        self.name = name
        self._steps: Dict[str, Step] = {}
        self._dependencies: Dict[str, Set[str]] = {}
        self._reverse_dependencies: Dict[str, Set[str]] = {}

    def add_step(self, step_or_func: Union[Step, Callable], depends_on: Optional[List[str]] = None):
        """
        Adds a step to the pipeline. Accepts either a Step object or a
        function decorated with @step. Optionally specify dependencies.
        """
        step_obj: Optional[Step] = None

        if isinstance(step_or_func, Step):
            step_obj = step_or_func
        elif callable(step_or_func):
            # Check if it's a decorated function
            step_obj = get_step_from_decorated_func(step_or_func)
            if step_obj is None:
                raise TypeError(
                    f"Callable '{getattr(step_or_func, '__name__', step_or_func)}' "
                    f"is not a Step instance or decorated with @step."
                )
        else:
            raise TypeError(f"Expected Step instance or callable decorated with @step, got {type(step_or_func)}")

        # Now proceed with the validated step_obj
        if step_obj.name in self._steps:
            raise ValueError(f"Step with name '{step_obj.name}' already exists in pipeline '{self.name}'.")

        if depends_on:
            for dep_name in depends_on:
                if dep_name not in self._steps:
                    raise ValueError(f"Dependency '{dep_name}' not found in pipeline '{self.name}'.")

        logger.debug(f"Adding step '{step_obj.name}' to pipeline '{self.name}'")
        self._steps[step_obj.name] = step_obj
        self._dependencies[step_obj.name] = set(depends_on) if depends_on else set()
        self._reverse_dependencies.setdefault(step_obj.name, set())

        if depends_on:
            for dep_name in depends_on:
                # Validation of dependency existence is deferred to the engine
                self._reverse_dependencies.setdefault(dep_name, set()).add(step_obj.name)

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

