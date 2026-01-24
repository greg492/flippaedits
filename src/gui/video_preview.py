"""Video preview widget with playback controls and scrubbing.

Provides a video player with seek slider for smooth navigation through
proxy files without lag.
"""

from pathlib import Path
from typing import Union, Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QPushButton,
    QLabel,
)


class VideoPreviewWidget(QWidget):
    """Video preview widget with playback controls and scrubbing.

    Provides smooth video playback using proxy files with:
    - Play/pause control
    - Seek slider for scrubbing through video
    - Time display showing current position and duration
    - Automatic aspect ratio handling (16:9 horizontal, 9:16 vertical)

    Signals:
        video_loaded: Emitted when video is loaded and ready to play
        position_changed: Emitted with current position in seconds (float)
    """

    video_loaded = Signal()
    position_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize video preview widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._is_seeking = False  # Track slider dragging to prevent feedback loops
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure video player and controls."""
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Video display widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        self.video_widget.setStyleSheet("""
            QVideoWidget {
                background-color: #000000;
            }
        """)
        layout.addWidget(self.video_widget, stretch=1)

        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect player signals
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)

        # Controls layout
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)

        # Play/pause button
        self.play_button = QPushButton("Play")
        self.play_button.setEnabled(False)
        self.play_button.setMinimumWidth(80)
        self.play_button.clicked.connect(self._toggle_play_pause)
        self.play_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 14px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        controls_layout.addWidget(self.play_button)

        # Seek slider
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setEnabled(False)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #357abd;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #357abd;
            }
            QSlider::sub-page:horizontal {
                background: #4a90e2;
                border-radius: 4px;
            }
        """)
        controls_layout.addWidget(self.seek_slider, stretch=1)

        # Time display
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMinimumWidth(120)
        self.time_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #333333;
                padding: 0 10px;
            }
        """)
        controls_layout.addWidget(self.time_label)

        layout.addLayout(controls_layout)

        # Status label (for loading state)
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666666;
                padding: 5px;
            }
        """)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def load_video(self, path: Union[str, Path]) -> None:
        """Load video file into player.

        Args:
            path: Path to video file (usually proxy file for smooth playback)

        Examples:
            >>> widget = VideoPreviewWidget()
            >>> widget.load_video("proxy_720p.mp4")
        """
        from PySide6.QtCore import QUrl

        path = Path(path)
        if not path.exists():
            self.status_label.setText(f"Error: File not found - {path.name}")
            return

        # Load media
        url = QUrl.fromLocalFile(str(path.resolve()))
        self.media_player.setSource(url)
        self.status_label.setText("Loading...")

    @Slot()
    def _toggle_play_pause(self) -> None:
        """Toggle between play and pause states."""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_button.setText("Play")
        else:
            self.media_player.play()
            self.play_button.setText("Pause")

    @Slot(int)
    def _on_position_changed(self, position: int) -> None:
        """Handle player position change.

        Args:
            position: Current position in milliseconds
        """
        # Update slider (only if not currently dragging)
        if not self._is_seeking:
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(position)
            self.seek_slider.blockSignals(False)

        # Update time display
        self._update_time_display(position, self.media_player.duration())

        # Emit position in seconds
        self.position_changed.emit(position / 1000.0)

    @Slot(int)
    def _on_duration_changed(self, duration: int) -> None:
        """Handle duration change when media loads.

        Args:
            duration: Total duration in milliseconds
        """
        self.seek_slider.setRange(0, duration)
        self._update_time_display(self.media_player.position(), duration)

    @Slot()
    def _on_media_status_changed(self, status) -> None:
        """Handle media status changes.

        Args:
            status: QMediaPlayer.MediaStatus enum value
        """
        if status == QMediaPlayer.MediaStatus.LoadedMedia:
            # Media loaded successfully
            self.status_label.setText("")
            self.play_button.setEnabled(True)
            self.seek_slider.setEnabled(True)
            self.video_loaded.emit()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            # Failed to load media
            self.status_label.setText("Error: Cannot load video")
            self.play_button.setEnabled(False)
            self.seek_slider.setEnabled(False)
        elif status == QMediaPlayer.MediaStatus.LoadingMedia:
            # Currently loading
            self.status_label.setText("Loading...")

    @Slot()
    def _on_slider_pressed(self) -> None:
        """Handle slider press (start seeking)."""
        self._is_seeking = True

    @Slot()
    def _on_slider_released(self) -> None:
        """Handle slider release (finish seeking)."""
        self._is_seeking = False
        # Seek to slider position
        self.media_player.setPosition(self.seek_slider.value())

    @Slot(int)
    def _on_slider_moved(self, position: int) -> None:
        """Handle slider movement during drag.

        Args:
            position: Slider position in milliseconds
        """
        # Update time display during drag
        self._update_time_display(position, self.media_player.duration())

    def _update_time_display(self, position: int, duration: int) -> None:
        """Update time label with current position and duration.

        Args:
            position: Current position in milliseconds
            duration: Total duration in milliseconds
        """
        current_time = self._format_time(position)
        total_time = self._format_time(duration)
        self.time_label.setText(f"{current_time} / {total_time}")

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        """Format milliseconds as MM:SS.

        Args:
            milliseconds: Time in milliseconds

        Returns:
            Formatted time string (e.g., "02:35")

        Examples:
            >>> VideoPreviewWidget._format_time(155000)
            '02:35'
        """
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


__all__ = ['VideoPreviewWidget']
