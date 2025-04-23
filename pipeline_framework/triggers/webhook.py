# pipeline_framework/triggers/webhook.py
import logging
from typing import Optional, Dict, Any, List
from flask import Flask, request, jsonify # Using Flask for the web server part

from .base import BaseTrigger, TriggerRunInfo

logger = logging.getLogger(__name__)

# --- WebhookTrigger Class ---

class WebhookTrigger(BaseTrigger):
    """
    Triggers a pipeline when an HTTP request is received on a specific endpoint.

    Note: This trigger class primarily holds configuration. The actual web server
    is managed by the monitoring service.
    """
    def __init__(self, trigger_id: str, pipeline_name: str, endpoint: str, methods: Optional[List[str]] = None):
        super().__init__(trigger_id, pipeline_name)
        if not endpoint.startswith('/'):
            raise ValueError("Webhook endpoint must start with '/'")
        self.endpoint = endpoint
        self.methods = methods or ['POST'] # Default to POST
        self._triggered_request_data: Optional[Dict[str, Any]] = None # Store data from the triggering request

        logger.info(f"WebhookTrigger '{self.trigger_id}' initialized. Endpoint: '{self.endpoint}', Methods: {self.methods}")

    def check(self) -> Optional[TriggerRunInfo]:
        """
        Check is not used for polling this trigger type.
        The monitor service handles requests directly via the Flask app.
        """
        return None

    def set_triggered_request(self, flask_request):
        """Stores relevant data from the Flask request object."""
        self._triggered_request_data = {
            "method": flask_request.method,
            "endpoint": flask_request.path,
            "args": flask_request.args.to_dict(),
            "headers": dict(flask_request.headers),
            "data": flask_request.get_data(as_text=True), # Raw body
            "json_data": flask_request.get_json(silent=True) # Parsed JSON if applicable
        }
        logger.debug(f"Stored request data for trigger '{self.trigger_id}'")


    def get_run_parameters(self) -> Dict[str, Any]:
        """Includes information from the HTTP request."""
        params = super().get_run_parameters()
        if self._triggered_request_data:
            params.update(self._triggered_request_data)
             # Clear the data after getting params
            self._triggered_request_data = None
        return params

# --- Flask App Setup (to be used by the monitor) ---

def create_webhook_app(trigger_registry, pipeline_runner_func) -> Flask:
    """
    Creates a Flask app with dynamic routes based on registered WebhookTriggers.

    Args:
        trigger_registry: The TriggerRegistry instance containing webhook triggers.
        pipeline_runner_func: A callable that takes TriggerRunInfo and runs the pipeline.
                               Example: monitor_instance.run_pipeline_from_trigger
    """
    app = Flask(f"pipeline_framework_webhooks_{id(trigger_registry)}") # Unique name
    app.config['SECRET_KEY'] = os.urandom(24) # Basic secret key
    logger.info("Creating Flask app for webhook triggers.")

    webhook_triggers = {
        trigger.endpoint: trigger
        for trigger in trigger_registry.get_all_triggers().values()
        if isinstance(trigger, WebhookTrigger)
    }
    logger.info(f"Found {len(webhook_triggers)} webhook triggers to configure routes for.")

    # Dynamically add routes based on registered triggers
    for endpoint, trigger in webhook_triggers.items():
        # Use a closure to capture the correct trigger instance for each route
        def create_view_func(current_trigger: WebhookTrigger):
            def view_func(**kwargs): # Use kwargs to capture path parameters if any
                logger.info(f"Webhook request received for endpoint: {current_trigger.endpoint} (Trigger ID: {current_trigger.trigger_id})")
                # Store request data in the trigger instance
                current_trigger.set_triggered_request(request)
                # Prepare run info
                run_info = TriggerRunInfo(
                    pipeline_name=current_trigger.pipeline_name,
                    parameters=current_trigger.get_run_parameters(), # This will now include request data
                    trigger_id=current_trigger.trigger_id
                )
                try:
                    # Call the provided function to actually run the pipeline
                    # This might run synchronously or asynchronously depending on the monitor's implementation
                    pipeline_runner_func(run_info)
                    return jsonify({"status": "success", "message": f"Pipeline '{run_info.pipeline_name}' triggered."}), 202 # Accepted
                except Exception as e:
                    logger.error(f"Error triggering pipeline '{run_info.pipeline_name}' from webhook '{current_trigger.trigger_id}': {e}", exc_info=True)
                    return jsonify({"status": "error", "message": "Failed to trigger pipeline."}), 500
            # Set a unique endpoint name for Flask based on the trigger ID
            view_func.__name__ = f"webhook_{current_trigger.trigger_id}"
            return view_func

        # Add the rule to the Flask app
        app.add_url_rule(
            trigger.endpoint,
            endpoint=f"webhook_{trigger.trigger_id}", # Unique endpoint name
            view_func=create_view_func(trigger),
            methods=trigger.methods
        )
        logger.debug(f"Added route: {trigger.endpoint} Methods: {trigger.methods} for trigger '{trigger.trigger_id}'")

    @app.route("/_health")
    def health_check():
        return jsonify({"status": "ok"})

    return app
