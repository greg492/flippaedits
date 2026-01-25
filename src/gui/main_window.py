"""Main application window with drag-drop video import and progress tracking.

This module provides the primary GUI interface for the Lacrosse Reel Editor,
featuring drag-drop video import, background task processing, and real-time
progress indicators.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from PySide6.QtCore import Qt, Signal, Slot, QThreadPool, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)

from .workers import Worker
from .video_preview import VideoPreviewWidget
from .timeline_widget import TimelineWidget
from .effects_panel import EffectsPanel
from .music_panel import MusicPanel
from .preview_controller import PreviewController
from .export_dialog import ExportDialog
from ..processing.video_info import get_video_info, VideoInfo, is_supported_format
from ..processing.proxy import generate_proxy
from ..processing.edit_session import EditSession
from ..processing.template_sequences import apply_template, TEMPLATES
from ..processing.export import assemble_segments, mix_audio, export_for_instagram, export_for_tiktok
from ..storage.temp_manager import get_temp_manager, is_external_drive, needs_copy
from ..audio import BeatDetectorWorker, BeatSnapper, WaveformCache

import numpy as np


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

        # Edit session and preview controller
        self.edit_session = EditSession()
        self.preview_controller = PreviewController(self)

        # Music sync state
        self.music_panel: Optional[MusicPanel] = None
        self.beat_snapper: Optional[BeatSnapper] = None
        self.beat_worker: Optional[BeatDetectorWorker] = None
        self.beat_thread: Optional[QThread] = None

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

        # Timeline widget (hidden initially)
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setVisible(False)
        layout.addWidget(self.timeline_widget)

        # Music panel (hidden initially, below timeline)
        self.music_panel = MusicPanel()
        self.music_panel.setVisible(False)
        layout.addWidget(self.music_panel)

        # Effects panel (hidden initially)
        self.effects_panel = EffectsPanel()
        self.effects_panel.setVisible(False)
        layout.addWidget(self.effects_panel)

        # Export button (hidden until ready)
        self.export_btn = QPushButton("Export Reel")
        self.export_btn.setEnabled(False)
        self.export_btn.setVisible(False)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                font-size: 16px;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(self.export_btn)

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

        # Connect signals
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect widget signals to handlers."""
        # Timeline signals -> EditSession updates
        self.timeline_widget.goal_marked.connect(self._on_goal_marked)
        self.timeline_widget.celebration_marked.connect(self._on_celebration_marked)
        self.timeline_widget.markers_cleared.connect(self._on_markers_cleared)

        # Music panel signals
        self.music_panel.music_loaded.connect(self._on_music_loaded)
        self.music_panel.volume_changed.connect(self._on_music_volume_changed)
        self.music_panel.playback_requested.connect(self._on_music_playback_requested)

        # Effects panel signals
        self.effects_panel.speed_changed.connect(self._on_speed_changed)
        self.effects_panel.lut_changed.connect(self._on_lut_changed)
        self.effects_panel.preview_requested.connect(self._on_preview_requested)

        # Video preview position -> timeline position
        self.video_preview.position_changed.connect(self._on_preview_position_changed)

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

        logger.info(f"Starting import workflow for: {file_path}")

        try:
            # Step 1: Get video metadata (I/O operation)
            if progress_callback:
                progress_callback(5)

            logger.info("Getting video metadata...")
            try:
                self.video_info = get_video_info(file_path)
                logger.info(f"Video info: {self.video_info.width}x{self.video_info.height} @ {self.video_info.fps}fps")
            except ValueError as e:
                # Handle missing video stream or corrupted files
                logger.error(f"Invalid video file: {e}")
                raise ValueError(f"Invalid video file: {str(e)}")
            except Exception as e:
                # Catch any other errors during metadata extraction
                logger.error(f"Could not read video metadata: {e}")
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
                logger.info(f"File is on external drive, copying to temp storage...")
                try:
                    temp_manager = get_temp_manager()
                    file_path = temp_manager.copy_video(file_path)
                    logger.info(f"Copied to: {file_path}")
                except (OSError, IOError) as e:
                    # Handle file copy errors (permissions, disk full, etc.)
                    logger.error(f"Copy failed: {e}")
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
            logger.info(f"Generating proxy at: {proxy_path}")

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
                logger.info(f"Proxy generation complete: {result}")
            except ValueError as e:
                # Handle missing video stream errors
                logger.error(f"Proxy generation validation error: {e}")
                raise ValueError(f"Cannot generate proxy: {str(e)}")
            except Exception as e:
                # Handle encoding errors
                logger.error(f"Proxy generation failed: {e}")
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

            # Update edit session with paths
            self.edit_session.proxy_path = Path(proxy_path)

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

        # Show editing controls
        self.timeline_widget.setVisible(True)
        self.timeline_widget.set_enabled(True)
        self.music_panel.setVisible(True)
        self.effects_panel.setVisible(True)
        self.export_btn.setVisible(True)

        # Set duration on timeline
        duration = self.video_preview.media_player.duration()
        self.timeline_widget.set_duration(duration)

        # Update status
        self.show_status("Ready to edit - mark timestamps and apply effects")

    @Slot(int)
    def _on_goal_marked(self, position_ms: int) -> None:
        """Handle goal timestamp marked - apply beat snap if music loaded."""
        if self.beat_snapper:
            position_ms = self.beat_snapper.snap_to_beat_ms(position_ms)
            # Update timeline display with snapped position
            self.timeline_widget.marker_display.set_goal_marker(position_ms)

        self.edit_session.goal_moment_ms = position_ms
        self._update_preview_button_state()
        logger.info(f"Goal marked in session: {position_ms}ms")

    @Slot(int)
    def _on_celebration_marked(self, position_ms: int) -> None:
        """Handle celebration timestamp marked - apply beat snap if music loaded."""
        if self.beat_snapper:
            position_ms = self.beat_snapper.snap_to_beat_ms(position_ms)
            # Update timeline display with snapped position
            self.timeline_widget.marker_display.set_celebration_marker(position_ms)

        self.edit_session.celebration_start_ms = position_ms
        self._update_preview_button_state()  # This now also updates export button
        logger.info(f"Celebration marked in session: {position_ms}ms")

    @Slot()
    def _on_markers_cleared(self) -> None:
        """Handle markers cleared."""
        self.edit_session.goal_moment_ms = None
        self.edit_session.celebration_start_ms = None
        self._update_preview_button_state()

    @Slot(float)
    def _on_speed_changed(self, speed: float) -> None:
        """Handle slow-motion speed changed."""
        self.edit_session.slow_motion.speed = speed

    @Slot(object)
    def _on_lut_changed(self, lut_preset) -> None:
        """Handle LUT preset changed."""
        if lut_preset:
            self.edit_session.color_grading.lut_name = lut_preset.name
            self.edit_session.color_grading.lut_path = lut_preset.path
        else:
            self.edit_session.color_grading.lut_name = None
            self.edit_session.color_grading.lut_path = None

    @Slot(float)
    def _on_preview_position_changed(self, position_sec: float) -> None:
        """Handle preview position change - update timeline."""
        position_ms = int(position_sec * 1000)
        self.timeline_widget.update_position(position_ms)

    def _update_preview_button_state(self) -> None:
        """Update preview button enabled state based on session."""
        ready = self.edit_session.is_ready_for_preview()
        self.effects_panel.set_preview_enabled(ready)

        # Also update export button (requires both timestamps)
        export_ready = self.edit_session.is_ready_for_export()
        self.export_btn.setEnabled(export_ready)

    @Slot()
    def _on_preview_requested(self) -> None:
        """Handle preview generation request."""
        if not self.edit_session.is_ready_for_preview():
            self.show_error("Mark goal timestamp before generating preview")
            return

        self.show_status("Generating preview with effects...")

        # Create worker for preview generation
        worker = Worker(
            self._generate_preview_workflow,
            self.edit_session,
            task_name="Generating preview..."
        )

        worker.signals.result.connect(self._on_preview_generated)
        self.start_background_task(worker)

    def _generate_preview_workflow(
        self,
        session: EditSession,
        progress_callback=None
    ) -> str:
        """Background workflow for preview generation."""
        return self.preview_controller.generate_preview(session, progress_callback)

    @Slot(str)
    def _on_preview_generated(self, preview_path: str) -> None:
        """Handle preview generation complete."""
        self.show_status("Preview ready - playing...")
        self.video_preview.load_video(preview_path)

    @Slot(str, int)
    def _on_music_loaded(self, file_path: str, duration_ms: int) -> None:
        """Handle music file loaded - start beat detection."""
        self.show_status("Detecting beats...")

        # Store in edit session
        self.edit_session.music_track.file_path = Path(file_path)
        self.edit_session.music_track.duration_ms = duration_ms

        # Start beat detection in background thread
        self._start_beat_detection(file_path)

    def _start_beat_detection(self, audio_path: str) -> None:
        """Start beat detection worker in background thread."""
        # Clean up any existing worker
        if self.beat_thread and self.beat_thread.isRunning():
            self.beat_thread.quit()
            self.beat_thread.wait()

        # Create worker and thread
        self.beat_worker = BeatDetectorWorker(audio_path)
        self.beat_thread = QThread()
        self.beat_worker.moveToThread(self.beat_thread)

        # Connect signals
        self.beat_worker.progress.connect(self.show_status)
        self.beat_worker.finished.connect(self._on_beats_detected)
        self.beat_worker.error.connect(self.show_error)

        # Start
        self.beat_thread.started.connect(self.beat_worker.run)
        self.beat_worker.finished.connect(self.beat_thread.quit)
        self.beat_thread.start()

    @Slot(object, object, object, int, int)
    def _on_beats_detected(self, beats: np.ndarray, onset_env: np.ndarray, tempo: float, sr: int, hop_length: int) -> None:
        """Handle beat detection complete.

        Args:
            beats: Array of beat times in seconds
            onset_env: Onset envelope array
            tempo: Detected tempo in BPM
            sr: Sample rate used during detection (from BeatDetectorWorker)
            hop_length: Hop length used during detection (from BeatDetectorWorker)
        """
        # Store in edit session - including sr and hop_length from worker
        self.edit_session.music_track.beats = beats
        self.edit_session.music_track.onset_envelope = onset_env
        self.edit_session.music_track.tempo = tempo
        self.edit_session.music_track.sample_rate = sr
        self.edit_session.music_track.hop_length = hop_length

        # Create beat snapper
        self.beat_snapper = BeatSnapper(beats, tolerance_ms=50)

        # Calculate beat intensities using values from MusicTrack (not hardcoded)
        intensities = self._calculate_beat_intensities(beats, onset_env)

        # Update UI
        duration_sec = self.edit_session.music_track.duration_ms / 1000.0
        self.timeline_widget.marker_display.set_beat_markers(beats, intensities, duration_sec)

        # Also update music panel waveform
        self.music_panel.set_beats(beats, intensities)

        self.show_status(f"Detected {len(beats)} beats at {tempo:.0f} BPM")

    def _calculate_beat_intensities(self, beats: np.ndarray, onset_env: np.ndarray) -> np.ndarray:
        """Calculate normalized intensities for each beat.

        Uses sample_rate and hop_length from MusicTrack to correctly
        map beat times to onset envelope frames.
        """
        # Use stored values from MusicTrack, NOT hardcoded defaults
        sr = self.edit_session.music_track.sample_rate
        hop_length = self.edit_session.music_track.hop_length

        intensities = []
        for beat_time in beats:
            frame = int(beat_time * sr / hop_length)
            if 0 <= frame < len(onset_env):
                intensities.append(onset_env[frame])
            else:
                intensities.append(0.5)
        intensities = np.array(intensities)
        if len(intensities) > 0 and np.max(intensities) > 0:
            intensities = intensities / np.max(intensities)
        return intensities

    @Slot(float)
    def _on_music_volume_changed(self, volume: float) -> None:
        """Handle music volume changed."""
        self.edit_session.music_track.volume = volume
        logger.info(f"Music volume: {volume:.2f}")

    @Slot(bool)
    def _on_music_playback_requested(self, play: bool) -> None:
        """Handle music playback request."""
        # For v1, just log - can sync with video preview later
        logger.info(f"Music playback: {'play' if play else 'pause'}")

    @Slot()
    def _on_export_clicked(self):
        """Handle Export button click - show export dialog."""
        if not self.edit_session.is_ready_for_export():
            self.show_error("Mark both goal and celebration timestamps before exporting")
            return

        # Generate default filename from source video
        source_name = self.source_video_path.stem if self.source_video_path else "reel"
        default_name = f"{source_name}_reel.mp4"

        self.export_dialog = ExportDialog(self, default_filename=default_name)
        self.export_dialog.export_requested.connect(self._on_export_requested)
        self.export_dialog.show()

    @Slot(str, str, str)
    def _on_export_requested(self, template_name: str, platform: str, output_path: str):
        """Handle export request from dialog."""
        self.show_status(f"Exporting with {TEMPLATES[template_name].name} template...")

        # Create worker for export workflow
        worker = Worker(
            self._export_workflow,
            template_name, platform, output_path,
            task_name="Exporting reel..."
        )

        # Connect progress to dialog
        worker.signals.progress.connect(self.export_dialog.set_progress)
        worker.signals.status.connect(self.export_dialog.set_status)
        worker.signals.result.connect(self._on_export_complete)
        worker.signals.error.connect(self._on_export_error)

        self.start_background_task(worker)

    def _export_workflow(
        self,
        template_name: str,
        platform: str,
        output_path: str,
        progress_callback=None
    ) -> str:
        """Complete export workflow running in background thread.

        Steps:
        1. Apply template to get segments
        2. Assemble segments with beat snapping
        3. Mix audio (video + music)
        4. Export to platform format (Instagram/TikTok vertical)
        """
        import tempfile
        import os

        logger.info(f"Starting export: template={template_name}, platform={platform}")

        # Step 1: Apply template (5%)
        if progress_callback:
            progress_callback(5)

        segments = apply_template(self.edit_session, template_name)
        logger.info(f"Template applied: {len(segments)} segments")

        # Get beats for snapping (if music loaded)
        beats = self.edit_session.music_track.beats
        if beats is None:
            beats = np.array([])

        # Create temp files for intermediate stages
        temp_assembled = tempfile.mktemp(suffix='_assembled.mp4', prefix='export_')
        temp_mixed = tempfile.mktemp(suffix='_mixed.mp4', prefix='export_')

        try:
            # Step 2: Assemble segments with beat snapping (5-40%)
            def assemble_progress(p):
                if progress_callback:
                    progress_callback(5 + int(p * 0.35))

            logger.info("Assembling segments...")
            assemble_segments(
                str(self.edit_session.source_path),
                temp_assembled,
                segments,
                beats,
                snap_tolerance_ms=50,
                progress_callback=assemble_progress
            )

            # Step 3: Mix audio if music loaded (40-60%)
            if self.edit_session.music_track.file_path:
                def mix_progress(p):
                    if progress_callback:
                        progress_callback(40 + int(p * 0.20))

                logger.info("Mixing audio...")
                mix_audio(
                    temp_assembled,
                    str(self.edit_session.music_track.file_path),
                    temp_mixed,
                    video_volume=0.3,
                    music_volume=self.edit_session.music_track.volume,
                    trim_start_ms=self.edit_session.music_track.trim_start_ms,
                    trim_end_ms=self.edit_session.music_track.trim_end_ms,
                    progress_callback=mix_progress
                )
                source_for_export = temp_mixed
            else:
                source_for_export = temp_assembled

            # Step 4: Export to platform format (60-100%)
            def export_progress(p):
                if progress_callback:
                    progress_callback(60 + int(p * 0.40))

            logger.info(f"Exporting for {platform}...")
            if platform == "instagram":
                export_for_instagram(source_for_export, output_path, progress_callback=export_progress)
            else:
                export_for_tiktok(source_for_export, output_path, progress_callback=export_progress)

            logger.info(f"Export complete: {output_path}")
            return output_path

        finally:
            # Clean up temp files
            for temp_file in [temp_assembled, temp_mixed]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    @Slot(str)
    def _on_export_complete(self, output_path: str):
        """Handle export completion."""
        self.export_dialog.export_complete(output_path)
        self.show_status(f"Export complete: {Path(output_path).name}")

    @Slot(str)
    def _on_export_error(self, error: str):
        """Handle export error."""
        self.export_dialog.set_status(f"Error: {error}")
        self.show_error(error)

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
