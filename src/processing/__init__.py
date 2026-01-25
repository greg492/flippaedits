"""
Video processing module.

Handles video decoding, frame extraction, effects application, and encoding
using PyAV for memory-efficient streaming of large video files.
"""

from .edit_session import EditSession, SlowMotionSettings, ColorGradingSettings

__all__ = [
    'EditSession',
    'SlowMotionSettings',
    'ColorGradingSettings',
]
