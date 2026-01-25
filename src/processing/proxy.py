"""
Proxy video generation utilities.

Provides hardware-accelerated 720p proxy generation from 4K source videos
using PyAV streaming architecture and VideoToolbox acceleration.
"""

import os
from pathlib import Path
from typing import Union, Optional, Callable, Dict
import av
from .errors import translate_ffmpeg_error


# Global encoder state (set during first generate_proxy call)
_encoder_info: Optional[Dict[str, Union[str, bool]]] = None


def get_encoder_info() -> Dict[str, Union[str, bool]]:
    """
    Get information about the encoder being used.

    Returns:
        Dictionary with:
            - encoder: Codec name ('h264_videotoolbox' or 'libx264')
            - hardware_accelerated: True if using VideoToolbox, False otherwise

    Note:
        Encoder is determined on first call to generate_proxy().
        Returns cached result on subsequent calls.

    Examples:
        >>> info = get_encoder_info()
        >>> info['encoder']
        'h264_videotoolbox'
        >>> info['hardware_accelerated']
        True
    """
    global _encoder_info

    if _encoder_info is None:
        # Not yet determined - try to detect VideoToolbox availability
        try:
            # Attempt to create a test encoder
            with av.open(av.format.Format('null', 'w')) as container:
                stream = container.add_stream('h264_videotoolbox', rate=30)
                stream.width = 1280
                stream.height = 720
                stream.pix_fmt = 'yuv420p'
                _encoder_info = {
                    'encoder': 'h264_videotoolbox',
                    'hardware_accelerated': True
                }
        except (av.FFmpegError, ValueError):
            # VideoToolbox not available, use software encoder
            _encoder_info = {
                'encoder': 'libx264',
                'hardware_accelerated': False
            }

    return _encoder_info


