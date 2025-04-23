# pipeline_framework/triggers/file.py
import logging
import os
import queue
import time
from typing import Optional, Dict, Any, List, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent, FileCreatedEvent, FileModifiedEvent

from .base import BaseTrigger, TriggerRunInfo

logger = logging.getLogger(__name__)

# --- Watchdog Event Handler ---
# This handler will be shared by the monitor and will put events onto a queue
# that the monitor can process.

class _PipelineFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue: queue.Queue):
        super().__init__()
        self._queue = event_queue

    def on_any_event(self, event: FileSystemEvent):
        # We are interested in file creation and modification
        # Ignore directory events and other event types for now
        if not event.is_directory and isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
            logger.debug(f"Watchdog event received: {event.event_type} - {event.src_path}")
            self._queue.put(event) # Put the raw event onto the queue

# --- FileWatcherTrigger Class ---

class FileWatcherTrigger(BaseTrigger):
    """
    Triggers a pipeline when a file is created or modified in a watched directory.

    Note: This trigger class primarily holds configuration. The actual watching
    is performed by the monitoring service using a shared watchdog Observer.
    """
    def __init__(self, trigger_id: str, pipeline_name: str, path: str, patterns: Optional[List[str]] = None, recursive: bool = False, watch_creation: bool = True, watch_modification: bool = True):
        super().__init__(trigger_id, pipeline_name)
        if not os.path.isdir(path):
             # Could also support watching single files, but directory watching is more common
             raise ValueError(f"Path must be a valid directory: {path}")
        self.path = os.path.abspath(path)
        self.patterns = patterns # Watchdog patterns (e.g., ["*.csv", "*.txt"])
        self.recursive = recursive
        self.watch_creation = watch_creation
        self.watch_modification = watch_modification
        self._triggered_event: Optional[FileSystemEvent] = None # Store the event that triggered the run

        if not watch_creation and not watch_modification:
            raise ValueError("FileWatcherTrigger must watch for creation or modification (or both).")

        logger.info(f"FileWatcherTrigger '{self.trigger_id}' initialized. Path: '{self.path}', Recursive: {self.recursive}, Patterns: {self.patterns}")

    def check(self) -> Optional[TriggerRunInfo]:
        """
        Check is not used for polling this trigger type.
        The monitor service handles events from watchdog directly.
        This method could potentially be used for a manual check if needed,
        but returning None ensures it's not picked up by simple polling loops.
        """
        return None

    def matches_event(self, event: FileSystemEvent) -> bool:
        """Checks if this trigger should react to a given file system event."""
        # Check event type
        if isinstance(event, FileCreatedEvent) and not self.watch_creation:
            return False
        if isinstance(event, FileModifiedEvent) and not self.watch_modification:
            return False
        if not isinstance(event, (FileCreatedEvent, FileModifiedEvent)):
             return False # Only care about creation/modification

        # Check path: event path must be within the trigger's watched directory
        event_path = os.path.abspath(event.src_path)
        if not event_path.startswith(self.path):
            return False

        # If not recursive, check if the event is directly in the watched path
        if not self.recursive and os.path.dirname(event_path) != self.path:
            return False

        # Check patterns (if any) - Watchdog doesn't filter by pattern in the handler itself easily
        # We might need to do basic filename matching here
        if self.patterns:
            import fnmatch
            filename = os.path.basename(event_path)
            if not any(fnmatch.fnmatch(filename, pattern) for pattern in self.patterns):
                return False

        logger.debug(f"Event {event.src_path} matches trigger '{self.trigger_id}' criteria.")
        return True

    def set_triggered_event(self, event: FileSystemEvent):
        """Stores the event that caused the trigger."""
        self._triggered_event = event

    def get_run_parameters(self) -> Dict[str, Any]:
        """Includes information about the file event."""
        params = super().get_run_parameters()
        if self._triggered_event:
            params["event_type"] = self._triggered_event.event_type
            params["src_path"] = self._triggered_event.src_path
            # Clear the event after getting params to avoid reusing old data
            self._triggered_event = None
        return params

    # Optional: setup/teardown could be used by monitor to add/remove watch paths
    # from the observer, but managing a single observer might be simpler.
