"""
Video metadata extraction utilities.

Provides functions to read video file metadata (resolution, fps, duration, codec)
using PyAV streaming API.
"""

from pathlib import Path
from typing import NamedTuple, Union
import av
from .errors import translate_ffmpeg_error


class VideoInfo(NamedTuple):
    """
    Video metadata container.

    Attributes:
        width: Video width in pixels
        height: Video height in pixels
        fps: Frames per second (average rate)
        duration_seconds: Total duration in seconds
        codec: Codec name (e.g., 'h264', 'hevc')
        total_frames: Total number of frames (estimated if unavailable)
        pixel_format: Pixel format (e.g., 'yuv420p')
        is_4k: True if resolution is 4K or higher (width >= 3840 or height >= 2160)
        is_high_fps: True if fps >= 60
    """
    width: int
    height: int
    fps: float
    duration_seconds: float
    codec: str
    total_frames: int
    pixel_format: str
    is_4k: bool
    is_high_fps: bool


def is_supported_format(file_path: Union[str, Path]) -> bool:
    """
    Check if file format is supported (MP4 or MOV).

    Args:
        file_path: Path to video file

    Returns:
        True if file extension is .mp4 or .mov (case-insensitive)

    Examples:
        >>> is_supported_format("video.mp4")
        True
        >>> is_supported_format("video.MOV")
        True
        >>> is_supported_format("video.avi")
        False
    """
    path = Path(file_path)
    return path.suffix.lower() in {'.mp4', '.mov'}


def get_video_info(file_path: Union[str, Path]) -> VideoInfo:
    """
    Extract metadata from video file.

    Args:
        file_path: Path to video file (MP4 or MOV)

    Returns:
        VideoInfo object containing metadata

    Raises:
        ValueError: If file has no video stream
        av.FFmpegError: If file cannot be opened or read (wrapped with user-friendly message)

    Examples:
        >>> info = get_video_info("test_4k.mp4")
        >>> info.width, info.height
        (3840, 2160)
        >>> info.is_4k
        True
    """
    file_path = Path(file_path)

    try:
        # Open container for metadata extraction
        container = av.open(str(file_path))

        # Access video stream
        if not container.streams.video:
            container.close()
            raise ValueError("No video stream found in file")

        stream = container.streams.video[0]

        # Extract metadata from stream
        width = stream.width
        height = stream.height
        fps = float(stream.average_rate)

        # Calculate duration using pts * time_base (critical for accuracy)
        # Handle None duration (can occur with network files or corrupted metadata)
        if stream.duration is not None:
            duration_seconds = float(stream.duration * stream.time_base)
        else:
            # Fallback: Use container duration if stream duration unavailable
            if container.duration is not None:
                duration_seconds = float(container.duration) / av.time_base
            else:
                # Ultimate fallback: Estimate from total frames if available
                total_frames_temp = stream.frames
                if total_frames_temp > 0:
                    duration_seconds = float(total_frames_temp) / fps
                else:
                    raise ValueError("Cannot determine video duration - file may be corrupted or incomplete")

        codec = stream.codec_context.name
        pixel_format = stream.codec_context.pix_fmt

        # Get total frames (estimate if unavailable)
        total_frames = stream.frames
        if total_frames == 0:
            # Estimate from duration * fps
            total_frames = int(duration_seconds * fps)

        # Compute derived properties
        is_4k = width >= 3840 or height >= 2160
        is_high_fps = fps >= 60

        container.close()

        return VideoInfo(
            width=width,
            height=height,
            fps=fps,
            duration_seconds=duration_seconds,
            codec=codec,
            total_frames=total_frames,
            pixel_format=pixel_format,
            is_4k=is_4k,
            is_high_fps=is_high_fps
        )

    except av.FFmpegError as e:
        # Translate FFmpeg errors to user-friendly messages
        user_message = translate_ffmpeg_error(str(e))
        raise av.FFmpegError(user_message) from e


__all__ = ['VideoInfo', 'get_video_info', 'is_supported_format']
