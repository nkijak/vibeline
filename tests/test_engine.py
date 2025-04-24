# tests/test_engine.py
import pytest
from pipeline_framework.core import Pipeline
from pipeline_framework.models import Step, PipelineRunContext
from pipeline_framework.engine import PipelineExecutionEngine
from pipeline_framework.errors import CyclicDependencyError, StepExecutionError

# --- Test Setup ---
execution_order_tracker = []

def tracking_step_func(name: str) -> callable:
    """Factory for step functions that track execution order."""
    def step_func(context: PipelineRunContext):
        global execution_order_tracker
        execution_order_tracker.append(name)
        return f"Result from {name}"
    return step_func

@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset the tracker before each test."""
    global execution_order_tracker
    execution_order_tracker = []

# --- Test Cases ---

def test_engine_linear_pipeline():
    p = Pipeline(name="linear")
    step_a = Step(name="a", func=tracking_step_func("a"))
    step_b = Step(name="b", func=tracking_step_func("b"))
    step_c = Step(name="c", func=tracking_step_func("c"))

    p.add_step(step_a)
    p.add_step(step_b, depends_on=["a"])
    p.add_step(step_c, depends_on=["b"])

    engine = PipelineExecutionEngine(p)
    context = engine.run()

    assert execution_order_tracker == ["a", "b", "c"]
    assert context.pipeline_name == "linear"
    assert context.results["a"] == "Result from a"
    assert context.results["b"] == "Result from b"
    assert context.results["c"] == "Result from c"
    assert context.run_id is not None

def test_engine_branching_pipeline():
    p = Pipeline(name="branch")
    step_a = Step(name="a", func=tracking_step_func("a"))
    step_b = Step(name="b", func=tracking_step_func("b"))
    step_c = Step(name="c", func=tracking_step_func("c"))
    step_d = Step(name="d", func=tracking_step_func("d")) # Depends on b and c

    p.add_step(step_a)
    p.add_step(step_b, depends_on=["a"])
    p.add_step(step_c, depends_on=["a"])
    p.add_step(step_d, depends_on=["b", "c"])

    engine = PipelineExecutionEngine(p)
    context = engine.run()

    # Possible valid orders: [a, b, c, d] or [a, c, b, d]
    assert execution_order_tracker[0] == "a"
    assert set(execution_order_tracker[1:3]) == {"b", "c"}
    assert execution_order_tracker[3] == "d"
    assert len(execution_order_tracker) == 4
    assert context.results["d"] == "Result from d"

def test_engine_pipeline_with_no_dependencies():
    p = Pipeline(name="no_deps")
    step_a = Step(name="a", func=tracking_step_func("a"))
    step_b = Step(name="b", func=tracking_step_func("b"))

    p.add_step(step_a)
    p.add_step(step_b)

    engine = PipelineExecutionEngine(p)
    engine.run()

    # Order isn't guaranteed, but both should run
    assert set(execution_order_tracker) == {"a", "b"}
    assert len(execution_order_tracker) == 2

# def test_engine_cyclic_dependency():
#     p = Pipeline(name="cycle")
#     step_a = Step(name="a", func=tracking_step_func("a"))
#     step_b = Step(name="b", func=tracking_step_func("b"))
#     step_c = Step(name="c", func=tracking_step_func("c"))

#     # Add step_b first, so it exists before being referenced as a dependency
#     p.add_step(step_b)
#     p.add_step(step_a, depends_on=["b"])

#     # Introduce a cyclic dependency by making step_b depend on step_a
#     with pytest.raises(CyclicDependencyError):
#         p.add_step(step_c, depends_on=["a"])

def test_engine_step_failure_fail_fast():
    p = Pipeline(name="fail_fast_test")
    step_a = Step(name="a", func=tracking_step_func("a"))
    step_fail = Step(name="fail", func=lambda ctx: 1 / 0) # Will raise ZeroDivisionError
    step_c = Step(name="c", func=tracking_step_func("c")) # Should not run

    p.add_step(step_a)
    p.add_step(step_fail, depends_on=["a"])
    p.add_step(step_c, depends_on=["fail"])

    engine = PipelineExecutionEngine(p)
    with pytest.raises(StepExecutionError) as excinfo:
        engine.run()

    assert execution_order_tracker == ["a"] # Only 'a' should have run
    assert excinfo.value.step_name == "fail"
    assert isinstance(excinfo.value.original_exception, ZeroDivisionError)

def test_engine_run_with_parameters():
    p = Pipeline(name="params_test")
    def check_params_step(context: PipelineRunContext):
        assert context.parameters.get("input_file") == "data.csv"
        execution_order_tracker.append("check")
        return "Params checked"

    step_check = Step(name="check", func=check_params_step)
    p.add_step(step_check)

    engine = PipelineExecutionEngine(p)
    params = {"input_file": "data.csv", "threshold": 10}
    context = engine.run(parameters=params)

    assert execution_order_tracker == ["check"]
    assert context.parameters == params
    assert context.results["check"] == "Params checked"

