# example_pipelines.py
import time
import random
from pipeline_framework.core import Pipeline, Step, PipelineRunContext
from pipeline_framework.pipeline_registry import register_pipeline
from pipeline_framework.logging_config import logger
from pipeline_framework.decorators import step


# --- Define Step Functions ---
# Remember: Step functions should accept PipelineRunContext as an argument

@step
def step_a(context: PipelineRunContext) -> dict:
    logger.info(f"Running Step A for run {context.run_id}...")
    time.sleep(1) # Simulate work
    result = {"data": "Data from A", "timestamp": time.time()}
    logger.info("Step A finished.")
    return result

# Example with an explicit name
@step(name="step_b_processor")
def step_b(context: PipelineRunContext) -> str:
    """This is Step B. It depends on Step A."""
    logger.info("Running Step B...")
    # Access results (basic example, persistence in Epic 5 will improve this)
    if 'step_a' in context.results:
         logger.info(f"Step A result accessed in Step B: {context.results['step_a']}")
    else:
         logger.warning("Step A result not found in context for Step B.")
    time.sleep(0.8)
    result = "Result from B"
    logger.info("Step B finished.")
    return result


@step
def step_c(context: PipelineRunContext) -> int:
    """This is Step C. It also depends on Step A in branching_pipeline."""
    logger.info("Running Step C...")
    time.sleep(0.3)
    result = 123
    logger.info("Step C finished.")
    return result

@step
def failing_step(context: PipelineRunContext):
    """This step is designed to fail."""
    logger.info("Running Failing Step...")
    time.sleep(0.1)
    raise ValueError("This step is designed to fail!")

# --- Define Steps ---
# step_a = Step(name="step_a", func=step_a_func)
# step_b = Step(name="step_b", func=step_b_func)
# step_c = Step(name="step_c", func=step_c_func)
# failing_step = Step(name="failing_step", func=failing_step_func)
# Pipeline 1: Simple Linear
pipeline1 = Pipeline(name="simple_linear_pipeline")
pipeline1.add_step(step_a) # Add decorated function directly
pipeline1.add_step(step_b, depends_on=[step_a.__name__]) # Depend on function name (or explicit step name)
pipeline1.add_step(step_c, depends_on=[step_b.name]) # Can also use .name if step has explicit name like step_b

# Pipeline 2: With a Branch
pipeline2 = Pipeline(name="branching_pipeline")
pipeline2.add_step(step_a)
pipeline2.add_step(step_b, depends_on=[step_a.__name__]) # step_b has explicit name "step_b_processor"
pipeline2.add_step(step_c, depends_on=[step_a.__name__]) # step_c uses function name "step_c"

# Pipeline 3: Includes a Failing Step
pipeline3 = Pipeline(name="failing_pipeline")
pipeline3.add_step(step_a)
pipeline3.add_step(failing_step, depends_on=[step_a.__name__])
# Use the correct name for dependency - step_b's actual step name is "step_b_processor"
pipeline3.add_step(step_b, depends_on=[failing_step.__name__]) # This won't run

# --- Register Pipelines ---
register_pipeline(pipeline1)
register_pipeline(pipeline2)
register_pipeline(pipeline3)

logger.info("Example pipelines defined using @step decorator and registered.")