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
    """Waveform visualization widget with beat markers overlay and editing."""

    # Signals for beat editing
    beat_removed = Signal(int)  # Index of removed beat
    beat_added = Signal(float)  # Time in seconds of added beat
    trim_changed = Signal(float, float)  # (start_sec, end_sec)

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

        # Beat editing state
        self._editable = True
        self._hover_beat_idx: Optional[int] = None  # Beat under mouse

        # Trim handle state
        self._trim_handle_size = 8
        self._dragging_trim_start = False
        self._dragging_trim_end = False

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

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

        # Highlight hovered beat
        if self._hover_beat_idx is not None and self._beats is not None:
            beat_time = self._beats[self._hover_beat_idx]
            x = int((beat_time / self._duration_sec) * width)
            painter.setPen(QPen(QColor(255, 255, 0), 2))  # Yellow highlight
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(x - 5, height - 35, 10, 30)

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

        # 5. Draw trim handles
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.setPen(Qt.PenStyle.NoPen)

        # Start trim handle
        trim_start_x = int((self._trim_start_sec / self._duration_sec) * width) if self._duration_sec > 0 else 0
        painter.drawRect(trim_start_x - 4, 0, 8, height)

        # End trim handle
        trim_end = self._trim_end_sec if self._trim_end_sec else self._duration_sec
        trim_end_x = int((trim_end / self._duration_sec) * width) if self._duration_sec > 0 else width
        painter.drawRect(trim_end_x - 4, 0, 8, height)

        painter.end()

    def mousePressEvent(self, event) -> None:
        """Handle mouse click for beat removal or trim drag start."""
        if not self._editable or self._duration_sec <= 0:
            return

        x = event.position().x()
        y = event.position().y()
        width = self.width()
        height = self.height()

        # Check if clicking on trim handles (at edges)
        if x <= self._trim_handle_size * 2:
            # Near start - check if on trim handle
            trim_x = int((self._trim_start_sec / self._duration_sec) * width) if self._duration_sec > 0 else 0
            if abs(x - trim_x) < self._trim_handle_size:
                self._dragging_trim_start = True
                return

        if x >= width - self._trim_handle_size * 2:
            # Near end - check if on trim handle
            trim_end = self._trim_end_sec if self._trim_end_sec else self._duration_sec
            trim_x = int((trim_end / self._duration_sec) * width) if self._duration_sec > 0 else width
            if abs(x - trim_x) < self._trim_handle_size:
                self._dragging_trim_end = True
                return

        # Left click on beat marker = remove beat
        if event.button() == Qt.MouseButton.LeftButton and self._hover_beat_idx is not None:
            self.beat_removed.emit(self._hover_beat_idx)
            return

        # Right click = add beat at position
        if event.button() == Qt.MouseButton.RightButton:
            click_time_sec = (x / width) * self._duration_sec
            self.beat_added.emit(click_time_sec)

    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for hover detection and trim dragging."""
        if self._duration_sec <= 0:
            return

        x = event.position().x()
        width = self.width()

        # Handle trim dragging
        if self._dragging_trim_start:
            new_trim = max(0, (x / width) * self._duration_sec)
            self._trim_start_sec = new_trim
            self.trim_changed.emit(self._trim_start_sec, self._trim_end_sec or self._duration_sec)
            self.update()
            return

        if self._dragging_trim_end:
            new_trim = min(self._duration_sec, (x / width) * self._duration_sec)
            self._trim_end_sec = new_trim
            self.trim_changed.emit(self._trim_start_sec, self._trim_end_sec)
            self.update()
            return

        # Detect hover over beat marker
        old_hover = self._hover_beat_idx
        self._hover_beat_idx = None

        if self._beats is not None:
            for i, beat_time in enumerate(self._beats):
                beat_x = int((beat_time / self._duration_sec) * width)
                if abs(x - beat_x) < 8:  # 8px hit zone
                    self._hover_beat_idx = i
                    break

        if old_hover != self._hover_beat_idx:
            self.update()  # Redraw for hover highlight

        # Update cursor based on position
        self._update_cursor(x)

    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release for trim drag end."""
        self._dragging_trim_start = False
        self._dragging_trim_end = False

    def _update_cursor(self, x: int) -> None:
        """Update cursor based on position."""
        width = self.width()

        # Check trim handles
        trim_start_x = int((self._trim_start_sec / self._duration_sec) * width) if self._duration_sec > 0 else 0
        trim_end = self._trim_end_sec if self._trim_end_sec else self._duration_sec
        trim_end_x = int((trim_end / self._duration_sec) * width) if self._duration_sec > 0 else width

        if abs(x - trim_start_x) < self._trim_handle_size or abs(x - trim_end_x) < self._trim_handle_size:
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self._hover_beat_idx is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)


