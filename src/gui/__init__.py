"""
GUI module.

Provides PySide6-based user interface for video import, timeline editing,
timestamp management, and preview functionality.
"""

from .timeline_widget import TimelineWidget, TimelineMarkerDisplay
from .effects_panel import EffectsPanel
from .video_preview import VideoPreviewWidget
from .main_window import MainWindow, VideoDropZone
from .music_panel import MusicPanel, WaveformDisplay

__all__ = [
    'TimelineWidget',
    'TimelineMarkerDisplay',
    'EffectsPanel',
    'VideoPreviewWidget',
    'MainWindow',
    'VideoDropZone',
    'MusicPanel',
    'WaveformDisplay',
]
