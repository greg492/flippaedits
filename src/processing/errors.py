"""
FFmpeg error translation utilities.

Provides user-friendly error messages for common FFmpeg/PyAV errors.
"""

from typing import Optional
from av import FFmpegError


def translate_ffmpeg_error(stderr: str) -> str:
    """
    Translate FFmpeg error messages to user-friendly descriptions.

    Args:
        stderr: FFmpeg stderr output containing error information

    Returns:
        User-friendly error message string

    Examples:
        >>> translate_ffmpeg_error("no such file or directory")
        'Could not find the video file. Please check if the file still exists.'
        >>> translate_ffmpeg_error("Invalid data found when processing input")
        'This file format is not supported. Please use MP4 or MOV files.'
    """
    stderr_lower = stderr.lower()

    # Check for common error patterns
    if "no such file" in stderr_lower or "does not exist" in stderr_lower:
        return "Could not find the video file. Please check if the file still exists."

    if "invalid data" in stderr_lower or "invalid argument" in stderr_lower:
        return "This file format is not supported. Please use MP4 or MOV files."

    if "permission denied" in stderr_lower:
        return "Cannot access this file. Please check file permissions."

    if "codec" in stderr_lower and "not found" in stderr_lower:
        return "Video codec not supported. Please convert to H.264 format."

    if "resource temporarily unavailable" in stderr_lower:
        return "File is in use by another application. Please close other apps and try again."

    # Fallback: Try to extract meaningful error from stderr
    # Remove lines with brackets (typically timestamps and metadata)
    lines = [line.strip() for line in stderr.split('\n')
             if line.strip() and not line.strip().startswith('[')]

    if lines:
        # Return last few non-bracket lines as they often contain the actual error
        meaningful_lines = lines[-3:] if len(lines) >= 3 else lines
        return ' '.join(meaningful_lines)

    # Ultimate fallback
    return "An unexpected error occurred while processing the video."


__all__ = ['FFmpegError', 'translate_ffmpeg_error']
