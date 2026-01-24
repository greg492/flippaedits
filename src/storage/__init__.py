"""
Storage module.

Manages project state persistence, preset storage, and configuration data
using JSON-based formats for easy version control and backup.
"""

from .temp_manager import (
    TempManager,
    get_temp_manager,
    cleanup_temp_manager,
    is_external_drive,
    needs_copy
)

__all__ = [
    'TempManager',
    'get_temp_manager',
    'cleanup_temp_manager',
    'is_external_drive',
    'needs_copy'
]
