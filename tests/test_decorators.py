# tests/test_decorators.py
import pytest

from pipeline_framework.decorators import step, get_step_from_decorated_func
from pipeline_framework.core import Pipeline
from pipeline_framework.models import Step, PipelineRunContext
from pipeline_framework.engine import PipelineExecutionEngine

# --- Test Functions ---

@step
def simple_decorated_step(context: PipelineRunContext):
    """A simple decorated step."""
    return f"Simple step executed for {context.run_id}"

@step(name="custom_name_step")
def named_decorated_step(context: PipelineRunContext):
    """A decorated step with a custom name."""
    return "Named step executed"

def not_decorated_func():
    """This function is not decorated."""
    return "Not decorated"

# --- Test Cases ---

def test_decorator_attaches_step_object():
    """Verify that @step attaches a Step object."""
    step_obj = get_step_from_decorated_func(simple_decorated_step)
    assert step_obj is not None
    assert isinstance(step_obj, Step)

def test_decorator_uses_function_name_as_default():
    """Verify the default step name is the function name."""
    step_obj = get_step_from_decorated_func(simple_decorated_step)
    assert step_obj.name == "simple_decorated_step"
    # Check that the original function is stored
    assert step_obj.func == simple_decorated_step.__wrapped__ # Access original via __wrapped__

def test_decorator_uses_explicit_name():
    """Verify the step name uses the name argument if provided."""
    step_obj = get_step_from_decorated_func(named_decorated_step)
    assert step_obj is not None
    assert step_obj.name == "custom_name_step"
    assert step_obj.func == named_decorated_step.__wrapped__

def test_get_step_from_undecorated_function():
    """Verify None is returned for non-decorated functions."""
    assert get_step_from_decorated_func(not_decorated_func) is None

def test_add_decorated_step_to_pipeline():
    """Test adding a decorated function directly to a Pipeline."""
    p = Pipeline("test_add_decorated")
    p.add_step(simple_decorated_step) # Add decorated function

    assert "simple_decorated_step" in p.steps
    retrieved_step = p.get_step("simple_decorated_step")
    assert isinstance(retrieved_step, Step)
    assert retrieved_step.name == "simple_decorated_step"
    assert retrieved_step.func == simple_decorated_step.__wrapped__

def test_add_decorated_step_with_custom_name_to_pipeline():
    """Test adding a decorated function with a custom name."""
    p = Pipeline("test_add_custom_name")
    p.add_step(named_decorated_step) # Add decorated function

    assert "custom_name_step" in p.steps
    retrieved_step = p.get_step("custom_name_step")
    assert retrieved_step.name == "custom_name_step"

def test_add_undecorated_function_raises_error():
    """Test that adding a non-decorated function raises TypeError."""
    p = Pipeline("test_add_undecorated")
    with pytest.raises(TypeError, match="is not a Step instance or decorated with @step"):
        p.add_step(not_decorated_func)

def test_add_non_callable_raises_error():
    """Test that adding non-step, non-callable raises TypeError."""
    p = Pipeline("test_add_non_callable")
    with pytest.raises(TypeError, match="Expected Step instance or callable decorated with @step"):
        p.add_step(123)

def test_execute_pipeline_with_decorated_steps():
    """Integration test: Execute a pipeline defined with decorators."""
    @step
    def step1(ctx):
        ctx.results["step1_marker"] = "A"
        return "one"

    @step(name="step_two")
    def step2(ctx):
        assert ctx.results.get("step1_marker") == "A" # Check context propagation
        return "two"

    p = Pipeline("decorated_exec_test")
    p.add_step(step1)
    p.add_step(step2, depends_on=[step1.__name__]) # Depend on "step1"

    engine = PipelineExecutionEngine(p)
    context = engine.run(run_id="deco-run-1")

    assert context.results["step1"] == "one"
    assert context.results["step_two"] == "two" # Use the actual step name for result key

