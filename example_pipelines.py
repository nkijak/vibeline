# example_pipelines.py
import time
import random
from pipeline_framework.core import Pipeline, Step, PipelineRunContext
from pipeline_framework.cli import register_pipeline # Import the registration function
from pipeline_framework.logging_config import logger # Use the framework logger

# --- Define Step Functions ---
# Remember: Step functions should accept PipelineRunContext as an argument

def step_a_func(context: PipelineRunContext) -> dict:
    logger.info(f"Running Step A for run {context.run_id}...")
    time.sleep(1) # Simulate work
    result = {"data": "Data from A", "timestamp": time.time()}
    logger.info("Step A finished.")
    return result

def step_b_func(context: PipelineRunContext) -> str:
    logger.info("Running Step B...")
    # Access results from previous steps if needed (though persistence isn't fully implemented yet)
    # if 'step_a' in context.results:
    #     logger.info(f"Step A result accessed in Step B: {context.results['step_a']}")
    time.sleep(1.5)
    result = "Result from B"
    logger.info("Step B finished.")
    return result

def step_c_func(context: PipelineRunContext) -> int:
    logger.info("Running Step C...")
    time.sleep(0.5)
    result = 123
    logger.info("Step C finished.")
    return result

def failing_step_func(context: PipelineRunContext):
    logger.info("Running Failing Step...")
    time.sleep(0.2)
    raise ValueError("This step is designed to fail!")

# --- Define Steps ---
step_a = Step(name="step_a", func=step_a_func)
step_b = Step(name="step_b", func=step_b_func)
step_c = Step(name="step_c", func=step_c_func)
failing_step = Step(name="failing_step", func=failing_step_func)

# --- Define Pipeline 1: Simple Linear ---
pipeline1 = Pipeline(name="simple_linear_pipeline")
pipeline1.add_step(step_a)
pipeline1.add_step(step_b, depends_on=["step_a"])
pipeline1.add_step(step_c, depends_on=["step_b"])

# --- Define Pipeline 2: With a Branch ---
pipeline2 = Pipeline(name="branching_pipeline")
pipeline2.add_step(step_a)
pipeline2.add_step(step_b, depends_on=["step_a"])
pipeline2.add_step(step_c, depends_on=["step_a"]) # C also depends on A

# --- Define Pipeline 3: Includes a Failing Step ---
pipeline3 = Pipeline(name="failing_pipeline")
pipeline3.add_step(step_a)
pipeline3.add_step(failing_step, depends_on=["step_a"])
pipeline3.add_step(step_b, depends_on=["failing_step"]) # This won't run

# --- Register Pipelines for CLI Discovery ---
register_pipeline(pipeline1)
register_pipeline(pipeline2)
register_pipeline(pipeline3)

logger.info("Example pipelines defined and registered.")