def generate_proxy(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """
    Generate 720p proxy video from source using hardware acceleration.

    Uses PyAV streaming architecture (no array loading) for memory-efficient
    processing. Attempts h264_videotoolbox encoder, falls back to libx264
    if VideoToolbox unavailable.

    Args:
        input_path: Path to source video file
        output_path: Path where proxy file should be saved
        progress_callback: Optional callback for progress updates (0-100)

    Returns:
        Path to generated proxy file (str)

    Raises:
        ValueError: If input file has no video stream
        av.FFmpegError: If video cannot be processed (wrapped with user-friendly message)

    Examples:
        >>> def on_progress(percent):
        ...     print(f"Progress: {percent}%")
        >>> result = generate_proxy("source_4k.mp4", "proxy_720p.mp4", on_progress)
        >>> result
        'proxy_720p.mp4'
    """
    global _encoder_info

    input_path = Path(input_path)
    output_path = Path(output_path)

    try:
        # Check available disk space before starting
        # Estimate proxy will be ~10% of source size (720p vs 4K with similar quality)
        source_size = input_path.stat().st_size
        estimated_proxy_size = int(source_size * 0.15)  # Add 50% safety margin

        output_dir = output_path.parent
        stat = os.statvfs(output_dir)
        available_bytes = stat.f_bavail * stat.f_frsize

        if available_bytes < estimated_proxy_size:
            # Convert to human-readable sizes
            required_gb = estimated_proxy_size / (1024 ** 3)
            available_gb = available_bytes / (1024 ** 3)
            raise OSError(
                f"Not enough disk space to generate proxy. "
                f"Need ~{required_gb:.1f}GB, only {available_gb:.1f}GB available. "
                f"Please free up disk space and try again."
            )

        # Open input container
        input_container = av.open(str(input_path))

        # Get input video stream
        if not input_container.streams.video:
            input_container.close()
            raise ValueError("No video stream found in input file")

        input_stream = input_container.streams.video[0]

        # Enable multi-core decoding for 5x performance improvement (per research)
        input_stream.codec_context.thread_type = "AUTO"

        # Get input frame rate
        input_rate = input_stream.average_rate

        # Open output container
        output_container = av.open(str(output_path), mode='w')

        # Try VideoToolbox hardware encoder, fallback to software
        encoder_name = None
        output_stream = None

        try:
            encoder_name = "h264_videotoolbox"
            output_stream = output_container.add_stream(encoder_name, rate=input_rate)
            output_stream.width = 1280
            output_stream.height = 720
            output_stream.pix_fmt = "yuv420p"

            # Set quality for VideoToolbox (1-100, higher = better)
            # Per research: 50 = medium quality, balances file size vs preview fidelity
            output_stream.codec_context.options = {"q:v": "50"}

            # Cache encoder info
            _encoder_info = {
                'encoder': encoder_name,
                'hardware_accelerated': True
            }

        except av.FFmpegError:
            # VideoToolbox unavailable - fallback to software encoder
            encoder_name = "libx264"
            output_stream = output_container.add_stream(encoder_name, rate=input_rate)
            output_stream.width = 1280
            output_stream.height = 720
            output_stream.pix_fmt = "yuv420p"

            # Cache encoder info
            _encoder_info = {
                'encoder': encoder_name,
                'hardware_accelerated': False
            }

        # Copy audio stream to proxy (no re-encoding for speed)
        # Audio at original speed - TF-05 (sync through speed changes) deferred to Phase 2
        audio_stream = None
        if input_container.streams.audio:
            input_audio = input_container.streams.audio[0]
            # add_stream() requires codec as first positional argument (PyAV 16.1.0 API)
            audio_stream = output_container.add_stream(
                input_audio.codec_context.name,
                rate=input_audio.rate
            )

        # Get total frames for progress calculation
        total_frames = input_stream.frames
        if total_frames == 0:
            # Estimate from duration * fps if unavailable
            if input_stream.duration is not None:
                duration = float(input_stream.duration * input_stream.time_base)
                fps = float(input_stream.average_rate)
                total_frames = int(duration * fps)
            else:
                # Fallback: Use container duration
                if input_container.duration is not None:
                    duration = float(input_container.duration) / av.time_base
                    fps = float(input_stream.average_rate)
                    total_frames = int(duration * fps)
                else:
                    # Unable to determine total frames - progress will be estimates only
                    total_frames = 0

        processed_frames = 0

        # Stream frames using container.decode() - CRITICAL: no to_ndarray()
        # Process video frames
        for frame in input_container.decode(video=0):
            # Reformat to 720p (hardware-accelerated scaling)
            new_frame = frame.reformat(width=1280, height=720, format="yuv420p")

            # Encode and mux
            for packet in output_stream.encode(new_frame):
                output_container.mux(packet)

            # Update progress
            processed_frames += 1
            if progress_callback and total_frames > 0:
                progress = int((processed_frames / total_frames) * 100)
                progress_callback(progress)

        # Flush video encoder
        for packet in output_stream.encode():
            output_container.mux(packet)

        # Process audio frames if audio stream exists
        if audio_stream:
            for frame in input_container.decode(audio=0):
                for packet in audio_stream.encode(frame):
                    output_container.mux(packet)

            # Flush audio encoder
            for packet in audio_stream.encode():
                output_container.mux(packet)

        # Close containers
        input_container.close()
        output_container.close()

        # Report 100% completion
        if progress_callback:
            progress_callback(100)

        return str(output_path)

    except OSError as e:
        # Handle OS errors (disk full, permissions, etc.)
        if e.errno == 28:  # ENOSPC - No space left on device
            raise OSError(
                "Disk full! Cannot generate proxy. Please free up disk space and try again."
            ) from e
        raise

    except av.FFmpegError as e:
        # Translate FFmpeg errors to user-friendly messages
        user_message = translate_ffmpeg_error(str(e))
        raise RuntimeError(user_message) from e


__all__ = ['generate_proxy', 'get_encoder_info']
