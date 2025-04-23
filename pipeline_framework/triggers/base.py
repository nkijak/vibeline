# pipeline_framework/triggers/base.py
import abc
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TriggerRunInfo:
    """Information needed to start a pipeline run from a trigger."""
    pipeline_name: str
    parameters: Dict[str, Any]
    trigger_id: str # Identifier for the specific trigger instance

class BaseTrigger(abc.ABC):
    """Abstract base class for all pipeline triggers."""

    def __init__(self, trigger_id: str, pipeline_name: str):
        """
        Args:
            trigger_id: A unique identifier for this specific trigger instance.
            pipeline_name: The name of the pipeline to run when triggered.
        """
        if not trigger_id:
            raise ValueError("trigger_id cannot be empty.")
        if not pipeline_name:
            raise ValueError("pipeline_name cannot be empty.")
        self.trigger_id = trigger_id
        self.pipeline_name = pipeline_name
        logger.debug(f"Initialized trigger '{self.trigger_id}' for pipeline '{self.pipeline_name}'")

    @abc.abstractmethod
    def check(self) -> Optional[TriggerRunInfo]:
        """
        Checks if the trigger condition is met.

        This method is primarily for poll-based triggers. Event-based triggers
        might use a different mechanism within the monitoring service.

        Returns:
            TriggerRunInfo if the trigger condition is met and a run should start,
            otherwise None.
        """
        pass

    def get_run_parameters(self) -> Dict[str, Any]:
        """
        Generates the parameters to be passed to the pipeline run.
        This can be overridden by subclasses to include trigger-specific data.

        Returns:
            A dictionary of parameters for the PipelineRunContext.
        """
        return {"trigger_id": self.trigger_id}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(trigger_id='{self.trigger_id}', pipeline='{self.pipeline_name}')>"

    # Optional methods for event-based triggers if needed for setup/teardown by monitor
    def setup(self, monitor):
        """Optional setup hook called by the monitor."""
        pass

    def teardown(self, monitor):
        """Optional teardown hook called by the monitor."""
        pass

