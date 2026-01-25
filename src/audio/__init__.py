"""Audio processing module for music sync.

Provides beat detection, music playback, and waveform visualization.
"""

# Always available
from .music_player import MusicPlayer
from .waveform_cache import WaveformCache

__all__ = [
    'MusicPlayer',
    'WaveformCache',
]

# Import beat detector if available (from Plan 01 in parallel execution)
try:
    from .beat_detector import BeatDetectorWorker, detect_beats
    __all__.extend(['BeatDetectorWorker', 'detect_beats'])
except ImportError:
    # Beat detector not yet implemented (Plan 01 pending)
    pass
