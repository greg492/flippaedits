"""Background worker classes for Qt threading.

This module provides QRunnable workers for executing tasks in QThreadPool,
following Qt best practices for responsive GUI applications.

Pattern:
    - Use QThreadPool.globalInstance().start(worker) to run tasks
    - Connect worker.signals to GUI slots for updates
    - Never use QThread subclassing or processEvents()
"""

from typing import Callable, Any
from PySide6.QtCore import QRunnable, Slot

from .signals import WorkerSignals


class Worker(QRunnable):
    """Generic background task worker.

    Executes a function in a background thread via QThreadPool, emitting
    signals for progress, status, results, and errors.

    Args:
        fn: Function to execute in background
        *args: Positional arguments for fn
        **kwargs: Keyword arguments for fn

    Special kwargs:
        task_name: If provided, emitted as initial status message

    Usage:
        def my_task(arg1, progress_callback=None):
            if progress_callback:
                progress_callback(50)
            return "result"

        worker = Worker(my_task, "value", task_name="Processing")
        worker.signals.progress.connect(update_ui)
        worker.signals.finished.connect(on_complete)
        QThreadPool.globalInstance().start(worker)
    """

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Initialize worker with function and arguments.

        Args:
            fn: Function to execute
            *args: Positional arguments for fn
            **kwargs: Keyword arguments for fn (task_name is special)
        """
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_cancelled = False

        # Extract task_name if provided (don't pass to fn)
        self.task_name = self.kwargs.pop('task_name', None)

    def cancel(self) -> None:
        """Request cancellation of the task.

        Sets the is_cancelled flag. The task function should check
        this periodically and exit early if cancelled.
        """
        self.is_cancelled = True

    @Slot()
    def run(self) -> None:
        """Execute the task function.

        Emits status, progress, result, and error signals as appropriate.
        Always emits finished signal when complete (success or failure).
        """
        try:
            # Emit initial status if task_name provided
            if self.task_name:
                self.signals.status.emit(self.task_name)

            # Execute function with progress callback
            result = self.fn(
                *self.args,
                progress_callback=self.signals.progress.emit,
                **self.kwargs
            )

            # Emit result if not cancelled
            if not self.is_cancelled:
                self.signals.result.emit(result)

        except Exception as e:
            # Emit error message (assumed to be user-friendly)
            self.signals.error.emit(str(e))

        finally:
            # Always emit finished
            self.signals.finished.emit()
