"""Main application window with drag-drop video import and progress tracking.

This module provides the primary GUI interface for the Lacrosse Reel Editor,
featuring drag-drop video import, background task processing, and real-time
progress indicators.
"""

import sys
from pathlib import Path
from typing import Optional, Callable

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
from .video_preview import VideoPreviewWidget
from ..processing.video_info import get_video_info, VideoInfo, is_supported_format
from ..processing.proxy import generate_proxy
from ..storage.temp_manager import get_temp_manager, is_external_drive, needs_copy


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

        # Video state
        self.source_video_path: Optional[Path] = None
        self.proxy_video_path: Optional[Path] = None
        self.video_info: Optional[VideoInfo] = None

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

        # Video preview (hidden initially)
        self.video_preview = VideoPreviewWidget()
        self.video_preview.setVisible(False)
        self.video_preview.video_loaded.connect(self.on_video_preview_loaded)
        layout.addWidget(self.video_preview, stretch=1)

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

        Triggers complete import workflow in background:
        1. Validate file format (lightweight check)
        2. Extract video metadata
        3. Copy from external drive if needed
        4. Generate 720p proxy
        5. Load proxy into preview on completion

        All I/O operations run in background thread to prevent GUI freeze.

        Args:
            path: Absolute path to dropped video file
        """
        file_path = Path(path)

        # Quick format validation (non-blocking)
        if not file_path.suffix.lower() in ('.mp4', '.mov'):
            self.show_error("Unsupported format. Please use .mp4 or .mov files.")
            return

        # Check file exists (lightweight)
        if not file_path.exists():
            self.show_error(f"File not found: {file_path.name}")
            return

        # Show initial status
        self.show_status("Preparing video import...")

        # Create worker for complete import workflow
        worker = Worker(
            self._import_workflow,
            str(file_path),
            task_name="Importing video..."
        )

        # Connect result signal to load preview
        worker.signals.result.connect(self.on_proxy_complete)

        # Start background task
        self.start_background_task(worker)

    def _import_workflow(
        self,
        input_path: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """Complete video import workflow running in background thread.

        Handles all I/O operations:
        1. Get video metadata
        2. Copy from external drive if needed
        3. Generate 720p proxy

        Args:
            input_path: Path to source video file
            progress_callback: Progress callback (0-100)

        Returns:
            Path to generated proxy file

        Raises:
            ValueError: If video format unsupported or no video stream
            Exception: For other processing errors
        """
        file_path = Path(input_path)

        try:
            # Step 1: Get video metadata (I/O operation)
            if progress_callback:
                progress_callback(5)

            try:
                self.video_info = get_video_info(file_path)
            except ValueError as e:
                # Handle missing video stream or corrupted files
                raise ValueError(f"Invalid video file: {str(e)}")
            except Exception as e:
                # Catch any other errors during metadata extraction
                raise Exception(f"Could not read video metadata: {str(e)}")

            # Emit status if not 4K (but still process)
            if not self.video_info.is_4k:
                # Note: Can't call show_status directly (wrong thread)
                # Worker will emit via status signal
                pass

            if progress_callback:
                progress_callback(10)

            # Step 2: Handle external drive files (I/O operation)
            if needs_copy(file_path):
                try:
                    temp_manager = get_temp_manager()
                    file_path = temp_manager.copy_video(file_path)
                except (OSError, IOError) as e:
                    # Handle file copy errors (permissions, disk full, etc.)
                    raise Exception(f"Could not copy video from external drive: {str(e)}")

            if progress_callback:
                progress_callback(15)

            # Store source path (safe - will be used in main thread later)
            self.source_video_path = file_path

            # Get proxy output path
            temp_manager = get_temp_manager()
            proxy_path = temp_manager.get_proxy_path(file_path.name)
            self.proxy_video_path = proxy_path

            # Step 3: Generate proxy (heavy I/O operation)
            # Progress 15-100 used by proxy generation
            def proxy_progress(percent: int) -> None:
                """Map proxy progress (0-100) to workflow progress (15-100)."""
                if progress_callback:
                    mapped = 15 + int(percent * 0.85)
                    progress_callback(mapped)

            try:
                result = generate_proxy(
                    str(file_path),
                    str(proxy_path),
                    progress_callback=proxy_progress
                )
            except ValueError as e:
                # Handle missing video stream errors
                raise ValueError(f"Cannot generate proxy: {str(e)}")
            except Exception as e:
                # Handle encoding errors
                raise Exception(f"Proxy generation failed: {str(e)}")

            return result

        except ValueError as e:
            # User-friendly message for validation errors
            raise ValueError(str(e))
        except Exception as e:
            # Preserve the error message (already user-friendly)
            raise Exception(str(e))

    @Slot(str)
    def on_proxy_complete(self, proxy_path: str) -> None:
        """Handle proxy generation completion.

        Loads proxy into video preview widget and shows it.

        Args:
            proxy_path: Path to generated proxy file
        """
        try:
            # Validate proxy file exists
            if not Path(proxy_path).exists():
                self.show_error(f"Proxy file not found: {Path(proxy_path).name}")
                return

            # Load proxy into preview
            self.video_preview.load_video(proxy_path)

            # Status will update to "Ready" when video loads
            self.show_status("Loading preview...")

        except Exception as e:
            self.show_error(f"Failed to load preview: {str(e)}")

    @Slot()
    def on_video_preview_loaded(self) -> None:
        """Handle video preview loaded and ready to play.

        Hides drop zone and shows preview widget.
        """
        # Hide drop zone, show preview
        self.drop_zone.setVisible(False)
        self.video_preview.setVisible(True)

        # Update status
        self.show_status("Ready to edit")

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
