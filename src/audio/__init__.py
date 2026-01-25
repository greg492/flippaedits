"""Audio processing module for music sync.

Provides beat detection, music playback, and waveform visualization.
"""

from .beat_detector import BeatDetectorWorker, detect_beats
from .music_player import MusicPlayer
from .waveform_cache import WaveformCache

__all__ = [
    'BeatDetectorWorker',
    'detect_beats',
    'MusicPlayer',
    'WaveformCache',
]
