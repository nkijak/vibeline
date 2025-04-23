# example_triggers.py
import os
import logging
from pipeline_framework.triggers import (
    register_trigger,
    CronTrigger,
    FileWatcherTrigger,
    WebhookTrigger
)

logger = logging.getLogger(__name__)

# --- Define Trigger Instances ---

# Example 1: Run 'simple_linear_pipeline' every minute
try:
    cron_trigger_1 = CronTrigger(
        trigger_id="cron_minute",
        pipeline_name="simple_linear_pipeline", # Assumes this pipeline exists
        cron_expression="* * * * *" # Every minute
    )
    register_trigger(cron_trigger_1)
except ValueError as e:
    logger.error(f"Failed to create cron_trigger_1: {e}")


# Example 2: Run 'branching_pipeline' when a CSV file is created/modified
# Create a directory to watch if it doesn't exist
watch_dir = os.path.abspath("./watched_files")
os.makedirs(watch_dir, exist_ok=True)
logger.info(f"Example trigger will watch for files in: {watch_dir}")

try:
    file_trigger_1 = FileWatcherTrigger(
        trigger_id="watch_csv_files",
        pipeline_name="branching_pipeline", # Assumes this pipeline exists
        path=watch_dir,
        patterns=["*.csv"],
        recursive=False,
        watch_creation=True,
        watch_modification=True
    )
    register_trigger(file_trigger_1)
except ValueError as e:
    logger.error(f"Failed to create file_trigger_1: {e}")


# Example 3: Run 'failing_pipeline' via a webhook
try:
    webhook_trigger_1 = WebhookTrigger(
        trigger_id="webhook_fail_test",
        pipeline_name="failing_pipeline", # Assumes this pipeline exists
        endpoint="/hooks/trigger-fail",
        methods=["POST", "GET"]
    )
    register_trigger(webhook_trigger_1)
except ValueError as e:
    logger.error(f"Failed to create webhook_trigger_1: {e}")


logger.info("Example triggers defined and registered.")

