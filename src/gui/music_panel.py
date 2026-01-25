"""Music control panel for audio import, playback, and waveform visualization.

Provides UI for music file import (drag-drop), playback controls, volume adjustment,
and waveform display with beat marker overlay.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import librosa
from PySide6.QtCore import Qt, Signal, Slot, QUrl
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSlider,
)
from PySide6.QtGui import QPainter, QColor, QPen, QDragEnterEvent, QDropEvent

from ..audio import MusicPlayer, WaveformCache

logger = logging.getLogger(__name__)


class WaveformDisplay(QWidget):
    """Waveform visualization widget with beat markers overlay."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._waveform_cache: Optional[WaveformCache] = None
        self._beats: Optional[np.ndarray] = None
        self._beat_intensities: Optional[np.ndarray] = None
        self._duration_sec: float = 0.0
        self._current_position_sec: float = 0.0
        self._trim_start_sec: float = 0.0
        self._trim_end_sec: Optional[float] = None

    def set_waveform(self, cache: WaveformCache, duration_sec: float) -> None:
        """Set waveform data for rendering."""
        self._waveform_cache = cache
        self._duration_sec = duration_sec
        self.update()

    def set_beats(self, beats: np.ndarray, intensities: np.ndarray) -> None:
        """Set beat positions and intensities for overlay."""
        self._beats = beats
        self._beat_intensities = intensities
        self.update()

    def paintEvent(self, event) -> None:
        """Draw waveform and beat markers using QPainter batch operations."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        mid_y = height // 2

        # Background
        painter.fillRect(0, 0, width, height, QColor(30, 30, 30))

        # 1. Draw waveform from cache
        if self._waveform_cache is not None and self._duration_sec > 0:
            min_peaks, max_peaks = self._waveform_cache.get_peaks(
                0.0, self._duration_sec, width
            )

            # Batch draw waveform lines for performance
            painter.setPen(QPen(QColor(100, 200, 100), 1))
            from PySide6.QtCore import QLine

            lines = []
            for i in range(len(min_peaks)):
                y_min = int(mid_y + min_peaks[i] * (height // 2 - 5))
                y_max = int(mid_y + max_peaks[i] * (height // 2 - 5))
                lines.append(QLine(i, y_min, i, y_max))

            # Draw all lines in batch
            painter.drawLines(lines)

        # 2. Draw beat markers
        if self._beats is not None and self._duration_sec > 0:
            for i, beat_time in enumerate(self._beats):
                x = int((beat_time / self._duration_sec) * width)
                intensity = (
                    self._beat_intensities[i]
                    if self._beat_intensities is not None
                    and i < len(self._beat_intensities)
                    else 0.5
                )

                # Stronger beats are taller lines
                line_height = int(10 + intensity * 20)
                alpha = int(100 + intensity * 155)
                painter.setPen(QPen(QColor(66, 133, 244, alpha), 2))
                painter.drawLine(x, height - line_height, x, height)

        # 3. Draw position indicator
        if self._duration_sec > 0 and self._current_position_sec > 0:
            pos_x = int((self._current_position_sec / self._duration_sec) * width)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(pos_x, 0, pos_x, height)

        # 4. Draw trim region highlighting (dimmed outside trim)
        if self._trim_start_sec > 0 or (
            self._trim_end_sec is not None
            and self._trim_end_sec < self._duration_sec
        ):
            dim_color = QColor(0, 0, 0, 128)
            if self._trim_start_sec > 0:
                trim_x = int((self._trim_start_sec / self._duration_sec) * width)
                painter.fillRect(0, 0, trim_x, height, dim_color)
            if self._trim_end_sec is not None and self._duration_sec > 0:
                trim_end_x = int((self._trim_end_sec / self._duration_sec) * width)
                painter.fillRect(trim_end_x, 0, width - trim_end_x, height, dim_color)

        painter.end()


class MusicPanel(QWidget):
    """Music controls panel with waveform display.

    Signals:
        music_loaded: Emitted when music file loaded (path, duration_ms)
        beats_detected: Emitted when detection complete (beats, intensities)
        volume_changed: float (0.0-1.0)
        trim_changed: (start_ms, end_ms)
        playback_requested: bool (True=play, False=pause)
    """

    music_loaded = Signal(str, int)  # path, duration_ms
    beats_detected = Signal(object, object)  # beats, intensities
    volume_changed = Signal(float)
    trim_changed = Signal(int, int)
    playback_requested = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)  # Enable drag-drop

        # Create MusicPlayer instance
        self._player = MusicPlayer()
        self._waveform_cache: Optional[WaveformCache] = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Build the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Waveform display
        self._waveform_display = WaveformDisplay()
        layout.addWidget(self._waveform_display)

        # Controls row
        controls = QHBoxLayout()

        # Play/Pause button
        self._play_btn = QPushButton("Play")
        self._play_btn.setFixedWidth(60)
        self._play_btn.clicked.connect(self._toggle_playback)
        self._play_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 10px;
                font-size: 13px;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        controls.addWidget(self._play_btn)

        # Volume slider
        controls.addWidget(QLabel("Vol:"))
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(70)
        self._volume_slider.setFixedWidth(100)
        self._volume_slider.valueChanged.connect(self._on_volume_changed)
        self._volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #cccccc;
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #4a90e2;
                border: 1px solid #357abd;
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        controls.addWidget(self._volume_slider)

        # Position label
        self._position_label = QLabel("00:00 / 00:00")
        self._position_label.setStyleSheet("font-size: 12px; min-width: 80px;")
        controls.addWidget(self._position_label)

        controls.addStretch()

        # Drop hint (shown when no music loaded)
        self._drop_hint = QLabel("Drop MP3 or WAV file here")
        self._drop_hint.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
        controls.addWidget(self._drop_hint)

        layout.addLayout(controls)

    def _connect_signals(self) -> None:
        """Wire up internal signals."""
        # Connect MusicPlayer signals
        self._player.position_changed.connect(self._on_position_changed)
        self._player.duration_changed.connect(self._on_duration_changed)
        self._player.playback_state_changed.connect(self._on_playback_state_changed)

    def _toggle_playback(self) -> None:
        """Toggle play/pause state."""
        if self._player.is_playing():
            self._player.pause()
            self.playback_requested.emit(False)
        else:
            self._player.play()
            self.playback_requested.emit(True)

    @Slot(int)
    def _on_volume_changed(self, value: int) -> None:
        """Handle volume slider change."""
        volume = value / 100.0
        self._player.set_volume(volume)
        self.volume_changed.emit(volume)

    @Slot(int)
    def _on_position_changed(self, position_ms: int) -> None:
        """Update position display."""
        duration_ms = self._player.get_duration_ms()
        pos_str = self._format_time(position_ms)
        dur_str = self._format_time(duration_ms)
        self._position_label.setText(f"{pos_str} / {dur_str}")

        # Update waveform position indicator
        if duration_ms > 0:
            self._waveform_display._current_position_sec = position_ms / 1000.0
            self._waveform_display.update()

    @Slot(int)
    def _on_duration_changed(self, duration_ms: int) -> None:
        """Handle duration becoming available."""
        pos_str = self._format_time(0)
        dur_str = self._format_time(duration_ms)
        self._position_label.setText(f"{pos_str} / {dur_str}")

    @Slot(object)
    def _on_playback_state_changed(self, state) -> None:
        """Update play button text based on state."""
        from PySide6.QtMultimedia import QMediaPlayer

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_btn.setText("Pause")
        else:
            self._play_btn.setText("Play")

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = ms // 1000
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    # ===== DRAG-DROP HANDLING =====

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag if it contains audio files."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if path.endswith('.mp3') or path.endswith('.wav'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle dropped audio file."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp3', '.wav')):
                self._load_music_file(file_path)
                event.acceptProposedAction()
                return
        event.ignore()

    def _load_music_file(self, file_path: str) -> None:
        """Load music file, create waveform cache, emit signal."""
        try:
            # Load audio with librosa for waveform visualization
            y, sr = librosa.load(file_path, sr=None, mono=True)
            duration_sec = len(y) / sr
            duration_ms = int(duration_sec * 1000)

            # Create waveform cache
            self._waveform_cache = WaveformCache(y, sr)
            self._waveform_display.set_waveform(self._waveform_cache, duration_sec)

            # Load into player for playback
            self._player.load(file_path)

            # Hide drop hint
            self._drop_hint.hide()

            # Emit signal for MainWindow to start beat detection
            self.music_loaded.emit(file_path, duration_ms)

            logger.info(f"Music loaded: {file_path} ({duration_sec:.2f}s)")

        except Exception as e:
            # Show error in drop hint area
            error_msg = f"Error: {str(e)}"
            self._drop_hint.setText(error_msg)
            self._drop_hint.setStyleSheet("color: #f44; font-style: italic; font-size: 12px;")
            logger.error(f"Failed to load music: {e}")

    def set_beats(self, beats: np.ndarray, intensities: np.ndarray) -> None:
        """Set beat markers on waveform display."""
        self._waveform_display.set_beats(beats, intensities)
        self.beats_detected.emit(beats, intensities)
        logger.info(f"Beat markers set: {len(beats)} beats")


__all__ = ['MusicPanel', 'WaveformDisplay']
