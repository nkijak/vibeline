# tests/test_core.py
import pytest
from pipeline_framework.core import Pipeline, Step, PipelineRunContext

# Dummy step function for testing
def dummy_step_func(context: PipelineRunContext):
    return f"Executed {context.run_id}"

def test_pipeline_creation():
    p = Pipeline(name="test_pipeline")
    assert p.name == "test_pipeline"
    assert len(p.steps) == 0

def test_add_step():
    p = Pipeline(name="test_add")
    step1 = Step(name="step1", func=dummy_step_func)
    p.add_step(step1)
    assert "step1" in p.steps
    assert p.get_step("step1") == step1
    assert p.dependencies["step1"] == set()

def test_add_step_with_dependency():
    p = Pipeline(name="test_deps")
    step1 = Step(name="step1", func=dummy_step_func)
    step2 = Step(name="step2", func=dummy_step_func)
    p.add_step(step1)
    p.add_step(step2, depends_on=["step1"])
    assert "step2" in p.steps
    assert p.dependencies["step2"] == {"step1"}
    # Check reverse dependency (internal detail, but good for sanity check)
    assert p._reverse_dependencies["step1"] == {"step2"}

def test_add_step_duplicate_name():
    p = Pipeline(name="test_dup")
    step1 = Step(name="step1", func=dummy_step_func)
    p.add_step(step1)
    with pytest.raises(ValueError, match="already exists"):
        p.add_step(step1) # Add same step again

def test_add_step_missing_dependency():
    p = Pipeline(name="test_missing_dep")
    step2 = Step(name="step2", func=dummy_step_func)
    with pytest.raises(ValueError, match="not found in pipeline"):
        p.add_step(step2, depends_on=["non_existent_step"])

def test_get_missing_step():
     p = Pipeline(name="test_get_missing")
     with pytest.raises(ValueError, match="not found in pipeline"):
         p.get_step("non_existent_step")

def test_step_execute_success():
    context = PipelineRunContext(run_id="test_run_123", pipeline_name="test")
    step = Step(name="success_step", func=lambda ctx: {"value": 42})
    result = step.execute(context)
    assert result == {"value": 42}
    assert context.results["success_step"] == {"value": 42}

def test_step_execute_failure():
    context = PipelineRunContext(run_id="test_run_fail", pipeline_name="test")
    def failing_func(ctx):
        raise RuntimeError("Something went wrong")
    step = Step(name="fail_step", func=failing_func)
    with pytest.raises(RuntimeError, match="Something went wrong"):
        step.execute(context)
    # Check result was not added to context on failure
    assert "fail_step" not in context.results

