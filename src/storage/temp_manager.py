"""Temporary file management for video processing.

Provides automatic cleanup of temporary files created during video import,
especially for videos copied from external drives.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Union, Optional


class TempManager:
    """Manages temporary directory for video processing.

    Creates a temporary directory for storing copied videos and proxy files,
    with automatic cleanup when the manager is destroyed or explicitly closed.

    Examples:
        >>> with TempManager() as tm:
        ...     copied = tm.copy_video("/Volumes/BACKUP/video.mp4")
        ...     proxy = tm.get_proxy_path("video.mp4")
        # Temp directory automatically cleaned up after context exit

        >>> tm = TempManager()
        >>> copied = tm.copy_video("/path/to/video.mp4")
        >>> tm.cleanup()  # Explicit cleanup
    """

    def __init__(self) -> None:
        """Initialize temp manager with temporary directory."""
        self._temp_dir = tempfile.TemporaryDirectory(prefix="lacrosse_")
        self.temp_dir = Path(self._temp_dir.name)

    def copy_video(self, source_path: Union[str, Path]) -> Path:
        """Copy video file to temporary directory.

        Preserves file metadata (timestamps, permissions) using shutil.copy2.

        Args:
            source_path: Path to source video file

        Returns:
            Path to copied file in temp directory

        Examples:
            >>> tm = TempManager()
            >>> copied = tm.copy_video("/Volumes/BACKUP/video.mp4")
            >>> copied.exists()
            True
        """
        source_path = Path(source_path)
        dest_path = self.temp_dir / source_path.name

        # Copy file preserving metadata
        shutil.copy2(source_path, dest_path)

        return dest_path

    def get_proxy_path(self, original_name: str) -> Path:
        """Get path for proxy file corresponding to original video.

        Args:
            original_name: Name of original video file (e.g., "video.mp4")

        Returns:
            Path where proxy should be saved (e.g., "video_proxy.mp4")

        Examples:
            >>> tm = TempManager()
            >>> proxy_path = tm.get_proxy_path("test_video.mp4")
            >>> proxy_path.name
            'test_video_proxy.mp4'
        """
        original_path = Path(original_name)
        stem = original_path.stem
        proxy_name = f"{stem}_proxy.mp4"
        return self.temp_dir / proxy_name

    def cleanup(self) -> None:
        """Explicitly clean up temporary directory.

        Note:
            Cleanup also happens automatically when object is destroyed
            or when used as context manager.
        """
        if hasattr(self, '_temp_dir'):
            self._temp_dir.cleanup()

    def __enter__(self) -> 'TempManager':
        """Enter context manager.

        Returns:
            self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and cleanup.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        self.cleanup()

    def __del__(self) -> None:
        """Clean up on object destruction."""
        self.cleanup()


# Module-level singleton for global temp manager access
_temp_manager: Optional[TempManager] = None


def get_temp_manager() -> TempManager:
    """Get or create the global temp manager singleton.

    Returns:
        Global TempManager instance

    Examples:
        >>> tm1 = get_temp_manager()
        >>> tm2 = get_temp_manager()
        >>> tm1 is tm2
        True
    """
    global _temp_manager

    if _temp_manager is None:
        _temp_manager = TempManager()

    return _temp_manager


def cleanup_temp_manager() -> None:
    """Clean up and reset the global temp manager singleton.

    Examples:
        >>> tm = get_temp_manager()
        >>> cleanup_temp_manager()
        >>> get_temp_manager() is tm
        False
    """
    global _temp_manager

    if _temp_manager is not None:
        _temp_manager.cleanup()
        _temp_manager = None


def is_external_drive(path: Union[str, Path]) -> bool:
    """Check if path is on an external drive.

    On macOS, external drives are mounted under /Volumes/.

    Args:
        path: File or directory path to check

    Returns:
        True if path is on external drive, False otherwise

    Examples:
        >>> is_external_drive("/Volumes/BACKUP/video.mp4")
        True
        >>> is_external_drive("/Users/name/video.mp4")
        False
    """
    path = Path(path).resolve()
    # Check if path starts with /Volumes/ (macOS external drive mount point)
    return path.parts[0] == '/' and len(path.parts) > 1 and path.parts[1] == 'Volumes'


def needs_copy(path: Union[str, Path]) -> bool:
    """Check if video file should be copied to temp storage.

    Files on external drives should be copied for performance and reliability.

    Args:
        path: Path to video file

    Returns:
        True if file should be copied to temp storage

    Examples:
        >>> needs_copy("/Volumes/BACKUP/video.mp4")
        True
        >>> needs_copy("/Users/name/Desktop/video.mp4")
        False
    """
    return is_external_drive(path)


__all__ = [
    'TempManager',
    'get_temp_manager',
    'cleanup_temp_manager',
    'is_external_drive',
    'needs_copy'
]
