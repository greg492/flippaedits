"""Main application window with drag-drop video import and progress tracking.

This module provides the primary GUI interface for the Lacrosse Reel Editor,
featuring drag-drop video import, background task processing, and real-time
progress indicators.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot, QThreadPool
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
)

from .workers import Worker


class VideoDropZone(QWidget):
    """Drag-and-drop zone for video file import.

    Provides visual feedback during drag operations and emits file paths
    when valid video files (.mp4, .mov) are dropped.

    Signals:
        file_dropped: Emits str with absolute path to dropped video file
    """

    file_dropped = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize drop zone widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure drop zone appearance."""
        # Create layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create drop instruction label
        self.label = QLabel("Drop 4K video here\n(.mp4 or .mov)")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #666666;
                padding: 40px;
            }
        """)

        layout.addWidget(self.label)
        self.setLayout(layout)

        # Style the drop zone
        self.setStyleSheet("""
            VideoDropZone {
                background-color: #f5f5f5;
                border: 3px dashed #cccccc;
                border-radius: 10px;
                min-height: 300px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event.

        Args:
            event: Drag enter event
        """
        # Accept if event contains file URLs
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            # Change border color to indicate valid drop target
            self.setStyleSheet("""
                VideoDropZone {
                    background-color: #e8f4f8;
                    border: 3px dashed #4a90e2;
                    border-radius: 10px;
                    min-height: 300px;
                }
            """)

    def dragLeaveEvent(self, event) -> None:
        """Handle drag leave event.

        Args:
            event: Drag leave event
        """
        # Reset border color
        self.setStyleSheet("""
            VideoDropZone {
                background-color: #f5f5f5;
                border: 3px dashed #cccccc;
                border-radius: 10px;
                min-height: 300px;
            }
        """)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event.

        Args:
            event: Drop event
        """
        # Reset border color
        self.dragLeaveEvent(event)

        # Extract file paths from URLs
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            # Accept only .mp4 and .mov files
            if file_path.lower().endswith(('.mp4', '.mov')):
                self.file_dropped.emit(file_path)
                break  # Only handle first valid file


class MainWindow(QMainWindow):
    """Main application window.

    Provides the primary interface for video import, processing, and
    progress tracking. Manages background tasks using QThreadPool.
    """

    def __init__(self) -> None:
        """Initialize main window."""
        super().__init__()
        self.threadpool = QThreadPool.globalInstance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure window and widgets."""
        # Window properties
        self.setWindowTitle("Lacrosse Reel Editor")
        self.setMinimumSize(800, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Drop zone
        self.drop_zone = VideoDropZone()
        self.drop_zone.file_dropped.connect(self.on_file_dropped)
        layout.addWidget(self.drop_zone, stretch=1)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #cccccc;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #4a90e2;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333333;
                padding: 10px;
            }
        """)
        layout.addWidget(self.status_label)

        central_widget.setLayout(layout)

    @Slot(int)
    def update_progress(self, value: int) -> None:
        """Update progress bar value.

        Args:
            value: Progress percentage (0-100)
        """
        self.progress_bar.setValue(value)
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)

    @Slot(str)
    def show_status(self, message: str) -> None:
        """Update status label with normal message.

        Args:
            message: Status message to display
        """
        self.status_label.setText(message)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #333333;
                padding: 10px;
            }
        """)

    @Slot(str)
    def show_error(self, message: str) -> None:
        """Update status label with error message.

        Args:
            message: Error message to display
        """
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #d32f2f;
                padding: 10px;
                font-weight: bold;
            }
        """)

    @Slot()
    def on_task_finished(self) -> None:
        """Handle task completion.

        Hides progress bar and resets to ready state.
        """
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.show_status("Ready")

    @Slot(str)
    def on_file_dropped(self, path: str) -> None:
        """Handle dropped video file.

        Stub for Plan 01-04 where video processing will be integrated.

        Args:
            path: Absolute path to dropped video file
        """
        # For now, just show the file path
        self.show_status(f"Received: {Path(path).name}")
        # TODO (Plan 01-04): Trigger proxy generation workflow

    def start_background_task(self, worker: Worker) -> None:
        """Start a worker in the background thread pool.

        Connects worker signals to GUI slots and starts execution.

        Args:
            worker: Worker instance to execute
        """
        # Connect worker signals to GUI slots
        worker.signals.progress.connect(self.update_progress)
        worker.signals.status.connect(self.show_status)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.on_task_finished)

        # Start worker in thread pool
        self.threadpool.start(worker)


def main() -> int:
    """Application entry point.

    Returns:
        Exit code
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
