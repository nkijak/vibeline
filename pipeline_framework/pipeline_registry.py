# pipeline_framework/pipeline_registry.py
import logging
import importlib
from typing import Dict

# Assuming Pipeline class is defined in core, adjust if necessary
from .core import Pipeline

logger = logging.getLogger(__name__)

# Central registry for pipelines
PIPELINE_REGISTRY: Dict[str, Pipeline] = {}

def register_pipeline(pipeline: Pipeline):
    """Registers a pipeline instance to the global pipeline registry."""
    if pipeline.name in PIPELINE_REGISTRY:
        logger.warning(f"Pipeline with name '{pipeline.name}' is already registered. Overwriting.")
    logger.debug(f"Registering pipeline: {pipeline.name}")
    PIPELINE_REGISTRY[pipeline.name] = pipeline

def get_pipeline_registry() -> Dict[str, Pipeline]:
    """Returns the global pipeline registry."""
    return PIPELINE_REGISTRY

def load_pipelines_from_module(module_name="example_pipelines"):
    """
    Loads pipelines by importing a specific module.
    Assumes pipelines are registered using `register_pipeline` upon import.
    """
    try:
        logger.info(f"Attempting to load pipelines from module: {module_name}")
        importlib.import_module(module_name)
        count = len(get_pipeline_registry())
        logger.info(f"Successfully processed module {module_name}. Total pipelines registered: {count}")
    except ImportError:
        logger.warning(f"Could not import module '{module_name}' to load pipelines. No pipelines loaded from this module.")
    except Exception as e:
        logger.error(f"Error loading pipelines from {module_name}: {e}", exc_info=True)

