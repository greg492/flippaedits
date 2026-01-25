"""Waveform caching for efficient QPainter rendering.

Provides downsampled audio peaks at pixel resolution to avoid rendering
44,100+ samples per second directly in paintEvent.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Dict


class WaveformCache:
    """Pre-compute downsampled waveform for fast QPainter rendering.

    Downsamples audio from sample rate (typically 22,050 or 44,100 Hz) to
    pixel resolution (typically 1000-2000 points for screen width).
    Uses min/max peaks per pixel for accurate waveform shape.

    Example:
        >>> import numpy as np
        >>> # Create 1 second of 440Hz sine wave at 44100 Hz
        >>> sr = 44100
        >>> t = np.linspace(0, 1, sr)
        >>> audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        >>>
        >>> cache = WaveformCache(audio, sr)
        >>> min_peaks, max_peaks = cache.get_peaks(0.0, 1.0, 100)
        >>> len(min_peaks)  # 100 peaks for 100 pixels
        100
    """

    def __init__(self, audio_samples: np.ndarray, sample_rate: int) -> None:
        """Initialize waveform cache.

        Args:
            audio_samples: 1D numpy array from librosa.load(mono=True).
                          Shape: (n_samples,). Values typically in range [-1.0, 1.0].
            sample_rate: Sample rate in Hz (typically 22050 after librosa resampling)
        """
        self.samples = audio_samples
        self.sr = sample_rate
        self._cache: Dict[Tuple[float, float, int], Tuple[np.ndarray, np.ndarray]] = {}

    def get_peaks(
        self, start_sec: float, end_sec: float, pixel_width: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return (min_peaks, max_peaks) arrays for rendering.

        Strategy: For each pixel, compute min/max of corresponding sample chunk.
        This reduces 44,100 samples/sec to ~1000-2000 values for screen width.
        Results are cached by (start, end, width) tuple for performance.

        Args:
            start_sec: Start time in seconds
            end_sec: End time in seconds
            pixel_width: Number of pixels to render (output array length)

        Returns:
            Tuple of (min_peaks, max_peaks) numpy arrays, each length=pixel_width.
            Values are in the same range as input samples (typically [-1.0, 1.0]).

        Edge Cases:
            - start_sec >= end_sec: Returns empty arrays
            - pixel_width <= 0: Returns empty arrays
            - pixel_width > duration_samples: Uses 1 sample per pixel
            - Empty sample slice: Returns (0, 0) for that pixel

        Example:
            >>> cache = WaveformCache(audio_samples, 22050)
            >>> min_peaks, max_peaks = cache.get_peaks(0.5, 1.5, 200)
            >>> # Now have 200 min/max pairs for 1 second of audio at 200px width
        """
        # Validate inputs
        if start_sec >= end_sec or pixel_width <= 0:
            return np.array([]), np.array([])

        # Check cache
        cache_key = (start_sec, end_sec, pixel_width)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Convert time to sample indices
        start_sample = int(start_sec * self.sr)
        end_sample = int(end_sec * self.sr)

        # Clamp to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(self.samples), end_sample)

        duration_samples = end_sample - start_sample

        # Edge case: no samples in range
        if duration_samples <= 0:
            result = (np.zeros(pixel_width), np.zeros(pixel_width))
            self._cache[cache_key] = result
            return result

        # Calculate samples per pixel
        samples_per_pixel = max(1, duration_samples // pixel_width)

        # Extract min/max for each pixel
        min_peaks = []
        max_peaks = []

        for i in range(pixel_width):
            chunk_start = start_sample + i * samples_per_pixel
            chunk_end = min(chunk_start + samples_per_pixel, end_sample)

            # Handle edge case where we've run out of samples
            if chunk_start >= len(self.samples):
                min_peaks.append(0.0)
                max_peaks.append(0.0)
                continue

            chunk = self.samples[chunk_start:chunk_end]

            if len(chunk) > 0:
                min_peaks.append(float(np.min(chunk)))
                max_peaks.append(float(np.max(chunk)))
            else:
                min_peaks.append(0.0)
                max_peaks.append(0.0)

        result = (np.array(min_peaks), np.array(max_peaks))

        # Cache result (with LRU-style eviction if cache grows too large)
        if len(self._cache) >= 10:
            # Simple eviction: remove oldest entry
            self._cache.pop(next(iter(self._cache)))

        self._cache[cache_key] = result
        return result

    def clear_cache(self) -> None:
        """Clear the peak cache to free memory.

        Useful when zooming to many different levels or when memory is constrained.
        """
        self._cache.clear()

    def get_duration_sec(self) -> float:
        """Get audio duration in seconds.

        Returns:
            Duration in seconds
        """
        return len(self.samples) / self.sr

    def get_sample_rate(self) -> int:
        """Get audio sample rate.

        Returns:
            Sample rate in Hz
        """
        return self.sr


__all__ = ['WaveformCache']
