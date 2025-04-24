# pipeline_framework/engine.py
import logging
import time
import uuid
from typing import List, Dict, Set, Optional # Add Optional and Dict here

import networkx as nx # Using networkx for robust topological sort

from .core import Pipeline
from .models import PipelineRunContext, Step
from .errors import CyclicDependencyError, StepExecutionError
from .logging_config import setup_logging # Import setup function

logger = logging.getLogger(__name__)

class PipelineExecutionEngine:
    """Executes the steps of a pipeline in the correct order."""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        # Consider initializing logging here if not done globally
        # setup_logging()

    def _build_dependency_graph(self) -> nx.DiGraph:
        """Builds a directed graph from pipeline dependencies."""
        graph = nx.DiGraph()
        for step_name in self.pipeline.steps:
            graph.add_node(step_name)
        for step_name, dependencies in self.pipeline.dependencies.items():
            for dep_name in dependencies:
                if dep_name not in self.pipeline.steps:
                     # This check should ideally be in Pipeline.add_step
                     logger.warning(f"Dependency '{dep_name}' for step '{step_name}' not found in pipeline steps. Ignoring.")
                     continue
                graph.add_edge(dep_name, step_name) # Edge from dependency to dependent
        return graph

    def _get_execution_order(self) -> List[str]:
        """Determines the execution order of steps using topological sort."""
        graph = self._build_dependency_graph()
        if not nx.is_directed_acyclic_graph(graph):
            cycles = list(nx.simple_cycles(graph))
            raise CyclicDependencyError(f"Pipeline '{self.pipeline.name}' contains cycles: {cycles}")

        # networkx topological_sort returns an iterator
        return list(nx.topological_sort(graph))

    def run(self, run_id: Optional[str] = None, parameters: Optional[Dict] = None) -> PipelineRunContext:
        """
        Runs the entire pipeline.

        Args:
            run_id: A unique identifier for this run. Auto-generated if None.
            parameters: Optional dictionary of parameters for the run (e.g., from triggers).

        Returns:
            The PipelineRunContext containing run information and results.

        Raises:
            CyclicDependencyError: If the pipeline has dependency cycles.
            StepExecutionError: If a step fails (using fail-fast strategy).
        """
        if run_id is None:
            run_id = f"run_{uuid.uuid4().hex[:8]}"

        context = PipelineRunContext(
            run_id=run_id,
            pipeline_name=self.pipeline.name,
            parameters=parameters or {}
        )

        logger.info(f"Starting pipeline run: {self.pipeline.name} (Run ID: {run_id})")
        start_time = time.time()

        try:
            execution_order = self._get_execution_order()
            logger.info(f"Execution order: {execution_order}")

            for step_name in execution_order:
                step = self.pipeline.get_step(step_name)
                step_start_time = time.time()
                try:
                    # Execute step (basic fail-fast)
                    step.execute(context) # Step execution handles its own logging now
                    step_end_time = time.time()
                    logger.debug(f"Step '{step_name}' duration: {step_end_time - step_start_time:.4f} seconds")
                except Exception as e:
                    # Catch exception from step.execute (which might be StepExecutionError or original)
                    end_time = time.time()
                    logger.error(
                        f"Pipeline run '{context.run_id}' failed at step '{step_name}'. "
                        f"Total duration: {end_time - start_time:.4f} seconds."
                    )
                    # Wrap in StepExecutionError if it's not already one
                    if not isinstance(e, StepExecutionError):
                         raise StepExecutionError(step_name, e) from e
                    else:
                         raise # Re-raise the StepExecutionError

            end_time = time.time()
            logger.info(
                f"Pipeline run '{context.run_id}' completed successfully. "
                f"Total duration: {end_time - start_time:.4f} seconds."
            )
            return context

        except CyclicDependencyError as e:
            logger.error(f"Pipeline '{self.pipeline.name}' cannot run due to dependency error: {e}")
            raise # Re-raise the specific error
        except Exception as e:
            # Catch any other unexpected errors during engine setup/run
            logger.error(f"An unexpected error occurred during pipeline run '{context.run_id}': {e}", exc_info=True)
            raise # Re-raise

