# pipeline_framework/logging_config.py
import logging
import sys

def setup_logging(level=logging.INFO):
    """Configures basic logging to standard output."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=level, stream=sys.stdout, format=log_format)

# You might want to get a specific logger for the framework
logger = logging.getLogger("PipelineFramework")

# Call setup when the module is imported (or call it explicitly from your main entry points)
# setup_logging() # Or delay calling this until CLI/Engine initialization
