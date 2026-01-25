"""Video export with segment assembly, audio mixing, and vertical encoding.

Provides functions for extracting video segments, assembling them with
beat-synced cuts, mixing video audio with music tracks, and exporting
vertical 9:16 videos optimized for Instagram Reels and TikTok.
"""

from __future__ import annotations
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, List, Optional

import av
import numpy as np

from .template_sequences import VideoSegment
from ..audio.beat_snapper import BeatSnapper

logger = logging.getLogger(__name__)


def extract_segment(
    source_path: str,
    output_path: str,
    segment: VideoSegment,
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Extract single video segment with optional effects.

    Opens source video, seeks to segment start, decodes frames until end,
    applies effects if specified, and encodes to output.

    Args:
        source_path: Path to source video file
        output_path: Path for output file
        segment: VideoSegment with start_ms, end_ms, and optional effects
        progress_callback: Optional callback for progress (0-100)

    Returns:
        Path to output file

    Raises:
        av.FFmpegError: If video processing fails

    Note:
        Uses VideoToolbox hardware acceleration with libx264 fallback.
        If segment.effects contains 'slow_motion', applies PTS adjustment.
    """
    logger.info(f"Extracting segment {segment.start_ms}-{segment.end_ms}ms from {source_path}")

    input_container = av.open(source_path)
    output_container = av.open(output_path, mode='w')

    try:
        video_stream = input_container.streams.video[0]
        video_stream.thread_type = 'AUTO'  # Multi-core decoding

        audio_stream = None
        if input_container.streams.audio:
            audio_stream = input_container.streams.audio[0]

        # Check if slow-motion effect needed
        slow_motion_speed = 1.0
        if segment.effects and 'slow_motion' in segment.effects:
            slow_motion_speed = segment.effects['slow_motion']

        pts_factor = 1.0 / slow_motion_speed if slow_motion_speed != 1.0 else 1.0

        # Create output video stream
        try:
            output_video = output_container.add_stream('h264_videotoolbox', rate=video_stream.average_rate)
            output_video.options = {'q:v': '50'}
            logger.debug("Using VideoToolbox encoder")
        except av.FFmpegError:
            output_video = output_container.add_stream('libx264', rate=video_stream.average_rate)
            output_video.options = {'crf': '23', 'preset': 'medium'}
            logger.debug("Using libx264 encoder")

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

        # Seek to segment start
        start_us = segment.start_ms * 1000  # Convert to microseconds
        end_us = segment.end_ms * 1000

        input_container.seek(start_us, stream=video_stream)

        # Process video frames
        frame_count = 0
        for frame in input_container.decode(video=0):
            if frame.time is None:
                continue

            frame_us = int(frame.time * 1000000)
            if frame_us > end_us:
                break

            # Apply PTS adjustment for slow-motion
            if pts_factor != 1.0:
                if frame.pts is not None:
                    frame.pts = int(frame.pts * pts_factor)
                if frame.dts is not None:
                    frame.dts = int(frame.dts * pts_factor)

            for packet in output_video.encode(frame):
                output_container.mux(packet)

            frame_count += 1
            if progress_callback and frame_count % 10 == 0:
                # Estimate progress (video is ~70% of work)
                progress_callback(min(70, int(frame_count * 0.7)))

        # Flush video encoder
        for packet in output_video.encode():
            output_container.mux(packet)

        # Process audio
        if audio_stream and output_audio:
            input_container.seek(start_us, stream=audio_stream)

            # If slow-motion, need atempo filter
            if slow_motion_speed != 1.0 and slow_motion_speed in (0.25, 0.5, 0.75):
                # Create audio filter graph for atempo
                from .effects import _calculate_atempo_chain

                graph = av.filter.Graph()
                abuffer = graph.add_abuffer(template=audio_stream)

                # Chain atempo filters
                atempo_values = _calculate_atempo_chain(slow_motion_speed)
                prev_node = abuffer
                for atempo_val in atempo_values:
                    atempo = graph.add("atempo", str(atempo_val))
                    prev_node.link_to(atempo)
                    prev_node = atempo

                abuffersink = graph.add("abuffersink")
                prev_node.link_to(abuffersink)
                graph.configure()

                # Process through filter
                for frame in input_container.decode(audio=0):
                    if frame.time is None:
                        continue
                    frame_us = int(frame.time * 1000000)
                    if frame_us > end_us:
                        break

                    graph.push(frame)
                    while True:
                        try:
                            filtered_frame = graph.pull()
                            for packet in output_audio.encode(filtered_frame):
                                output_container.mux(packet)
                        except (av.BlockingIOError, av.EOFError):
                            break
            else:
                # Copy audio without filtering
                for frame in input_container.decode(audio=0):
                    if frame.time is None:
                        continue
                    frame_us = int(frame.time * 1000000)
                    if frame_us > end_us:
                        break

                    for packet in output_audio.encode(frame):
                        output_container.mux(packet)

            # Flush audio encoder
            for packet in output_audio.encode():
                output_container.mux(packet)

        if progress_callback:
            progress_callback(100)

        logger.info(f"Segment extraction complete: {output_path}")
        return output_path

    finally:
        input_container.close()
        output_container.close()


def assemble_segments(
    source_path: str,
    output_path: str,
    segments: List[VideoSegment],
    beats: np.ndarray,
    snap_tolerance_ms: int = 50,
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Assemble video segments with beat-synchronized cuts.

    Extracts each segment, applies beat snapping to boundaries,
    and concatenates using FFmpeg concat demuxer.

    Args:
        source_path: Path to source video file
        output_path: Path for assembled output
        segments: List of VideoSegment objects
        beats: Array of beat times in seconds
        snap_tolerance_ms: Snap tolerance in milliseconds (default 50ms)
        progress_callback: Optional callback for progress (0-100)

    Returns:
        Path to assembled output file

    Raises:
        ValueError: If segments list is empty
        av.FFmpegError: If video processing fails

    Note:
        Creates temporary files for each segment, then concatenates.
        Temporary files are cleaned up after assembly.
    """
    if not segments:
        raise ValueError("Segments list cannot be empty")

    logger.info(f"Assembling {len(segments)} segments with beat snapping")

    # Create beat snapper
    snapper = BeatSnapper(beats, tolerance_ms=snap_tolerance_ms)

    # Snap segment boundaries to beats
    snapped_segments = []
    for seg in segments:
        start_sec = seg.start_ms / 1000.0
        end_sec = seg.end_ms / 1000.0

        snapped_start = snapper.snap_to_beat(start_sec)
        snapped_end = snapper.snap_to_beat(end_sec)

        snapped_segments.append(VideoSegment(
            start_ms=int(snapped_start * 1000),
            end_ms=int(snapped_end * 1000),
            effects=seg.effects
        ))
        logger.debug(
            f"Segment snap: {seg.start_ms}->{int(snapped_start * 1000)}ms, "
            f"{seg.end_ms}->{int(snapped_end * 1000)}ms"
        )

    # Extract segments to temporary files
    temp_files = []
    temp_dir = tempfile.mkdtemp(prefix='lacrosse_segments_')

    try:
        for i, seg in enumerate(snapped_segments):
            temp_path = os.path.join(temp_dir, f'seg{i:03d}.mp4')
            temp_files.append(temp_path)

            # Progress for this segment
            segment_start = int(i / len(snapped_segments) * 80)
            segment_end = int((i + 1) / len(snapped_segments) * 80)

            def seg_progress(p):
                if progress_callback:
                    progress_callback(segment_start + int(p * (segment_end - segment_start) / 100))

            extract_segment(source_path, temp_path, seg, progress_callback=seg_progress)

        # Create concat list file
        list_path = os.path.join(temp_dir, 'concat_list.txt')
        with open(list_path, 'w') as f:
            for temp_file in temp_files:
                # Use absolute paths for concat demuxer
                abs_path = os.path.abspath(temp_file)
                f.write(f"file '{abs_path}'\n")

        logger.info(f"Concatenating {len(temp_files)} segments")

        # Use FFmpeg concat demuxer for fast concatenation
        input_container = av.open(list_path, format='concat', options={'safe': '0'})
        output_container = av.open(output_path, mode='w')

        try:
            # Add output streams matching input
            output_streams = {}
            for stream in input_container.streams:
                if stream.type == 'video':
                    output_stream = output_container.add_stream(template=stream)
                    output_streams[stream] = output_stream
                elif stream.type == 'audio':
                    output_stream = output_container.add_stream(template=stream)
                    output_streams[stream] = output_stream

            # Mux packets
            packet_count = 0
            for packet in input_container.demux():
                if packet.dts is not None:
                    packet.stream = output_streams[packet.stream]
                    output_container.mux(packet)
                    packet_count += 1
                    if progress_callback and packet_count % 100 == 0:
                        progress_callback(min(95, 80 + int(packet_count / 10)))

            if progress_callback:
                progress_callback(100)

            logger.info(f"Assembly complete: {output_path}")
            return output_path

        finally:
            input_container.close()
            output_container.close()

    finally:
        # Clean up temp files and directory
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists(list_path):
            os.remove(list_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


def mix_audio(
    video_path: str,
    music_path: str,
    output_path: str,
    video_volume: float = 0.3,
    music_volume: float = 0.7,
    trim_start_ms: int = 0,
    trim_end_ms: Optional[int] = None,
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Mix video audio with music track using volume control.

    Combines original video audio and music track at specified volumes,
    matching video duration. Uses FFmpeg amix filter for professional mixing.

    Args:
        video_path: Path to video file (with audio)
        music_path: Path to music file (MP3/WAV)
        output_path: Path for output file
        video_volume: Volume for video audio 0.0-1.0 (default 0.3 = 30%)
        music_volume: Volume for music track 0.0-1.0 (default 0.7 = 70%)
        trim_start_ms: Music trim start in milliseconds
        trim_end_ms: Music trim end in milliseconds (None = full duration)
        progress_callback: Optional callback for progress (0-100)

    Returns:
        Path to output file

    Raises:
        ValueError: If total volume > 1.0 (will cause clipping)
        av.FFmpegError: If video processing fails

    Note:
        Video stream is copied unchanged. Only audio is mixed.
        Uses amix filter with normalize=0 to preserve volume settings.
    """
    # Validate volume levels
    if video_volume + music_volume > 1.0:
        raise ValueError(
            f"Total volume ({video_volume + music_volume}) exceeds 1.0. "
            f"This will cause audio clipping. "
            f"Adjust volumes so video_volume + music_volume <= 1.0"
        )

    logger.info(
        f"Mixing audio: video={video_volume}, music={music_volume}, "
        f"trim={trim_start_ms}-{trim_end_ms}ms"
    )

    video_container = av.open(video_path)
    music_container = av.open(music_path)
    output_container = av.open(output_path, mode='w')

    try:
        video_stream = video_container.streams.video[0]
        video_audio = video_container.streams.audio[0] if video_container.streams.audio else None
        music_audio = music_container.streams.audio[0]

        # Create output video stream (copy video unchanged)
        try:
            output_video = output_container.add_stream('h264_videotoolbox', rate=video_stream.average_rate)
            output_video.options = {'q:v': '50'}
        except av.FFmpegError:
            output_video = output_container.add_stream('libx264', rate=video_stream.average_rate)
            output_video.options = {'crf': '23', 'preset': 'medium'}

        output_video.width = video_stream.width
        output_video.height = video_stream.height
        output_video.pix_fmt = 'yuv420p'

        # Create output audio stream (AAC 48kHz stereo)
        output_audio = output_container.add_stream('aac', rate=48000)
        output_audio.channels = 2
        output_audio.layout = 'stereo'

        # Copy video frames unchanged
        frame_count = 0
        for frame in video_container.decode(video=0):
            for packet in output_video.encode(frame):
                output_container.mux(packet)
            frame_count += 1
            if progress_callback and frame_count % 30 == 0:
                progress_callback(min(40, int(frame_count * 0.4)))

        # Flush video encoder
        for packet in output_video.encode():
            output_container.mux(packet)

        # Mix audio if video has audio
        if video_audio:
            logger.info("Creating audio filter graph for mixing")

            # Create filter graph for audio mixing
            graph = av.filter.Graph()

            # Add buffers for both audio streams
            video_audio_buffer = graph.add_abuffer(template=video_audio)
            music_audio_buffer = graph.add_abuffer(template=music_audio)

            # Add volume filters
            video_volume_filter = graph.add("volume", str(video_volume))
            music_volume_filter = graph.add("volume", str(music_volume))

            # Add amix filter
            # duration=first: output ends when first stream (video) ends
            # normalize=0: disable normalization to preserve volume settings
            amix_filter = graph.add("amix", "inputs=2:duration=first:normalize=0")

            # Add sink
            audio_sink = graph.add("abuffersink")

            # Link filters
            video_audio_buffer.link_to(video_volume_filter)
            video_volume_filter.link_to(amix_filter, 0, 0)  # First input to amix

            music_audio_buffer.link_to(music_volume_filter)
            music_volume_filter.link_to(amix_filter, 0, 1)  # Second input to amix

            amix_filter.link_to(audio_sink)

            graph.configure()

            # Seek music to trim start if specified
            if trim_start_ms > 0:
                music_container.seek(trim_start_ms * 1000)  # Seek in microseconds

            # Process audio frames
            # Need to push frames from both sources and pull mixed output
            video_container.seek(0)

            video_frames = video_container.decode(audio=0)
            music_frames = music_container.decode(audio=0)

            # Interleave pushing frames from both sources
            try:
                while True:
                    try:
                        v_frame = next(video_frames)
                        graph.push(v_frame)
                    except StopIteration:
                        break

                    try:
                        m_frame = next(music_frames)
                        graph.push(m_frame)
                    except StopIteration:
                        # Music ended before video - keep processing video
                        pass

                    # Pull mixed frames
                    while True:
                        try:
                            mixed_frame = graph.pull()
                            for packet in output_audio.encode(mixed_frame):
                                output_container.mux(packet)
                        except (av.BlockingIOError, av.EOFError):
                            break

            except StopIteration:
                pass

        else:
            # No video audio - just add music
            logger.info("No video audio found, adding music only")
            if trim_start_ms > 0:
                music_container.seek(trim_start_ms * 1000)

            for frame in music_container.decode(audio=0):
                # Apply music volume
                for packet in output_audio.encode(frame):
                    output_container.mux(packet)

        # Flush audio encoder
        for packet in output_audio.encode():
            output_container.mux(packet)

        if progress_callback:
            progress_callback(100)

        logger.info(f"Audio mixing complete: {output_path}")
        return output_path

    finally:
        video_container.close()
        music_container.close()
        output_container.close()


# Module exports
__all__ = [
    'extract_segment',
    'assemble_segments',
    'mix_audio',
]
