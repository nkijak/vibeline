# pipeline_framework/monitor.py
import logging
import time
import threading
import queue
import os
from typing import Optional, Dict, List
from werkzeug.serving import make_server, BaseWSGIServer # For running Flask dev server
from flask import Flask

from watchdog.observers import Observer

from .triggers.base import BaseTrigger, TriggerRunInfo
from .triggers.registry import TriggerRegistry
from .triggers.file import FileWatcherTrigger, _PipelineFileSystemEventHandler # Import the handler
from .triggers.webhook import WebhookTrigger, create_webhook_app # Import app factory
from .engine import PipelineExecutionEngine
from .core import Pipeline # Need Pipeline definition

logger = logging.getLogger(__name__)

class TriggerMonitor:
    """
    Monitors registered triggers and initiates pipeline runs.
    Handles polling, file watching, and webhook endpoints.
    """
    def __init__(self,
                 trigger_registry: TriggerRegistry,
                 pipeline_registry: Dict[str, Pipeline], # Pass the pipeline registry
                 poll_interval: int = 10, # Seconds for polling triggers like Cron
                 webhook_host: str = '127.0.0.1',
                 webhook_port: int = 5000):
        self.trigger_registry = trigger_registry
        self.pipeline_registry = pipeline_registry
        self.poll_interval = poll_interval
        self.webhook_host = webhook_host
        self.webhook_port = webhook_port
        self._stop_event = threading.Event()
        self._threads: List[threading.Thread] = []

        # Components for event-based triggers
        self._watchdog_observer: Optional[Observer] = None # type: ignore
        self._watchdog_event_queue: queue.Queue = queue.Queue()
        self._flask_app: Optional['Flask'] = None
        self._flask_server: Optional[BaseWSGIServer] = None


    def _run_pipeline(self, run_info: TriggerRunInfo):
        """Finds the pipeline and runs it using the execution engine."""
        logger.info(f"Monitor: Received request to run pipeline '{run_info.pipeline_name}' from trigger '{run_info.trigger_id}'")
        if run_info.pipeline_name not in self.pipeline_registry:
            logger.error(f"Pipeline '{run_info.pipeline_name}' requested by trigger '{run_info.trigger_id}' not found in registry.")
            return

        pipeline = self.pipeline_registry[run_info.pipeline_name]
        engine = PipelineExecutionEngine(pipeline)

        try:
            # For simplicity, run synchronously in the monitor's thread for now.
            # In production, you'd likely dispatch this to a separate process or thread pool.
            logger.info(f"Executing pipeline '{pipeline.name}' with parameters: {run_info.parameters}")
            context = engine.run(parameters=run_info.parameters) # Pass parameters from trigger
            logger.info(f"Pipeline '{pipeline.name}' run {context.run_id} completed.")
        except Exception as e:
            logger.error(f"Error executing pipeline '{pipeline.name}' triggered by '{run_info.trigger_id}': {e}", exc_info=True)


    def _poll_triggers(self):
        """Periodically checks poll-based triggers (like CronTrigger)."""
        logger.info(f"Starting trigger polling loop (interval: {self.poll_interval}s)")
        while not self._stop_event.is_set():
            try:
                triggers = self.trigger_registry.get_all_triggers()
                # logger.debug(f"Polling {len(triggers)} triggers...")
                for trigger_id, trigger in triggers.items():
                    # Only poll triggers that implement a meaningful check()
                    if isinstance(trigger, (FileWatcherTrigger, WebhookTrigger)):
                        continue # These are handled by events

                    # logger.debug(f"Checking trigger: {trigger_id}")
                    run_info = trigger.check()
                    if run_info:
                        logger.info(f"Trigger '{trigger_id}' condition met via polling.")
                        self._run_pipeline(run_info)

            except Exception as e:
                logger.error(f"Error during trigger polling loop: {e}", exc_info=True)

            # Wait for the next interval or until stop event is set
            self._stop_event.wait(self.poll_interval)
        logger.info("Trigger polling loop stopped.")


    def _process_file_events(self):
        """Processes file events detected by watchdog."""
        logger.info("Starting file event processing loop.")
        file_triggers = [
            t for t in self.trigger_registry.get_all_triggers().values()
            if isinstance(t, FileWatcherTrigger)
        ]
        if not file_triggers:
            logger.info("No FileWatcherTriggers registered. File event loop will not run.")
            return # No need to run if no file triggers

        while not self._stop_event.is_set():
            try:
                # Block waiting for an event from the queue
                event = self._watchdog_event_queue.get(block=True, timeout=1.0) # Timeout allows checking stop_event
            except queue.Empty:
                continue # Timeout reached, loop again to check stop_event

            if event is None: # Sentinel value to stop
                 break

            logger.debug(f"Processing file event: {event.event_type} - {event.src_path}")
            for trigger in file_triggers:
                if trigger.matches_event(event):
                    logger.info(f"File event matched trigger '{trigger.trigger_id}'.")
                    trigger.set_triggered_event(event) # Store event for parameter generation
                    run_info = TriggerRunInfo(
                        pipeline_name=trigger.pipeline_name,
                        parameters=trigger.get_run_parameters(),
                        trigger_id=trigger.trigger_id
                    )
                    self._run_pipeline(run_info)
                # else:
                    # logger.debug(f"Event {event.src_path} did not match trigger '{trigger.trigger_id}'")

        logger.info("File event processing loop stopped.")


    def _start_watchdog(self):
        """Sets up and starts the watchdog observer."""
        file_triggers = [
            t for t in self.trigger_registry.get_all_triggers().values()
            if isinstance(t, FileWatcherTrigger)
        ]
        if not file_triggers:
            logger.info("No FileWatcherTriggers registered. Watchdog observer will not start.")
            return None # No observer needed

        logger.info("Starting Watchdog observer...")
        event_handler = _PipelineFileSystemEventHandler(self._watchdog_event_queue)
        self._watchdog_observer = Observer()

        # Schedule watches for unique paths
        watched_paths = set()
        for trigger in file_triggers:
            # Watchdog needs separate watches for recursive/non-recursive on the same path
            watch_key = (trigger.path, trigger.recursive)
            if trigger.path not in watched_paths:
                 logger.info(f"Watchdog: Scheduling watch for path '{trigger.path}' (Recursive: {trigger.recursive})")
                 self._watchdog_observer.schedule(event_handler, trigger.path, recursive=trigger.recursive)
                 watched_paths.add(trigger.path) # Track paths to avoid duplicate watches if config allows

        if not watched_paths:
             logger.warning("Watchdog observer created but no paths scheduled.")
             self._watchdog_observer = None # Reset if no paths
             return None

        self._watchdog_observer.start()
        logger.info("Watchdog observer started.")
        return self._watchdog_observer


    def _start_webhook_server(self):
        """Sets up and starts the Flask server for webhooks."""
        webhook_triggers_exist = any(
            isinstance(t, WebhookTrigger)
            for t in self.trigger_registry.get_all_triggers().values()
        )
        if not webhook_triggers_exist:
            logger.info("No WebhookTriggers registered. Flask server will not start.")
            return None

        logger.info(f"Starting Flask server for webhooks on {self.webhook_host}:{self.webhook_port}...")
        # Pass the _run_pipeline method as the callback
        self._flask_app = create_webhook_app(self.trigger_registry, self._run_pipeline)

        # Use Werkzeug's make_server for better control over shutdown
        self._flask_server = make_server(self.webhook_host, self.webhook_port, self._flask_app, threaded=True) # Threaded allows handling multiple requests

        # Run the server in a separate thread
        server_thread = threading.Thread(target=self._flask_server.serve_forever, daemon=True)
        server_thread.start()
        self._threads.append(server_thread) # Keep track if needed, though daemon=True helps
        logger.info("Flask server started in a background thread.")
        return self._flask_server


    def start(self):
        """Starts all monitoring components."""
        if self._threads:
             logger.warning("Monitor already seems to be running or was not stopped cleanly.")
             return # Avoid starting multiple times

        logger.info("Starting TriggerMonitor...")
        self._stop_event.clear()

        # Start Watchdog Observer (if needed)
        observer = self._start_watchdog()
        if observer:
            # Start file event processing thread
            file_thread = threading.Thread(target=self._process_file_events, daemon=True)
            file_thread.start()
            self._threads.append(file_thread)

        # Start Webhook Server (if needed)
        self._start_webhook_server() # This starts its own thread via make_server

        # Start polling thread
        poll_thread = threading.Thread(target=self._poll_triggers, daemon=True)
        poll_thread.start()
        self._threads.append(poll_thread)

        logger.info("TriggerMonitor started with all components.")


    def stop(self):
        """Stops all monitoring components gracefully."""
        if not self._threads and not self._watchdog_observer and not self._flask_server:
            logger.info("Monitor is not running.")
            return

        logger.info("Stopping TriggerMonitor...")
        self._stop_event.set()

        # Stop Watchdog
        if self._watchdog_observer:
            logger.info("Stopping Watchdog observer...")
            self._watchdog_observer.stop()
            # Join observer thread AFTER signaling the event processor to stop
            # Put a sentinel value in the queue to unblock the processor thread
            self._watchdog_event_queue.put(None)
            # Find and join the file processor thread
            # (Assuming specific thread management or rely on daemon=True for cleanup)
            # self._watchdog_observer.join() # Wait for observer thread
            logger.info("Watchdog observer stopped.")
            self._watchdog_observer = None


        # Stop Flask Server
        if self._flask_server:
            logger.info("Stopping Flask server...")
            self._flask_server.shutdown() # Graceful shutdown
            logger.info("Flask server stopped.")
            self._flask_server = None
            self._flask_app = None

        # Wait for threads to finish (optional, depends on daemon setting and cleanup needs)
        # logger.info("Waiting for monitor threads to finish...")
        # for thread in self._threads:
        #     if thread.is_alive():
        #          thread.join(timeout=5.0) # Wait with timeout
        #          if thread.is_alive():
        #              logger.warning(f"Thread {thread.name} did not stop gracefully.")

        self._threads = []
        logger.info("TriggerMonitor stopped.")

    def run_forever(self):
        """Starts the monitor and keeps the main thread alive."""
        self.start()
        try:
            while not self._stop_event.is_set():
                time.sleep(1) # Keep main thread alive
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received.")
        finally:
            self.stop()

