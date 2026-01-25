"""Edit session data model.

Stores all editing state: timestamps, slow-motion settings, color grading.
Acts as the central data structure passed between GUI and processing modules.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SlowMotionSettings:
    """Slow-motion effect configuration.

    Attributes:
        speed: Playback speed multiplier (0.25, 0.5, 0.75, 1.0)
        start_ms: Start time of slow-motion segment in milliseconds
        duration_ms: Duration of slow-motion segment in milliseconds
    """
    speed: float = 0.5
    start_ms: int = 0
    duration_ms: int = 3000  # 3 seconds default

    def validate(self) -> bool:
        """Validate settings are within allowed ranges.

        Returns:
            True if speed is in allowed values and duration is positive
        """
        return self.speed in (0.25, 0.5, 0.75, 1.0) and self.duration_ms > 0


@dataclass
class ColorGradingSettings:
    """Color grading configuration.

    Attributes:
        lut_name: Display name of selected LUT preset (e.g., "Cinematic Warm")
        lut_path: Absolute path to .cube LUT file
    """
    lut_name: Optional[str] = None
    lut_path: Optional[Path] = None

    def is_enabled(self) -> bool:
        """Check if color grading is enabled.

        Returns:
            True if both name and path are set
        """
        return self.lut_name is not None and self.lut_path is not None


@dataclass
class EditSession:
    """Complete editing session state.

    Stores all information needed for preview generation and final export:
    - Source and proxy video paths
    - User-marked timestamps (goal moment, celebration start)
    - Effects settings (slow-motion, color grading)

    Attributes:
        source_path: Path to original source video file
        proxy_path: Path to generated proxy video file
        goal_moment_ms: Timestamp of goal/highlight moment (milliseconds)
        celebration_start_ms: Timestamp when celebration begins (milliseconds)
        slow_motion: Slow-motion effect settings
        color_grading: Color grading/LUT settings
    """
    source_path: Optional[Path] = None
    proxy_path: Optional[Path] = None
    goal_moment_ms: Optional[int] = None
    celebration_start_ms: Optional[int] = None
    slow_motion: SlowMotionSettings = field(default_factory=SlowMotionSettings)
    color_grading: ColorGradingSettings = field(default_factory=ColorGradingSettings)

    def is_ready_for_preview(self) -> bool:
        """Check if session has minimum data for preview generation.

        Returns:
            True if proxy path exists and goal moment is marked
        """
        return (
            self.proxy_path is not None and
            self.goal_moment_ms is not None
        )

    def is_ready_for_export(self) -> bool:
        """Check if session has all data for final export.

        Returns:
            True if source path exists and both timestamps are marked
        """
        return (
            self.source_path is not None and
            self.goal_moment_ms is not None and
            self.celebration_start_ms is not None
        )

    def reset_timestamps(self) -> None:
        """Clear all timestamp markers."""
        self.goal_moment_ms = None
        self.celebration_start_ms = None

    def reset_effects(self) -> None:
        """Reset all effects to defaults."""
        self.slow_motion = SlowMotionSettings()
        self.color_grading = ColorGradingSettings()
