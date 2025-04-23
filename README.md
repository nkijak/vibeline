# Python Pipeline Framework

<!-- Add your logo here! Replace the src attribute -->
<p align="center">
  <img src="logo.jpg" alt="Project Logo" width="200"/>
</p>

## Overview

This project provides a flexible and extensible framework for defining, executing, and monitoring data pipelines in Python. It allows developers to structure complex workflows as a series of dependent steps (forming a Directed Acyclic Graph - DAG) and trigger these pipelines based on various events like schedules, file changes, or webhooks.

## Core Features

*   **Pipeline Definition:** Define pipelines as collections of steps with explicit dependencies using simple Python objects.
*   **Execution Engine:** Automatically resolves step dependencies and executes them in the correct order using topological sorting.
*   **Extensible Triggers:** Initiate pipelines based on:
    *   **Cron Schedules:** Run pipelines at specific times or intervals.
    *   **File Events:** Trigger pipelines when files are created or modified in watched directories.
    *   **Webhooks:** Start pipelines via incoming HTTP requests.
    *   *(Custom triggers can be added by inheriting from `BaseTrigger`)*.
*   **Monitoring Service:** A central service monitors active triggers and launches pipeline runs.
*   **Command-Line Interface (CLI):** Interact with the framework to list defined pipelines, run them manually, and start the trigger monitor.
*   **Basic Logging:** Provides essential logging for pipeline and step execution status.

## Getting Started

### Prerequisites

*   Python >= 3.11
*   uv (for environment and package management)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd pipeline # Or your project's root directory name
    ```

2.  **Create a virtual environment:**
    ```bash
    uv venv
    ```

3.  **Install dependencies:**
    ```bash
    uv sync --dev
    ```

### Usage

1.  **Activate the virtual environment:**
    *   Linux/macOS: `source .venv/bin/activate`
    *   Windows (CMD): `.venv\Scripts\activate.bat`
    *   Windows (PowerShell): `.venv\Scripts\Activate.ps1`

2.  **List available pipelines:**
    (Ensure `example_pipelines.py` exists and defines pipelines)
    ```bash
    pipeline-cli list
    ```

3.  **Run a specific pipeline manually:**
    ```bash
    pipeline-cli run <pipeline_name>
    # Example:
    # pipeline-cli run simple_linear_pipeline
    ```

4.  **Start the trigger monitor:**
    (Ensure `example_triggers.py` exists and defines triggers)
    ```bash
    pipeline-cli monitor
    # Or with options:
    # pipeline-cli monitor --webhook-port 5001
    ```
    The monitor will run in the foreground. Press `Ctrl+C` to stop it. While running, it will:
    *   Check cron triggers based on their schedule.
    *   Watch for file events in configured directories (e.g., `./watched_files` for the example).
    *   Listen for webhook requests on configured endpoints (e.g., `http://127.0.0.1:5000/hooks/trigger-fail` for the example).

5.  **Run tests:**
    ```bash
    pytest
    # Or using uv:
    # uv run pytest
    ```

## Project Structure (Core)

*   `pipeline_framework/`: Main package directory.
    *   `core.py`: Defines `Pipeline`, `Step`, `PipelineRunContext`.
    *   `engine.py`: Contains the `PipelineExecutionEngine`.
    *   `triggers/`: Contains trigger base class, specific implementations (Cron, File, Webhook), and registry.
    *   `monitor.py`: Implements the `TriggerMonitor` service.
    *   `pipeline_registry.py`: Handles discovery and registration of pipelines.
    *   `cli.py`: Defines the command-line interface using Click.
    *   `logging_config.py`: Basic logging setup.
    *   `errors.py`: Custom exception classes.
*   `example_pipelines.py`: Example pipeline definitions.
*   `example_triggers.py`: Example trigger definitions.
*   `tests/`: Unit and integration tests.
*   `pyproject.toml`: Project metadata and dependencies (using PEP 621 format, managed with `uv`).
*   `requirements.md`: Detailed project requirements breakdown.
*   `README.md`: This file.
*   `logo.jpg`: Project logo.

## Future Development (Based on Requirements)

*   Step definition via function decorators (`@step`).
*   Conditional step execution logic.
*   Automatic data persistence between steps.
*   Web UI for visualization and monitoring.
