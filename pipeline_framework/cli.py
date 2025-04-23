# pipeline_framework/cli.py
import click
import logging
import importlib
import os
import sys
from typing import Dict

# Make sure the project root is potentially in the path if running directly
# This might be needed if 'example_pipelines.py' is not installed as part of the package
# For robust deployment, rely on package installation and entry points
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from .core import Pipeline
from .engine import PipelineExecutionEngine
from .logging_config import setup_logging, logger # Use the framework logger

# --- Pipeline Discovery (Simple Version) ---
# A simple mechanism to find pipeline definitions.
# In a real app, this could use entry points, configuration files, or module scanning.
PIPELINE_REGISTRY: Dict[str, Pipeline] = {}

def register_pipeline(pipeline: Pipeline):
    """Registers a pipeline instance for discovery by the CLI."""
    if pipeline.name in PIPELINE_REGISTRY:
        logger.warning(f"Pipeline with name '{pipeline.name}' is already registered. Overwriting.")
    logger.debug(f"Registering pipeline: {pipeline.name}")
    PIPELINE_REGISTRY[pipeline.name] = pipeline

def load_pipelines_from_module(module_name="example_pipelines"):
    """Loads pipelines by importing a specific module."""
    try:
        logger.info(f"Attempting to load pipelines from module: {module_name}")
        importlib.import_module(module_name)
        logger.info(f"Successfully loaded pipelines from {module_name}. Found: {list(PIPELINE_REGISTRY.keys())}")
    except ImportError:
        logger.warning(f"Could not import module '{module_name}' to load pipelines.")
    except Exception as e:
        logger.error(f"Error loading pipelines from {module_name}: {e}", exc_info=True)

# --- CLI Commands ---

@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging.")
@click.option('--pipeline-module', default="example_pipelines", help="Module to load pipeline definitions from.")
def cli(verbose, pipeline_module):
    """A simple CLI for the Python Pipeline Framework."""
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)
    # Load pipelines *after* logging is set up
    load_pipelines_from_module(pipeline_module)

@cli.command()
def list():
    """Lists all registered pipelines."""
    logger.info("Listing available pipelines...")
    if not PIPELINE_REGISTRY:
        click.echo("No pipelines found or registered.")
        logger.warning("Pipeline registry is empty.")
        return

    for name in PIPELINE_REGISTRY:
        click.echo(f"- {name}")

@cli.command()
@click.argument('pipeline_name')
def run(pipeline_name):
    """Runs a specific pipeline by name."""
    logger.info(f"Attempting to run pipeline: {pipeline_name}")
    if pipeline_name not in PIPELINE_REGISTRY:
        click.echo(f"Error: Pipeline '{pipeline_name}' not found.")
        logger.error(f"Pipeline '{pipeline_name}' not found in registry.")
        sys.exit(1) # Exit with error code

    pipeline = PIPELINE_REGISTRY[pipeline_name]
    engine = PipelineExecutionEngine(pipeline)

    try:
        click.echo(f"Running pipeline: {pipeline.name}...")
        context = engine.run()
        click.echo(f"Pipeline '{pipeline.name}' finished successfully (Run ID: {context.run_id}).")
        # Optionally print results if needed
        # click.echo(f"Results: {context.results}")
    except Exception as e:
        click.echo(f"Pipeline '{pipeline.name}' failed: {e}")
        logger.error(f"Pipeline run failed for '{pipeline_name}'.", exc_info=True)
        sys.exit(1) # Exit with error code

if __name__ == '__main__':
    cli()
