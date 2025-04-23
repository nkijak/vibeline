# pipeline_framework/cli.py
import click
import logging
import os
import sys
import signal # For graceful shutdown
# typing import might be needed if Dict hint is used elsewhere
# from typing import Dict

# Make sure the project root is potentially in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new pipeline registry module
from .pipeline_registry import load_pipelines_from_module, get_pipeline_registry
# Import trigger utilities
from .triggers import load_triggers_from_module, get_trigger_registry
from .monitor import TriggerMonitor # Import the monitor
from .logging_config import setup_logging, logger # Use the framework logger

# --- Remove Pipeline Discovery from here ---
# PIPELINE_REGISTRY: Dict[str, Pipeline] = {} # REMOVE
# def register_pipeline(pipeline: Pipeline): # REMOVE
# def load_pipelines_from_module(module_name="example_pipelines"): # REMOVE

# --- CLI Commands ---

@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging.")
@click.option('--pipeline-module', default="example_pipelines", help="Module to load pipeline definitions from.")
@click.option('--trigger-module', default="example_triggers", help="Module to load trigger definitions from.")
def cli(verbose, pipeline_module, trigger_module):
    """A simple CLI for the Python Pipeline Framework."""
    log_level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=log_level)
    # Load pipelines *first* using the function from the registry module
    load_pipelines_from_module(pipeline_module)
    # Load triggers
    load_triggers_from_module(trigger_module)

@cli.command()
def list():
    """Lists all registered pipelines."""
    logger.info("Listing available pipelines...")
    # Get registry from the dedicated module
    pipeline_registry = get_pipeline_registry()
    if not pipeline_registry:
        click.echo("No pipelines found or registered.")
        logger.warning("Pipeline registry is empty.")
        return

    for name in pipeline_registry:
        click.echo(f"- {name}")

@cli.command()
@click.argument('pipeline_name')
def run(pipeline_name):
    """Runs a specific pipeline by name."""
    logger.info(f"Attempting to run pipeline: {pipeline_name}")
    # Get registry from the dedicated module
    pipeline_registry = get_pipeline_registry()
    if pipeline_name not in pipeline_registry:
        click.echo(f"Error: Pipeline '{pipeline_name}' not found.")
        logger.error(f"Pipeline '{pipeline_name}' not found in registry.")
        sys.exit(1) # Exit with error code

    pipeline = pipeline_registry[pipeline_name]
    # Need to import PipelineExecutionEngine here if not already imported
    from .engine import PipelineExecutionEngine
    engine = PipelineExecutionEngine(pipeline)

    try:
        click.echo(f"Running pipeline: {pipeline.name}...")
        context = engine.run()
        click.echo(f"Pipeline '{pipeline.name}' finished successfully (Run ID: {context.run_id}).")
    except Exception as e:
        click.echo(f"Pipeline '{pipeline.name}' failed: {e}")
        logger.error(f"Pipeline run failed for '{pipeline_name}'.", exc_info=True)
        sys.exit(1) # Exit with error code


@cli.command()
@click.option('--poll-interval', type=int, default=10, help='Polling interval for triggers (seconds).')
@click.option('--webhook-host', default='127.0.0.1', help='Host for the webhook server.')
@click.option('--webhook-port', type=int, default=5000, help='Port for the webhook server.')
def monitor(poll_interval, webhook_host, webhook_port):
    """Runs the trigger monitor service."""
    logger.info("Initializing Trigger Monitor...")
    trigger_registry = get_trigger_registry()
    # Get pipeline registry from the dedicated module
    pipeline_registry = get_pipeline_registry()

    if not pipeline_registry:
         logger.warning("No pipelines loaded. Monitor might not be able to run triggered pipelines.")

    monitor_instance = TriggerMonitor(
        trigger_registry=trigger_registry,
        pipeline_registry=pipeline_registry, # Pass the obtained registry
        poll_interval=poll_interval,
        webhook_host=webhook_host,
        webhook_port=webhook_port
    )

    # Setup graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}. Shutting down monitor...")
        monitor_instance.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("Starting monitor service. Press Ctrl+C to stop.")
    monitor_instance.run_forever()


if __name__ == '__main__':
    cli()
