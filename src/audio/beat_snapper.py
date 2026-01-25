"""Beat snapping for magnetic timestamp alignment.

Implements magnetic snap-to-beat functionality with strict tolerance for
professional sync quality. Only snaps timestamps within tolerance window,
otherwise preserves original timing.
"""

import numpy as np
from typing import Optional


class BeatSnapper:
    """Magnetic snap to beat points with strict tolerance.

    Implements +/-50ms snap tolerance (stricter than 100ms success criteria)
    for professional sync feel. Only snaps if timestamp is very close to beat,
    otherwise preserves original timing.

    Based on audio-video sync perception threshold of ~40-60ms (EBU R37).
    """

    def __init__(self, beat_times_sec: np.ndarray, tolerance_ms: int = 50):
        """Initialize beat snapper.

        Args:
            beat_times_sec: Array of beat times in seconds from librosa
            tolerance_ms: Snap distance in milliseconds (default 50ms)
        """
        self.beats = beat_times_sec if beat_times_sec is not None else np.array([])
        self.tolerance_sec = tolerance_ms / 1000.0

    def snap_to_beat(self, time_sec: float) -> float:
        """Return snapped time if within tolerance, original time otherwise.

        Args:
            time_sec: Input timestamp in seconds

        Returns:
            Snapped timestamp if within tolerance, otherwise original
        """
        if len(self.beats) == 0:
            return time_sec

        # Find nearest beat using numpy for efficiency
        distances = np.abs(self.beats - time_sec)
        nearest_idx = np.argmin(distances)
        nearest_beat = self.beats[nearest_idx]
        distance = distances[nearest_idx]

        # Snap only if within tolerance
        if distance <= self.tolerance_sec:
            return float(nearest_beat)
        return time_sec

    def snap_to_beat_ms(self, time_ms: int) -> int:
        """Convenience method for millisecond inputs.

        Args:
            time_ms: Input timestamp in milliseconds

        Returns:
            Snapped timestamp in milliseconds
        """
        snapped_sec = self.snap_to_beat(time_ms / 1000.0)
        return int(snapped_sec * 1000)

    def get_nearest_beat(self, time_sec: float) -> Optional[float]:
        """Get nearest beat time regardless of tolerance.

        Args:
            time_sec: Input timestamp in seconds

        Returns:
            Nearest beat time, or None if no beats available
        """
        if len(self.beats) == 0:
            return None
        nearest_idx = np.argmin(np.abs(self.beats - time_sec))
        return float(self.beats[nearest_idx])

    def is_on_beat(self, time_sec: float) -> bool:
        """Check if time is within snap tolerance of any beat.

        Args:
            time_sec: Input timestamp in seconds

        Returns:
            True if timestamp is within tolerance of any beat
        """
        if len(self.beats) == 0:
            return False
        min_distance = np.min(np.abs(self.beats - time_sec))
        return min_distance <= self.tolerance_sec
