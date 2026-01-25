"""Timeline widget with timestamp marking for video editing.

Provides visual timeline with clickable markers for goal moment
and celebration start timestamps.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from PySide6.QtCore import Qt, Signal, Slot, QPointF
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
)
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF

logger = logging.getLogger(__name__)


class TimelineMarkerDisplay(QFrame):
    """Visual display of timeline with markers.

    Shows a horizontal bar representing video duration with
    colored markers for goal and celebration timestamps.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(40)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)

        # Marker positions (0.0 to 1.0 as fraction of duration)
        self._duration_ms: int = 0
        self._goal_position: Optional[float] = None  # 0.0-1.0
        self._celebration_position: Optional[float] = None  # 0.0-1.0
        self._current_position: float = 0.0  # 0.0-1.0

        # Beat markers
        self._beat_positions: list[float] = []  # 0.0-1.0 fractions
        self._beat_intensities: list[float] = []  # 0.0-1.0 intensities

    def set_duration(self, duration_ms: int) -> None:
        """Set total video duration in milliseconds."""
        self._duration_ms = duration_ms
        self.update()

    def set_goal_marker(self, position_ms: Optional[int]) -> None:
        """Set goal marker position."""
        if position_ms is not None and self._duration_ms > 0:
            self._goal_position = position_ms / self._duration_ms
        else:
            self._goal_position = None
        self.update()

    def set_celebration_marker(self, position_ms: Optional[int]) -> None:
        """Set celebration marker position."""
        if position_ms is not None and self._duration_ms > 0:
            self._celebration_position = position_ms / self._duration_ms
        else:
            self._celebration_position = None
        self.update()

    def set_current_position(self, position_ms: int) -> None:
        """Set current playback position."""
        if self._duration_ms > 0:
            self._current_position = position_ms / self._duration_ms
        else:
            self._current_position = 0.0
        self.update()

    def set_beat_markers(
        self, beat_times_sec: np.ndarray, intensities: np.ndarray, duration_sec: float
    ) -> None:
        """Set beat markers from detection results.

        Args:
            beat_times_sec: Array of beat times in seconds
            intensities: Array of beat intensities (0-1)
            duration_sec: Total music duration for position calculation
        """
        if duration_sec > 0:
            self._beat_positions = (beat_times_sec / duration_sec).tolist()
            self._beat_intensities = intensities.tolist()
        else:
            self._beat_positions = []
            self._beat_intensities = []
        self.update()

    def clear_beat_markers(self) -> None:
        """Remove all beat markers."""
        self._beat_positions = []
        self._beat_intensities = []
        self.update()

    def paintEvent(self, event) -> None:
        """Draw timeline bar with markers."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Timeline dimensions
        margin = 10
        bar_height = 12
        bar_y = (self.height() - bar_height) // 2
        bar_width = self.width() - 2 * margin

        # Draw timeline background
        painter.fillRect(margin, bar_y, bar_width, bar_height, QColor("#e0e0e0"))

        # Draw current position indicator
        if self._duration_ms > 0:
            pos_x = margin + int(self._current_position * bar_width)
            painter.setPen(QPen(QColor("#333333"), 2))
            painter.drawLine(pos_x, bar_y - 5, pos_x, bar_y + bar_height + 5)

        # Draw goal marker (green triangle)
        if self._goal_position is not None:
            goal_x = margin + int(self._goal_position * bar_width)
            painter.setBrush(QColor("#4CAF50"))  # Green
            painter.setPen(Qt.PenStyle.NoPen)
            # Triangle pointing down
            painter.drawPolygon([
                (goal_x - 6, bar_y - 2),
                (goal_x + 6, bar_y - 2),
                (goal_x, bar_y + 8),
            ])

        # Draw celebration marker (orange triangle)
        if self._celebration_position is not None:
            celeb_x = margin + int(self._celebration_position * bar_width)
            painter.setBrush(QColor("#FF9800"))  # Orange
            painter.setPen(Qt.PenStyle.NoPen)
            # Triangle pointing down
            painter.drawPolygon([
                (celeb_x - 6, bar_y - 2),
                (celeb_x + 6, bar_y - 2),
                (celeb_x, bar_y + 8),
            ])

        # Draw beat markers BELOW timeline bar
        for i, pos in enumerate(self._beat_positions):
            beat_x = margin + int(pos * bar_width)
            intensity = (
                self._beat_intensities[i]
                if i < len(self._beat_intensities)
                else 0.5
            )

            # Visual differentiation: strong beats (>0.7) are larger diamonds
            # weak beats (<=0.7) are smaller dots
            if intensity > 0.7:
                # Strong beat: diamond shape, blue color
                size = 6
                painter.setBrush(QColor(66, 133, 244, int(200 * intensity)))  # Blue
                painter.setPen(Qt.PenStyle.NoPen)
                # Diamond shape using QPolygonF
                diamond = QPolygonF([
                    QPointF(beat_x, bar_y + bar_height + 2),
                    QPointF(beat_x - size // 2, bar_y + bar_height + size + 2),
                    QPointF(beat_x, bar_y + bar_height + size * 2 + 2),
                    QPointF(beat_x + size // 2, bar_y + bar_height + size + 2),
                ])
                painter.drawPolygon(diamond)
            else:
                # Weak beat: small dot, lighter blue
                size = 3
                painter.setBrush(QColor(66, 133, 244, int(120 * intensity)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(
                    int(beat_x - size // 2),
                    bar_y + bar_height + 4,
                    size,
                    size,
                )

        painter.end()


class TimelineWidget(QWidget):
    """Timeline widget with timestamp marking controls.

    Provides buttons to mark goal and celebration timestamps,
    with visual feedback showing marker positions.

    Signals:
        goal_marked: Emitted with position_ms when goal marked
        celebration_marked: Emitted with position_ms when celebration marked
        markers_cleared: Emitted when markers are reset
    """

    goal_marked = Signal(int)  # position_ms
    celebration_marked = Signal(int)  # position_ms
    markers_cleared = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_position_ms: int = 0
        self._duration_ms: int = 0
        self._goal_ms: Optional[int] = None
        self._celebration_ms: Optional[int] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure timeline UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(10)

        # Marker display
        self.marker_display = TimelineMarkerDisplay()
        layout.addWidget(self.marker_display)

        # Control buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # Mark Goal button
        self.mark_goal_btn = QPushButton("Mark Goal")
        self.mark_goal_btn.setEnabled(False)
        self.mark_goal_btn.clicked.connect(self._on_mark_goal)
        self.mark_goal_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        buttons_layout.addWidget(self.mark_goal_btn)

        # Goal timestamp display
        self.goal_label = QLabel("Goal: --:--")
        self.goal_label.setStyleSheet("font-size: 12px; color: #4CAF50; min-width: 80px;")
        buttons_layout.addWidget(self.goal_label)

        buttons_layout.addStretch()

        # Mark Celebration button
        self.mark_celeb_btn = QPushButton("Mark Celebration")
        self.mark_celeb_btn.setEnabled(False)
        self.mark_celeb_btn.clicked.connect(self._on_mark_celebration)
        self.mark_celeb_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-size: 13px;
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #f57c00; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        buttons_layout.addWidget(self.mark_celeb_btn)

        # Celebration timestamp display
        self.celeb_label = QLabel("Celebration: --:--")
        self.celeb_label.setStyleSheet("font-size: 12px; color: #FF9800; min-width: 100px;")
        buttons_layout.addWidget(self.celeb_label)

        buttons_layout.addStretch()

        # Clear markers button
        self.clear_btn = QPushButton("Clear Markers")
        self.clear_btn.clicked.connect(self._on_clear_markers)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 12px;
                font-size: 12px;
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        buttons_layout.addWidget(self.clear_btn)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable marking buttons."""
        self.mark_goal_btn.setEnabled(enabled)
        self.mark_celeb_btn.setEnabled(enabled)

    def set_duration(self, duration_ms: int) -> None:
        """Set video duration for marker display."""
        self._duration_ms = duration_ms
        self.marker_display.set_duration(duration_ms)

    @Slot(int)
    def update_position(self, position_ms: int) -> None:
        """Update current playback position."""
        self._current_position_ms = position_ms
        self.marker_display.set_current_position(position_ms)

    @Slot()
    def _on_mark_goal(self) -> None:
        """Handle mark goal button click."""
        self._goal_ms = self._current_position_ms
        self.marker_display.set_goal_marker(self._goal_ms)
        self.goal_label.setText(f"Goal: {self._format_time(self._goal_ms)}")
        self.goal_marked.emit(self._goal_ms)
        logger.info(f"Goal marked at {self._goal_ms}ms")

    @Slot()
    def _on_mark_celebration(self) -> None:
        """Handle mark celebration button click."""
        self._celebration_ms = self._current_position_ms
        self.marker_display.set_celebration_marker(self._celebration_ms)
        self.celeb_label.setText(f"Celebration: {self._format_time(self._celebration_ms)}")
        self.celebration_marked.emit(self._celebration_ms)
        logger.info(f"Celebration marked at {self._celebration_ms}ms")

    @Slot()
    def _on_clear_markers(self) -> None:
        """Handle clear markers button click."""
        self._goal_ms = None
        self._celebration_ms = None
        self.marker_display.set_goal_marker(None)
        self.marker_display.set_celebration_marker(None)
        self.goal_label.setText("Goal: --:--")
        self.celeb_label.setText("Celebration: --:--")
        self.markers_cleared.emit()
        logger.info("Markers cleared")

    def get_goal_timestamp(self) -> Optional[int]:
        """Get marked goal timestamp in milliseconds."""
        return self._goal_ms

    def get_celebration_timestamp(self) -> Optional[int]:
        """Get marked celebration timestamp in milliseconds."""
        return self._celebration_ms

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        """Format milliseconds as MM:SS."""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


__all__ = ['TimelineWidget', 'TimelineMarkerDisplay']
