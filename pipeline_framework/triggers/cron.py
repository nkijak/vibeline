# pipeline_framework/triggers/cron.py
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from croniter import croniter

from .base import BaseTrigger, TriggerRunInfo

logger = logging.getLogger(__name__)

class CronTrigger(BaseTrigger):
    """Triggers a pipeline based on a cron schedule."""

    def __init__(self, trigger_id: str, pipeline_name: str, cron_expression: str):
        super().__init__(trigger_id, pipeline_name)
        if not croniter.is_valid(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        self.cron_expression = cron_expression
        # Initialize last check time to ensure the first run happens correctly
        # We use UTC for internal consistency
        self._iter = croniter(self.cron_expression, datetime.now(timezone.utc))
        # Get the *previous* scheduled time to avoid triggering immediately on startup
        # if the current time is exactly the next scheduled time.
        self.last_scheduled_fire_time = self._iter.get_prev(datetime)
        logger.info(f"CronTrigger '{self.trigger_id}' initialized. Schedule: '{self.cron_expression}'. Last fire time set to: {self.last_scheduled_fire_time}")


    def check(self) -> Optional[TriggerRunInfo]:
        """Checks if the next cron time has passed since the last check."""
        now_utc = datetime.now(timezone.utc)
        # Reset iterator to the last known fire time to find the *next* one after that
        iter_from_last = croniter(self.cron_expression, self.last_scheduled_fire_time)
        next_fire_time = iter_from_last.get_next(datetime)

        if now_utc >= next_fire_time:
            logger.info(f"CronTrigger '{self.trigger_id}' condition met. Current time {now_utc} >= Next fire time {next_fire_time}")
            # Update last fire time *before* returning, to prevent rapid re-triggering
            self.last_scheduled_fire_time = next_fire_time
            return TriggerRunInfo(
                pipeline_name=self.pipeline_name,
                parameters=self.get_run_parameters(fire_time=next_fire_time),
                trigger_id=self.trigger_id
            )
        # else:
            # logger.debug(f"CronTrigger '{self.trigger_id}' condition not met. Current time {now_utc} < Next fire time {next_fire_time}")

        return None

    def get_run_parameters(self, fire_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Includes the scheduled fire time in the parameters."""
        params = super().get_run_parameters()
        if fire_time:
            params["scheduled_fire_time_utc"] = fire_time.isoformat()
        return params

