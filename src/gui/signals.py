"""Worker signals for background task communication.

This module provides Qt signal classes for communicating between background workers
(running in QThreadPool) and the main GUI thread. Signals must be in QObject classes,
not QRunnable directly.
"""

from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """Signals for worker-to-GUI communication.

    These signals allow background tasks to communicate progress, results,
    and errors to the main thread without blocking the GUI.

    Signals:
        progress: Emits int (0-100) for progress percentage
        finished: Emits when task completes (success or failure)
        error: Emits str with user-friendly error message
        result: Emits object with task result data (e.g., file path)
        status: Emits str with current operation description
    """

    progress = Signal(int)      # Progress percentage 0-100
    finished = Signal()          # Task completed successfully
    error = Signal(str)          # Error message (already user-friendly)
    result = Signal(object)      # Result data (e.g., output file path)
    status = Signal(str)         # Status message for display (e.g., "Generating proxy...")