class MusicPanel(QWidget):
    """Music controls panel with waveform display.

    Signals:
        music_loaded: Emitted when music file loaded (path, duration_ms)
        beats_detected: Emitted when detection complete (beats, intensities)
        beats_changed: Emitted when beats manually edited (beats, intensities)
        volume_changed: float (0.0-1.0)
        trim_changed: (start_ms, end_ms)
        playback_requested: bool (True=play, False=pause)
    """

    music_loaded = Signal(str, int)  # path, duration_ms
    beats_detected = Signal(object, object)  # beats, intensities
    beats_changed = Signal(object, object)  # beats, intensities (after manual editing)
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

        # Connect WaveformDisplay beat editing signals
        self._waveform_display.beat_removed.connect(self._on_beat_removed)
        self._waveform_display.beat_added.connect(self._on_beat_added)
        self._waveform_display.trim_changed.connect(self._on_trim_changed)

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

    def load_music(self, file_path: str) -> None:
        """Public method to load music file.

        Args:
            file_path: Path to audio file (mp3, wav, m4a, aac)
        """
        self._load_music_file(file_path)

    def set_beats(self, beats: np.ndarray, intensities: np.ndarray) -> None:
        """Set beat markers on waveform display."""
        self._waveform_display.set_beats(beats, intensities)
        self.beats_detected.emit(beats, intensities)
        logger.info(f"Beat markers set: {len(beats)} beats")

    @Slot(int)
    def _on_beat_removed(self, beat_idx: int) -> None:
        """Remove beat at index from internal array."""
        if self._waveform_display._beats is not None and 0 <= beat_idx < len(self._waveform_display._beats):
            # Remove from array
            self._waveform_display._beats = np.delete(self._waveform_display._beats, beat_idx)
            if self._waveform_display._beat_intensities is not None:
                self._waveform_display._beat_intensities = np.delete(
                    self._waveform_display._beat_intensities, beat_idx
                )
            self._waveform_display.update()
            # Emit signal for MainWindow to update EditSession and timeline
            self.beats_changed.emit(self._waveform_display._beats, self._waveform_display._beat_intensities)
            logger.info(f"Beat removed at index {beat_idx}, {len(self._waveform_display._beats)} beats remaining")

    @Slot(float)
    def _on_beat_added(self, time_sec: float) -> None:
        """Add beat at specified time."""
        if self._waveform_display._beats is not None:
            # Insert beat in sorted order
            insert_idx = np.searchsorted(self._waveform_display._beats, time_sec)
            self._waveform_display._beats = np.insert(self._waveform_display._beats, insert_idx, time_sec)
            # Default intensity 0.5 for manually added beats
            if self._waveform_display._beat_intensities is not None:
                self._waveform_display._beat_intensities = np.insert(
                    self._waveform_display._beat_intensities, insert_idx, 0.5
                )
            self._waveform_display.update()
            self.beats_changed.emit(self._waveform_display._beats, self._waveform_display._beat_intensities)
            logger.info(f"Beat added at {time_sec:.2f}s, {len(self._waveform_display._beats)} beats total")

    @Slot(float, float)
    def _on_trim_changed(self, start_sec: float, end_sec: float) -> None:
        """Handle trim region change."""
        self.trim_changed.emit(int(start_sec * 1000), int(end_sec * 1000))
        logger.info(f"Trim changed: {start_sec:.2f}s - {end_sec:.2f}s")


__all__ = ['MusicPanel', 'WaveformDisplay']
