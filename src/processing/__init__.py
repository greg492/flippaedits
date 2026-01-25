"""
Video processing module.

Handles video decoding, frame extraction, effects application, and encoding
using PyAV for memory-efficient streaming of large video files.
"""

from .edit_session import EditSession, SlowMotionSettings, ColorGradingSettings
from .effects import apply_slow_motion, apply_lut, apply_effects_chain
from .lut_loader import LUTPreset, load_lut_registry, get_lut_by_name, get_luts_directory

__all__ = [
    'EditSession',
    'SlowMotionSettings',
    'ColorGradingSettings',
    'apply_slow_motion',
    'apply_lut',
    'apply_effects_chain',
    'LUTPreset',
    'load_lut_registry',
    'get_lut_by_name',
    'get_luts_directory',
]
