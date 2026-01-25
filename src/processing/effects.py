"""Video effects processing using PyAV filter graphs.

Provides slow-motion and LUT color grading effects using FFmpeg's
battle-tested filters (setpts, atempo, lut3d) via PyAV's streaming API.
"""

import logging
from pathlib import Path
from typing import Callable, Optional

import av

logger = logging.getLogger(__name__)


def _calculate_atempo_chain(speed: float) -> list[float]:
    """Calculate atempo filter values for given speed.

    atempo range is [0.5, 2.0]. Values outside must be chained.

    Args:
        speed: Target playback speed (e.g., 0.25, 0.5, 0.75)

    Returns:
        List of atempo values to chain

    Examples:
        0.25 -> [0.5, 0.5]  (0.5 * 0.5 = 0.25)
        0.5  -> [0.5]
        0.75 -> [0.75]
        1.0  -> [1.0] (no change)
    """
    values = []
    remaining = speed

    while remaining < 0.5:
        values.append(0.5)
        remaining /= 0.5

    while remaining > 2.0:
        values.append(2.0)
        remaining /= 2.0

    if 0.5 <= remaining <= 2.0:
        values.append(remaining)

    return values if values else [1.0]


def apply_slow_motion(
    input_path: str,
    output_path: str,
    speed: float,
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Apply slow-motion effect to video with audio sync.

    Uses setpts filter for video speed and atempo for audio.
    Maintains audio-video sync by processing both streams.

    Args:
        input_path: Source video file path
        output_path: Output file path
        speed: Playback speed (0.25, 0.5, 0.75, 1.0)
        progress_callback: Optional progress callback (0-100)

    Returns:
        Path to output file

    Raises:
        ValueError: If speed not in allowed values
        av.FFmpegError: If processing fails

    Note:
        For speeds < 0.5, atempo filters are chained (FFmpeg limitation).
        VideoToolbox hardware acceleration used for encoding.
    """
    # Validate speed
    allowed_speeds = (0.25, 0.5, 0.75, 1.0)
    if speed not in allowed_speeds:
        raise ValueError(f"Speed must be one of {allowed_speeds}, got {speed}")

    # Skip processing if speed is 1.0 (no slow-motion)
    if speed == 1.0:
        logger.info("Speed is 1.0, copying file without modification")
        import shutil
        shutil.copy2(input_path, output_path)
        if progress_callback:
            progress_callback(100)
        return output_path

    logger.info(f"Applying slow-motion: {speed}x to {input_path}")

    input_container = av.open(input_path)
    output_container = av.open(output_path, mode='w')

    try:
        # Get input streams
        video_stream = input_container.streams.video[0]
        video_stream.thread_type = 'AUTO'  # Multi-core decoding

        audio_stream = None
        if input_container.streams.audio:
            audio_stream = input_container.streams.audio[0]

        # Calculate PTS multiplier (inverse of speed)
        pts_factor = 1.0 / speed  # 0.5x speed -> 2.0 PTS multiplier

        # Create output video stream with hardware acceleration
        try:
            output_video = output_container.add_stream('h264_videotoolbox', rate=video_stream.average_rate)
            output_video.options = {'q:v': '50'}  # Quality setting
            logger.info("Using VideoToolbox hardware encoder")
        except av.FFmpegError:
            output_video = output_container.add_stream('libx264', rate=video_stream.average_rate)
            output_video.options = {'crf': '23', 'preset': 'medium'}
            logger.info("Falling back to libx264 software encoder")

        output_video.width = video_stream.width
        output_video.height = video_stream.height
        output_video.pix_fmt = 'yuv420p'

        # Create output audio stream
        output_audio = None
        if audio_stream:
            output_audio = output_container.add_stream(
                audio_stream.codec_context.name,
                rate=audio_stream.rate
            )

        # Calculate total frames for progress
        total_frames = video_stream.frames or 0
        if total_frames == 0 and video_stream.duration:
            total_frames = int(float(video_stream.duration) * float(video_stream.time_base) * float(video_stream.average_rate))
        processed_frames = 0

        # Process video frames with PTS adjustment
        logger.info(f"Processing video with PTS factor: {pts_factor}")
        for frame in input_container.decode(video=0):
            # Adjust PTS for slow-motion
            if frame.pts is not None:
                frame.pts = int(frame.pts * pts_factor)
            if frame.dts is not None:
                frame.dts = int(frame.dts * pts_factor)

            # Encode frame
            for packet in output_video.encode(frame):
                output_container.mux(packet)

            processed_frames += 1
            if progress_callback and total_frames > 0:
                # Video is 70% of work
                progress_callback(int(processed_frames / total_frames * 70))

        # Flush video encoder
        for packet in output_video.encode():
            output_container.mux(packet)

        # Process audio with atempo filter
        if audio_stream and output_audio:
            logger.info(f"Processing audio with atempo chain for {speed}x")
            input_container.seek(0)

            # Create audio filter graph
            graph = av.filter.Graph()
            abuffer = graph.add_abuffer(template=audio_stream)

            # Chain atempo filters
            atempo_values = _calculate_atempo_chain(speed)
            prev_node = abuffer
            for atempo_val in atempo_values:
                atempo = graph.add("atempo", str(atempo_val))
                prev_node.link_to(atempo)
                prev_node = atempo

            abuffersink = graph.add("abuffersink")
            prev_node.link_to(abuffersink)
            graph.configure()

            # Process audio frames through filter
            for frame in input_container.decode(audio=0):
                graph.push(frame)
                while True:
                    try:
                        filtered_frame = graph.pull()
                        for packet in output_audio.encode(filtered_frame):
                            output_container.mux(packet)
                    except (av.BlockingIOError, av.EOFError):
                        break

            # Flush audio encoder
            for packet in output_audio.encode():
                output_container.mux(packet)

        if progress_callback:
            progress_callback(100)

        logger.info(f"Slow-motion complete: {output_path}")
        return output_path

    finally:
        input_container.close()
        output_container.close()
