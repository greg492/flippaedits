"""Main application window with simplified drag-drop workflow.

New workflow:
1. Drop video AND audio files together
2. Mark 3 points: Goal, Celebration (on video), Drop (on audio)
3. Hit "Start Analyzing" to auto-generate the edit
"""

import logging
import sys
import tempfile
import os
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
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QFileDialog,
    QFrame,
)

from .workers import Worker
from .video_preview import VideoPreviewWidget
from .timeline_widget import TimelineWidget
from .music_panel import MusicPanel
from ..processing.video_info import get_video_info, VideoInfo
from ..processing.proxy import generate_proxy
from ..processing.edit_session import EditSession
from ..processing.template_sequences import apply_template, TEMPLATES
from ..processing.export import assemble_segments, mix_audio, export_for_instagram, export_for_tiktok
from ..storage.temp_manager import get_temp_manager, needs_copy
from ..audio import BeatDetectorWorker, BeatSnapper

import numpy as np


class MediaDropZone(QWidget):
    """Drag-and-drop zone for video AND audio file import.

    Accepts video (.mp4, .mov) and audio (.mp3, .wav) files.
    User should drop both files to proceed.

    Signals:
        files_dropped: Emits (video_path, audio_path) when both are dropped
    """

    files_dropped = Signal(str, str)  # video_path, audio_path

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._video_path: Optional[str] = None
        self._audio_path: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure drop zone appearance."""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Main instruction label
        self.label = QLabel("Drop your video and audio files here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333333;
                padding: 20px;
            }
        """)
        layout.addWidget(self.label)

        # Sub-instruction
        self.sub_label = QLabel("Video: .mp4 or .mov  |  Audio: .mp3 or .wav")
        self.sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #666666;
                padding: 10px;
            }
        """)
        layout.addWidget(self.sub_label)

        # Status indicators
        self.status_frame = QFrame()
        status_layout = QHBoxLayout()
        status_layout.setSpacing(40)

        self.video_status = QLabel("Video: Not loaded")
        self.video_status.setStyleSheet("font-size: 14px; color: #999999;")
        status_layout.addWidget(self.video_status)

        self.audio_status = QLabel("Audio: Not loaded")
        self.audio_status.setStyleSheet("font-size: 14px; color: #999999;")
        status_layout.addWidget(self.audio_status)

        self.status_frame.setLayout(status_layout)
        layout.addWidget(self.status_frame)

        self.setLayout(layout)

        # Style the drop zone
        self._set_default_style()

    def _set_default_style(self) -> None:
        self.setStyleSheet("""
            MediaDropZone {
                background-color: #f8f9fa;
                border: 3px dashed #cccccc;
                border-radius: 12px;
                min-height: 300px;
            }
        """)

    def _set_active_style(self) -> None:
        self.setStyleSheet("""
            MediaDropZone {
                background-color: #e3f2fd;
                border: 3px dashed #2196F3;
                border-radius: 12px;
                min-height: 300px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active_style()

    def dragLeaveEvent(self, event) -> None:
        self._set_default_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_default_style()

        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            lower = file_path.lower()

            if lower.endswith(('.mp4', '.mov')):
                self._video_path = file_path
                self.video_status.setText(f"Video: {Path(file_path).name}")
                self.video_status.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")

            elif lower.endswith(('.mp3', '.wav')):
                self._audio_path = file_path
                self.audio_status.setText(f"Audio: {Path(file_path).name}")
                self.audio_status.setStyleSheet("font-size: 14px; color: #2196F3; font-weight: bold;")

        # Emit when both are loaded
        if self._video_path and self._audio_path:
            self.files_dropped.emit(self._video_path, self._audio_path)

    def reset(self) -> None:
        """Reset the drop zone state."""
        self._video_path = None
        self._audio_path = None
        self.video_status.setText("Video: Not loaded")
        self.video_status.setStyleSheet("font-size: 14px; color: #999999;")
        self.audio_status.setText("Audio: Not loaded")
        self.audio_status.setStyleSheet("font-size: 14px; color: #999999;")


class MainWindow(QMainWindow):
    """Main application window with simplified workflow.

    Workflow:
    1. Drop video + audio files together
    2. Mark Goal, Celebration, and Drop points
    3. Click "Start Analyzing" to generate edit
    """

    def __init__(self) -> None:
        super().__init__()
        self.threadpool = QThreadPool.globalInstance()

        # Video state
        self.source_video_path: Optional[Path] = None
        self.proxy_video_path: Optional[Path] = None
        self.video_info: Optional[VideoInfo] = None
        self.audio_path: Optional[Path] = None

        # Edit session
        self.edit_session = EditSession()

        # Music sync state
        self.beat_snapper: Optional[BeatSnapper] = None
        self.beat_worker: Optional[BeatDetectorWorker] = None
        self.beat_thread: Optional[QThread] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure window and widgets."""
        self.setWindowTitle("Lacrosse Reel Editor")
        self.setMinimumSize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Drop zone (visible initially)
        self.drop_zone = MediaDropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone, stretch=1)

        # Video preview (hidden initially)
        self.video_preview = VideoPreviewWidget()
        self.video_preview.setVisible(False)
        self.video_preview.video_loaded.connect(self._on_video_preview_loaded)
        layout.addWidget(self.video_preview, stretch=1)

        # Timeline with markers (hidden initially)
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setVisible(False)
        layout.addWidget(self.timeline_widget)

        # Music panel / waveform (hidden initially)
        self.music_panel = MusicPanel()
        self.music_panel.setVisible(False)
        layout.addWidget(self.music_panel)

        # Marker status display (hidden initially)
        self.marker_status_frame = QFrame()
        self.marker_status_frame.setVisible(False)
        marker_layout = QHBoxLayout()
        marker_layout.setSpacing(30)

        self.goal_status = QLabel("Goal: Not set")
        self.goal_status.setStyleSheet("font-size: 14px; color: #4CAF50;")
        marker_layout.addWidget(self.goal_status)

        self.celeb_status = QLabel("Celebration: Not set")
        self.celeb_status.setStyleSheet("font-size: 14px; color: #FF9800;")
        marker_layout.addWidget(self.celeb_status)

        self.drop_status = QLabel("Drop: Not set")
        self.drop_status.setStyleSheet("font-size: 14px; color: #9C27B0;")
        marker_layout.addWidget(self.drop_status)

        marker_layout.addStretch()
        self.marker_status_frame.setLayout(marker_layout)
        layout.addWidget(self.marker_status_frame)

        # Start Analyzing button (hidden until ready)
        self.analyze_btn = QPushButton("Start Analyzing")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setVisible(False)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 18px;
                padding: 15px 40px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self.analyze_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress bar
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
                background-color: #4CAF50;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Drop your video and audio files to get started")
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
        # Timeline markers
        self.timeline_widget.goal_marked.connect(self._on_goal_marked)
        self.timeline_widget.celebration_marked.connect(self._on_celebration_marked)
        self.timeline_widget.markers_cleared.connect(self._on_markers_cleared)

        # Music panel - for drop marker
        self.music_panel.music_loaded.connect(self._on_music_ready)
        self.music_panel.drop_marked.connect(self._on_drop_marked)

        # Video preview position -> timeline position
        self.video_preview.position_changed.connect(self._on_preview_position_changed)

    @Slot(int)
    def update_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)

    @Slot(str)
    def show_status(self, message: str) -> None:
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
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)

    @Slot(str, str)
    def _on_files_dropped(self, video_path: str, audio_path: str) -> None:
        """Handle both video and audio files dropped."""
        self.source_video_path = Path(video_path)
        self.audio_path = Path(audio_path)

        self.show_status("Processing video and audio...")

        # Start import workflow
        worker = Worker(
            self._import_workflow,
            video_path, audio_path,
            task_name="Importing media..."
        )
        worker.signals.result.connect(self._on_import_complete)
        self.start_background_task(worker)

    def _import_workflow(
        self,
        video_path: str,
        audio_path: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> dict:
        """Import both video and audio files."""
        file_path = Path(video_path)

        logger.info(f"Starting import: video={video_path}, audio={audio_path}")

        # Get video metadata
        if progress_callback:
            progress_callback(5)

        self.video_info = get_video_info(file_path)
        logger.info(f"Video: {self.video_info.width}x{self.video_info.height} @ {self.video_info.fps}fps")

        if progress_callback:
            progress_callback(10)

        # Handle external drive
        if needs_copy(file_path):
            temp_manager = get_temp_manager()
            file_path = temp_manager.copy_video(file_path)

        self.source_video_path = file_path
        self.edit_session.source_path = file_path

        # Generate proxy
        temp_manager = get_temp_manager()
        proxy_path = temp_manager.get_proxy_path(file_path.name)

        def proxy_progress(p):
            if progress_callback:
                progress_callback(10 + int(p * 0.9))

        generate_proxy(str(file_path), str(proxy_path), progress_callback=proxy_progress)

        self.proxy_video_path = proxy_path
        self.edit_session.proxy_path = proxy_path

        return {"proxy_path": str(proxy_path), "audio_path": audio_path}

    @Slot(object)
    def _on_import_complete(self, result: dict) -> None:
        """Handle import completion."""
        proxy_path = result["proxy_path"]
        audio_path = result["audio_path"]

        # Load proxy into preview
        self.video_preview.load_video(proxy_path)

        # Store audio path for music panel
        self._pending_audio_path = audio_path

        self.show_status("Loading preview...")

    @Slot()
    def _on_video_preview_loaded(self) -> None:
        """Handle video preview ready."""
        # Hide drop zone, show editing UI
        self.drop_zone.setVisible(False)
        self.video_preview.setVisible(True)
        self.timeline_widget.setVisible(True)
        self.timeline_widget.set_enabled(True)
        self.music_panel.setVisible(True)
        self.marker_status_frame.setVisible(True)
        self.analyze_btn.setVisible(True)

        # Set duration on timeline
        duration = self.video_preview.media_player.duration()
        self.timeline_widget.set_duration(duration)

        # Load audio into music panel
        if hasattr(self, '_pending_audio_path'):
            self.music_panel._load_music_file(self._pending_audio_path)
            del self._pending_audio_path

        self.show_status("Mark the Goal, Celebration, and Drop points, then click Start Analyzing")

    @Slot(str, int)
    def _on_music_ready(self, file_path: str, duration_ms: int) -> None:
        """Handle music loaded - start beat detection."""
        self.edit_session.music_track.file_path = Path(file_path)
        self.edit_session.music_track.duration_ms = duration_ms

        self.show_status("Detecting beats...")
        self._start_beat_detection(file_path)

    def _start_beat_detection(self, audio_path: str) -> None:
        """Start beat detection in background."""
        if self.beat_thread and self.beat_thread.isRunning():
            self.beat_thread.quit()
            self.beat_thread.wait()

        self.beat_worker = BeatDetectorWorker(audio_path)
        self.beat_thread = QThread()
        self.beat_worker.moveToThread(self.beat_thread)

        self.beat_worker.progress.connect(self.show_status)
        self.beat_worker.finished.connect(self._on_beats_detected)
        self.beat_worker.error.connect(self.show_error)

        self.beat_thread.started.connect(self.beat_worker.run)
        self.beat_worker.finished.connect(self.beat_thread.quit)
        self.beat_thread.start()

    @Slot(object, object, object, int, int)
    def _on_beats_detected(self, beats: np.ndarray, onset_env: np.ndarray, tempo: float, sr: int, hop_length: int) -> None:
        """Handle beat detection complete."""
        self.edit_session.music_track.beats = beats
        self.edit_session.music_track.onset_envelope = onset_env
        self.edit_session.music_track.tempo = tempo
        self.edit_session.music_track.sample_rate = sr
        self.edit_session.music_track.hop_length = hop_length

        self.beat_snapper = BeatSnapper(beats, tolerance_ms=50)

        # Calculate intensities
        intensities = self._calculate_beat_intensities(beats, onset_env, sr, hop_length)

        # Update music panel with beats
        self.music_panel.set_beats(beats, intensities)

        self.show_status(f"Detected {len(beats)} beats at {tempo:.0f} BPM - Mark your points!")
        self._update_analyze_button()

    def _calculate_beat_intensities(self, beats: np.ndarray, onset_env: np.ndarray, sr: int, hop_length: int) -> np.ndarray:
        """Calculate normalized intensities for each beat."""
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

    @Slot(int)
    def _on_goal_marked(self, position_ms: int) -> None:
        """Handle goal marker set."""
        if self.beat_snapper:
            position_ms = self.beat_snapper.snap_to_beat_ms(position_ms)
            self.timeline_widget.marker_display.set_goal_marker(position_ms)

        self.edit_session.goal_moment_ms = position_ms
        self.goal_status.setText(f"Goal: {self._format_time(position_ms)}")
        self.goal_status.setStyleSheet("font-size: 14px; color: #4CAF50; font-weight: bold;")
        self._update_analyze_button()
        logger.info(f"Goal marked: {position_ms}ms")

    @Slot(int)
    def _on_celebration_marked(self, position_ms: int) -> None:
        """Handle celebration marker set."""
        if self.beat_snapper:
            position_ms = self.beat_snapper.snap_to_beat_ms(position_ms)
            self.timeline_widget.marker_display.set_celebration_marker(position_ms)

        self.edit_session.celebration_start_ms = position_ms
        self.celeb_status.setText(f"Celebration: {self._format_time(position_ms)}")
        self.celeb_status.setStyleSheet("font-size: 14px; color: #FF9800; font-weight: bold;")
        self._update_analyze_button()
        logger.info(f"Celebration marked: {position_ms}ms")

    @Slot(int)
    def _on_drop_marked(self, position_ms: int) -> None:
        """Handle drop marker set (on audio)."""
        self.edit_session.drop_moment_ms = position_ms
        self.drop_status.setText(f"Drop: {self._format_time(position_ms)}")
        self.drop_status.setStyleSheet("font-size: 14px; color: #9C27B0; font-weight: bold;")
        self._update_analyze_button()
        logger.info(f"Drop marked: {position_ms}ms")

    @Slot()
    def _on_markers_cleared(self) -> None:
        """Handle markers cleared."""
        self.edit_session.goal_moment_ms = None
        self.edit_session.celebration_start_ms = None
        self.goal_status.setText("Goal: Not set")
        self.goal_status.setStyleSheet("font-size: 14px; color: #4CAF50;")
        self.celeb_status.setText("Celebration: Not set")
        self.celeb_status.setStyleSheet("font-size: 14px; color: #FF9800;")
        self._update_analyze_button()

    @Slot(float)
    def _on_preview_position_changed(self, position_sec: float) -> None:
        """Update timeline position from video preview."""
        position_ms = int(position_sec * 1000)
        self.timeline_widget.update_position(position_ms)

    def _update_analyze_button(self) -> None:
        """Enable analyze button when all markers are set."""
        ready = self.edit_session.is_ready_for_analysis()
        self.analyze_btn.setEnabled(ready)

        if ready:
            self.show_status("Ready! Click Start Analyzing to generate your reel")

    @Slot()
    def _on_analyze_clicked(self) -> None:
        """Handle Start Analyzing button click."""
        if not self.edit_session.is_ready_for_analysis():
            self.show_error("Please mark all three points: Goal, Celebration, and Drop")
            return

        # Ask for output location
        default_name = f"{self.source_video_path.stem}_reel.mp4" if self.source_video_path else "reel.mp4"
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Reel As",
            default_name,
            "Video Files (*.mp4)"
        )

        if not output_path:
            return

        self.show_status("Generating your reel...")
        self.analyze_btn.setEnabled(False)

        worker = Worker(
            self._generate_reel_workflow,
            output_path,
            task_name="Generating reel..."
        )
        worker.signals.result.connect(self._on_reel_complete)
        worker.signals.error.connect(self._on_reel_error)
        self.start_background_task(worker)

    def _generate_reel_workflow(
        self,
        output_path: str,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """Generate the final reel."""
        logger.info(f"Generating reel to: {output_path}")

        # Apply template
        if progress_callback:
            progress_callback(5)

        segments = apply_template(self.edit_session, "goal_celebration")
        logger.info(f"Template applied: {len(segments)} segments")

        beats = self.edit_session.music_track.beats
        if beats is None:
            beats = np.array([])

        temp_assembled = tempfile.mktemp(suffix='_assembled.mp4', prefix='reel_')
        temp_mixed = tempfile.mktemp(suffix='_mixed.mp4', prefix='reel_')

        try:
            # Assemble segments
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

            # Mix audio
            def mix_progress(p):
                if progress_callback:
                    progress_callback(40 + int(p * 0.20))

            logger.info("Mixing audio...")
            mix_audio(
                temp_assembled,
                str(self.edit_session.music_track.file_path),
                temp_mixed,
                video_volume=0.3,
                music_volume=0.7,
                trim_start_ms=0,
                trim_end_ms=None,
                progress_callback=mix_progress
            )

            # Export for Instagram (default)
            def export_progress(p):
                if progress_callback:
                    progress_callback(60 + int(p * 0.40))

            logger.info("Exporting final video...")
            export_for_instagram(temp_mixed, output_path, progress_callback=export_progress)

            logger.info(f"Reel complete: {output_path}")
            return output_path

        finally:
            for temp_file in [temp_assembled, temp_mixed]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

    @Slot(str)
    def _on_reel_complete(self, output_path: str) -> None:
        """Handle reel generation complete."""
        self.show_status(f"Reel saved to: {Path(output_path).name}")
        self.analyze_btn.setEnabled(True)

    @Slot(str)
    def _on_reel_error(self, error: str) -> None:
        """Handle reel generation error."""
        self.show_error(error)
        self.analyze_btn.setEnabled(True)

    def start_background_task(self, worker: Worker) -> None:
        """Start a worker in the thread pool."""
        worker.signals.progress.connect(self.update_progress)
        worker.signals.status.connect(self.show_status)
        worker.signals.error.connect(self.show_error)
        worker.signals.finished.connect(self.on_task_finished)
        self.threadpool.start(worker)

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


def main() -> int:
    """Application entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
