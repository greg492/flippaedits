"""Export dialog for template selection and platform configuration."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QProgressBar, QFileDialog,
    QGroupBox, QRadioButton, QButtonGroup
)
from pathlib import Path
from typing import Optional

from ..processing.template_sequences import TEMPLATES


class ExportDialog(QDialog):
    """Dialog for export settings with template and platform selection.

    Signals:
        export_requested: Emits (template_name: str, platform: str, output_path: str)
    """

    export_requested = Signal(str, str, str)  # template, platform, output_path

    def __init__(self, parent=None, default_filename: str = "reel_export.mp4"):
        """Initialize export dialog.

        Args:
            parent: Parent widget
            default_filename: Default output filename
        """
        super().__init__(parent)
        self.default_filename = default_filename
        self.output_path: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        """Configure dialog UI."""
        self.setWindowTitle("Export Reel")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Template selection group
        template_group = QGroupBox("Template")
        template_layout = QVBoxLayout()

        self.template_combo = QComboBox()
        for key, template in TEMPLATES.items():
            self.template_combo.addItem(template.name, key)

        # Template description label
        self.template_desc = QLabel()
        self.template_desc.setWordWrap(True)
        self.template_desc.setStyleSheet("color: #666; font-size: 12px;")
        self._update_template_description()
        self.template_combo.currentIndexChanged.connect(self._update_template_description)

        template_layout.addWidget(self.template_combo)
        template_layout.addWidget(self.template_desc)
        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        # Platform selection group
        platform_group = QGroupBox("Platform")
        platform_layout = QVBoxLayout()

        self.platform_group = QButtonGroup()
        self.instagram_radio = QRadioButton("Instagram Reels (1080p, 4 Mbps)")
        self.tiktok_radio = QRadioButton("TikTok (1080p, 5 Mbps)")
        self.instagram_radio.setChecked(True)

        self.platform_group.addButton(self.instagram_radio, 0)
        self.platform_group.addButton(self.tiktok_radio, 1)

        platform_layout.addWidget(self.instagram_radio)
        platform_layout.addWidget(self.tiktok_radio)
        platform_group.setLayout(platform_layout)
        layout.addWidget(platform_group)

        # Output location
        output_group = QGroupBox("Output")
        output_layout = QHBoxLayout()

        self.output_label = QLabel("No location selected")
        self.output_label.setStyleSheet("color: #666;")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_output)

        output_layout.addWidget(self.output_label, stretch=1)
        output_layout.addWidget(self.browse_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Cancel")
        self.export_btn = QPushButton("Export")
        self.export_btn.setEnabled(False)  # Disabled until output selected

        self.cancel_btn.clicked.connect(self.reject)
        self.export_btn.clicked.connect(self._start_export)

        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.export_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _update_template_description(self):
        """Update template description when selection changes."""
        key = self.template_combo.currentData()
        if key and key in TEMPLATES:
            self.template_desc.setText(TEMPLATES[key].description)

    def _browse_output(self):
        """Open file dialog to select output location."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Location",
            str(Path.home() / "Desktop" / self.default_filename),
            "MP4 Video (*.mp4)"
        )
        if path:
            if not path.endswith('.mp4'):
                path += '.mp4'
            self.output_path = path
            self.output_label.setText(Path(path).name)
            self.export_btn.setEnabled(True)

    def _start_export(self):
        """Emit export_requested signal with current settings."""
        template_key = self.template_combo.currentData()
        platform = "instagram" if self.instagram_radio.isChecked() else "tiktok"
        self.export_requested.emit(template_key, platform, self.output_path)

    def set_progress(self, value: int):
        """Update progress bar."""
        if not self.progress_bar.isVisible():
            self.progress_bar.setVisible(True)
            self.export_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
        self.progress_bar.setValue(value)

    def set_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)

    def export_complete(self, output_path: str):
        """Handle export completion."""
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Export complete: {Path(output_path).name}")
        self.cancel_btn.setText("Close")
        self.cancel_btn.setEnabled(True)
