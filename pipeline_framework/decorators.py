# pipeline_framework/decorators.py
import functools
import inspect
from typing import Callable, Optional, Any

from .models import Step, PipelineRunContext

# Define a constant for the attribute name to avoid magic strings
_STEP_ATTRIBUTE = "_pipeline_step_obj"

def step(func: Optional[Callable] = None, *, name: Optional[str] = None) -> Callable:
    """
    Decorator to designate a Python function as a pipeline step.

    Args:
        func: The function being decorated (implicitly passed).
        name: Optional explicit name for the step. If None, the function's
              name is used.

    Returns:
        The decorated function, with a `Step` object attached.
    """
    if func is None:
        # Called with arguments like @step(name="custom_name")
        return functools.partial(step, name=name)

    # --- Decorator Logic ---
    step_name = name if name else func.__name__
    if not step_name:
        # Should not happen with normal functions, but good practice
        raise ValueError("Step name cannot be empty. Provide an explicit name or use a named function.")

    # Create the Step instance using the original function
    # The actual execution logic (handling context, persistence) will eventually
    # be managed by the Step.execute method or a wrapper within it.
    # For now, the Step object just holds the reference.
    step_obj = Step(name=step_name, func=func)

    # Attach the Step object to the function itself using a known attribute
    setattr(func, _STEP_ATTRIBUTE, step_obj)

    # functools.wraps preserves the original function's metadata (name, docstring, etc.)
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # When the decorated function is called directly, just execute it.
        # The PipelineExecutionEngine will call step_obj.execute(context) instead.
        # This allows the function to still be used/tested outside the pipeline context.
        return func(*args, **kwargs)

    # Also attach the step object to the wrapper, in case the wrapper is inspected
    setattr(wrapper, _STEP_ATTRIBUTE, step_obj)

    return wrapper

def get_step_from_decorated_func(func: Callable) -> Optional[Step]:
    """
    Retrieves the Step object attached to a function decorated with @step.

    Args:
        func: The decorated function.

    Returns:
        The Step object if found, otherwise None.
    """
    return getattr(func, _STEP_ATTRIBUTE, None)

