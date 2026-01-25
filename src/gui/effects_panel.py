"""Effects control panel for slow-motion and color grading settings.

Provides UI controls for selecting playback speed and LUT color
grading presets before preview/export.
"""

import logging
from typing import Optional

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QGroupBox,
    QPushButton,
)

from ..processing.lut_loader import load_lut_registry, LUTPreset

logger = logging.getLogger(__name__)


class EffectsPanel(QWidget):
    """Effects control panel with speed and LUT selection.

    Provides dropdowns for slow-motion speed and LUT preset selection.
    Emits signals when settings change for EditSession integration.

    Signals:
        speed_changed: Emitted with new speed value (float)
        lut_changed: Emitted with LUTPreset or None if disabled
        preview_requested: Emitted when user wants to generate preview
    """

    speed_changed = Signal(float)
    lut_changed = Signal(object)  # LUTPreset or None
    preview_requested = Signal()

    # Available speed options
    SPEED_OPTIONS = [
        ("Normal (1.0x)", 1.0),
        ("Slow (0.75x)", 0.75),
        ("Slower (0.5x)", 0.5),
        ("Slowest (0.25x)", 0.25),
    ]

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._lut_presets: list[LUTPreset] = []
        self._current_speed: float = 1.0
        self._current_lut: Optional[LUTPreset] = None
        self._setup_ui()
        self._load_lut_presets()

    def _setup_ui(self) -> None:
        """Configure effects panel UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Slow-motion group
        slowmo_group = QGroupBox("Slow Motion")
        slowmo_layout = QHBoxLayout()

        slowmo_label = QLabel("Speed:")
        slowmo_layout.addWidget(slowmo_label)

        self.speed_combo = QComboBox()
        self.speed_combo.setMinimumWidth(150)
        for label, value in self.SPEED_OPTIONS:
            self.speed_combo.addItem(label, value)
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        self.speed_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                font-size: 13px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QComboBox:hover { border-color: #4a90e2; }
        """)
        slowmo_layout.addWidget(self.speed_combo)

        slowmo_layout.addStretch()
        slowmo_group.setLayout(slowmo_layout)
        layout.addWidget(slowmo_group)

        # Color grading group
        color_group = QGroupBox("Color Grading")
        color_layout = QVBoxLayout()

        # LUT selection row
        lut_row = QHBoxLayout()

        lut_label = QLabel("LUT Preset:")
        lut_row.addWidget(lut_label)

        self.lut_combo = QComboBox()
        self.lut_combo.setMinimumWidth(200)
        self.lut_combo.addItem("None (Original)", None)
        self.lut_combo.currentIndexChanged.connect(self._on_lut_changed)
        self.lut_combo.setStyleSheet("""
            QComboBox {
                padding: 6px 10px;
                font-size: 13px;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QComboBox:hover { border-color: #4a90e2; }
        """)
        lut_row.addWidget(self.lut_combo)

        lut_row.addStretch()
        color_layout.addLayout(lut_row)

        # LUT description
        self.lut_description = QLabel("")
        self.lut_description.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #666666;
                font-style: italic;
                padding-left: 10px;
            }
        """)
        color_layout.addWidget(self.lut_description)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Preview button
        self.preview_btn = QPushButton("Generate Preview")
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._on_preview_clicked)
        self.preview_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                background-color: #4a90e2;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #357abd; }
            QPushButton:disabled { background-color: #cccccc; color: #666666; }
        """)
        layout.addWidget(self.preview_btn)

        self.setLayout(layout)

    def _load_lut_presets(self) -> None:
        """Load LUT presets from registry into dropdown."""
        try:
            self._lut_presets = load_lut_registry()
            for preset in self._lut_presets:
                self.lut_combo.addItem(preset.name, preset)
            logger.info(f"Loaded {len(self._lut_presets)} LUT presets")
        except Exception as e:
            logger.error(f"Failed to load LUT presets: {e}")
            # Keep "None" option available

    @Slot(int)
    def _on_speed_changed(self, index: int) -> None:
        """Handle speed selection change."""
        self._current_speed = self.speed_combo.currentData()
        self.speed_changed.emit(self._current_speed)
        logger.info(f"Speed changed to {self._current_speed}x")

    @Slot(int)
    def _on_lut_changed(self, index: int) -> None:
        """Handle LUT selection change."""
        self._current_lut = self.lut_combo.currentData()
        self.lut_changed.emit(self._current_lut)

        # Update description
        if self._current_lut:
            self.lut_description.setText(self._current_lut.description)
        else:
            self.lut_description.setText("")

        logger.info(f"LUT changed to {self._current_lut.name if self._current_lut else 'None'}")

    @Slot()
    def _on_preview_clicked(self) -> None:
        """Handle preview button click."""
        self.preview_requested.emit()

    def set_preview_enabled(self, enabled: bool) -> None:
        """Enable or disable preview button."""
        self.preview_btn.setEnabled(enabled)

    def get_speed(self) -> float:
        """Get current slow-motion speed."""
        return self._current_speed

    def get_lut_preset(self) -> Optional[LUTPreset]:
        """Get current LUT preset or None."""
        return self._current_lut

    def reset(self) -> None:
        """Reset effects to defaults."""
        self.speed_combo.setCurrentIndex(0)  # Normal (1.0x)
        self.lut_combo.setCurrentIndex(0)  # None


__all__ = ['EffectsPanel']
