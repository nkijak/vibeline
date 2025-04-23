# pipeline_framework/triggers/registry.py
import logging
import importlib
from typing import Dict, Type

from .base import BaseTrigger

logger = logging.getLogger(__name__)

class TriggerRegistry:
    """Holds registered trigger instances."""
    def __init__(self):
        self._triggers: Dict[str, BaseTrigger] = {} # trigger_id -> Trigger instance

    def register(self, trigger: BaseTrigger):
        """Registers a trigger instance."""
        if trigger.trigger_id in self._triggers:
            logger.warning(f"Trigger with ID '{trigger.trigger_id}' already registered. Overwriting.")
        logger.info(f"Registering trigger: {trigger.trigger_id} ({trigger.__class__.__name__}) for pipeline '{trigger.pipeline_name}'")
        self._triggers[trigger.trigger_id] = trigger

    def get_trigger(self, trigger_id: str) -> BaseTrigger:
        """Gets a trigger by its ID."""
        if trigger_id not in self._triggers:
            raise KeyError(f"Trigger with ID '{trigger_id}' not found.")
        return self._triggers[trigger_id]

    def get_all_triggers(self) -> Dict[str, BaseTrigger]:
        """Returns all registered triggers."""
        return self._triggers.copy()

    def clear(self):
        """Clears all registered triggers (useful for testing)."""
        self._triggers = {}

# Global registry instance (simple approach)
_global_trigger_registry = TriggerRegistry()

def register_trigger(trigger: BaseTrigger):
    """Registers a trigger instance to the global registry."""
    _global_trigger_registry.register(trigger)

def get_trigger_registry() -> TriggerRegistry:
    """Returns the global trigger registry instance."""
    return _global_trigger_registry

def load_triggers_from_module(module_name: str = "example_triggers"):
    """
    Loads triggers by importing a specific module.
    Assumes triggers are registered using `register_trigger` upon import.
    """
    try:
        logger.info(f"Attempting to load triggers from module: {module_name}")
        importlib.import_module(module_name)
        count = len(get_trigger_registry().get_all_triggers())
        logger.info(f"Successfully processed module {module_name}. Total triggers registered: {count}")
    except ImportError:
        logger.warning(f"Could not import module '{module_name}' to load triggers. No triggers loaded from this module.")
    except Exception as e:
        logger.error(f"Error loading triggers from {module_name}: {e}", exc_info=True)

