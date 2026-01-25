"""Edit session data model.

Stores all editing state: timestamps, slow-motion settings, color grading.
Acts as the central data structure passed between GUI and processing modules.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np


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
class MusicTrack:
    """Music track with beat detection results.

    Attributes:
        file_path: Path to music file (MP3 or WAV)
        duration_ms: Total duration in milliseconds
        sample_rate: Audio sample rate used during detection (typically 22050 or 44100)
        hop_length: Hop length used for onset detection (typically 512)
        beats: Array of beat times in seconds (from librosa)
        onset_envelope: Onset strength values for intensity visualization
        tempo: Detected BPM (float)
        trim_start_ms: User-selected start point for music trim
        trim_end_ms: User-selected end point for music trim
        volume: Playback volume 0.0-1.0 (relative to video audio)
    """
    file_path: Optional[Path] = None
    duration_ms: int = 0
    sample_rate: int = 22050  # From librosa detection, used for intensity calculation
    hop_length: int = 512     # From librosa detection, used for intensity calculation
    beats: Optional[np.ndarray] = None  # Beat times in seconds
    onset_envelope: Optional[np.ndarray] = None
    tempo: float = 0.0
    trim_start_ms: int = 0
    trim_end_ms: Optional[int] = None  # None = full duration
    volume: float = 0.7  # Default 70% music volume

    def get_beat_intensity(self, beat_index: int) -> float:
        """Get normalized intensity (0-1) for a beat.

        Uses stored sample_rate and hop_length to correctly map
        beat time to onset envelope frame.
        """
        if self.beats is None or self.onset_envelope is None:
            return 0.5
        if beat_index < 0 or beat_index >= len(self.beats):
            return 0.5
        beat_time = self.beats[beat_index]
        frame = int(beat_time * self.sample_rate / self.hop_length)
        if 0 <= frame < len(self.onset_envelope):
            return float(self.onset_envelope[frame])
        return 0.5

    def get_trimmed_beats(self) -> np.ndarray:
        """Get beats within trim region only."""
        if self.beats is None:
            return np.array([])
        trim_start_sec = self.trim_start_ms / 1000.0
        trim_end_sec = (self.trim_end_ms / 1000.0) if self.trim_end_ms else float('inf')
        mask = (self.beats >= trim_start_sec) & (self.beats <= trim_end_sec)
        return self.beats[mask]


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
    music_track: MusicTrack = field(default_factory=MusicTrack)

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
