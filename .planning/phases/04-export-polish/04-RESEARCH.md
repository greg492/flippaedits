# Phase 4: Export & Polish - Research

**Researched:** 2026-01-25
**Domain:** Video export with beat-synced cuts, vertical aspect ratio conversion, audio mixing, and Instagram/TikTok optimization
**Confidence:** HIGH

## Summary

Phase 4 implements final export for Instagram Reels and TikTok: 1080x1920 (9:16 vertical), H.264 at 3Mbps+, with beat-synchronized cuts, audio mixing, and one-click template sequences. The research confirms that PyAV's existing filter graph architecture (established in Phases 1-3) extends naturally to export requirements: crop/scale filters for aspect ratio conversion, amix filter for audio mixing, trim/concat for segment assembly, and existing VideoToolbox acceleration for fast encoding.

**Key technical findings:**
- Instagram/TikTok standard: 1080x1920 (9:16), H.264, 3-5 Mbps, AAC 320kbps, 30fps minimum
- Crop 16:9 source to 9:16 using center crop: `crop=w=ih*9/16:h=ih:x=(iw-ow)/2:y=0`
- Audio mixing via amix filter with volume pre-adjustment: `[0:a]volume=0.3[a0];[1:a]volume=0.7[a1];[a0][a1]amix=inputs=2:duration=first`
- Beat-synced cuts with ±50ms snap tolerance align with Phase 3 beat detection
- Template sequences implemented as segment lists with predefined timings
- Single-pass encoding with VideoToolbox sufficient for quality (two-pass negligible benefit)

The existing EditSession model from Phase 3 already contains all state needed (timestamps, beats, effects, music track). Export workflow: trim segments → apply effects → crop/scale to 9:16 → mix audio → encode with high bitrate to survive platform re-encoding.

**Primary recommendation:** Use PyAV filter_complex with crop/scale/trim/concat for video assembly, amix for audio mixing, and VideoToolbox h264 encoding at 4-6 Mbps for Instagram/TikTok upload quality. Implement template sequences as predefined timing patterns applied to EditSession timestamps. Export from source (not proxy) for maximum quality.

## Standard Stack

The established libraries/tools for video export and final assembly:

### Core (from Phases 1-3)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyAV | 16.1.0 | Video export with filter graphs | Established in Phase 1, crop/scale/concat/amix filters available, VideoToolbox acceleration |
| FFmpeg | Latest (bundled) | crop, scale, trim, concat, amix filters | Industry standard, battle-tested filters for all export operations |
| NumPy | Latest | Beat snap calculations and timing | Already in stack from Phase 3 music sync |
| PySide6 | 6.10.1 | Export progress UI | Already in stack, QRunnable worker pattern established |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses | stdlib | Template sequence definitions | Define one-click template timing patterns |
| tempfile | stdlib | Intermediate segment files | Multiple effect passes or segment assembly |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyAV filter graphs | FFmpeg subprocess | Subprocess loses streaming efficiency, PyAV already established |
| PyAV amix | Python audio mixing libraries | Reinventing FFmpeg's battle-tested audio mixing, unnecessary complexity |
| Single-pass encode | Two-pass VBR | Two-pass provides minimal quality gain for modern codecs at adequate bitrates (3-5Mbps), not worth 2x processing time |
| Center crop 9:16 | Add padding bars | Crop maximizes content visibility; padding wastes vertical space on mobile |

**Installation:**
```bash
# No additional packages needed - PyAV 16.1.0 already installed
pip install av==16.1.0 PySide6==6.10.1 numpy
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── processing/
│   ├── export.py           # NEW: Final export with segment assembly
│   ├── effects.py          # (existing) Slow-motion, LUT application
│   ├── edit_session.py     # (existing) EditSession data model
│   └── template_sequences.py # NEW: One-click template definitions
├── audio/
│   ├── beat_snapper.py     # (existing) Beat snapping with tolerance
│   └── audio_mixer.py      # NEW: Audio mixing for video+music
└── gui/
    └── export_dialog.py    # NEW: Export settings UI
```

### Pattern 1: Vertical 9:16 Crop from 16:9 Source

**What:** Crop horizontal 16:9 video to vertical 9:16 for Instagram Reels/TikTok
**When to use:** All exports to social platforms (EX-02)
**Example:**
```python
# Source: FFmpeg crop filter documentation + vertical video best practices
# https://ffmpeg.org/ffmpeg-filters.html
# https://cloudinary.com/guides/video-effects/ffmpeg-crop-video

import av

def create_vertical_crop_graph(input_stream, target_width=1080, target_height=1920):
    """Create filter graph to crop 16:9 to 9:16 vertical format.

    Strategy: Center crop to 9:16, then scale to target resolution.
    For 3840x2160 (4K 16:9) source:
    1. Crop to 1215x2160 (center-cropped 9:16)
    2. Scale to 1080x1920 (Instagram/TikTok standard)

    Args:
        input_stream: PyAV video stream (16:9 aspect ratio)
        target_width: Output width (1080 for Instagram/TikTok)
        target_height: Output height (1920 for Instagram/TikTok)

    Returns:
        Configured filter graph
    """
    graph = av.filter.Graph()

    # Add buffer with template from input stream
    buffer_src = graph.add_buffer(template=input_stream)

    # Calculate center crop dimensions for 9:16 from 16:9 source
    # Crop width = height * (9/16) to preserve 9:16 aspect ratio
    # Formula: crop=w=ih*9/16:h=ih:x=(iw-ow)/2:y=0
    crop_filter = graph.add(
        "crop",
        f"w=ih*9/16:h=ih:x=(iw-ow)/2:y=0"
    )

    # Scale to target resolution (1080x1920 for Instagram/TikTok)
    scale_filter = graph.add(
        "scale",
        f"{target_width}:{target_height}"
    )

    # Add sink
    buffer_sink = graph.add("buffersink")

    # Link filters: buffer -> crop -> scale -> sink
    buffer_src.link_to(crop_filter)
    crop_filter.link_to(scale_filter)
    scale_filter.link_to(buffer_sink)

    graph.configure()
    return graph
```

### Pattern 2: Audio Mixing (Video Audio + Music Track)

**What:** Mix original video audio with music track at specified volumes
**When to use:** All exports with music tracks (EX-05)
**Example:**
```python
# Source: FFmpeg amix filter documentation
# https://ffmpeg.org/ffmpeg-filters.html
# https://www.ffmpeg.media/articles/extract-replace-mix-audio-tracks

import av

def mix_audio_tracks(
    video_path: str,
    music_path: str,
    output_path: str,
    video_volume: float = 0.3,  # 30% video audio
    music_volume: float = 0.7,  # 70% music
    trim_music_start_ms: int = 0,
    trim_music_end_ms: int = None
):
    """Mix video audio with music track using FFmpeg amix filter.

    Strategy:
    1. Decode both audio streams
    2. Apply volume filters to each stream
    3. Mix using amix filter with duration=first (match video length)

    Args:
        video_path: Source video file
        music_path: Music track file
        output_path: Output file path
        video_volume: Volume for video audio (0.0-1.0)
        music_volume: Volume for music track (0.0-1.0)
        trim_music_start_ms: Music trim start in milliseconds
        trim_music_end_ms: Music trim end in milliseconds (None = full duration)

    Note:
        Total volume should not exceed 1.0 to prevent clipping.
        amix filter normalizes by default but may cause volume reduction.
    """
    video_container = av.open(video_path)
    music_container = av.open(music_path)
    output_container = av.open(output_path, mode='w')

    try:
        video_stream = video_container.streams.video[0]
        video_audio = video_container.streams.audio[0] if video_container.streams.audio else None
        music_audio = music_container.streams.audio[0]

        # Create output video stream (copy video, no processing)
        output_video = output_container.add_stream(
            'h264_videotoolbox',
            rate=video_stream.average_rate
        )
        output_video.width = video_stream.width
        output_video.height = video_stream.height
        output_video.pix_fmt = 'yuv420p'
        output_video.options = {'q:v': '50'}

        # Create output audio stream
        output_audio = output_container.add_stream('aac', rate=48000)
        output_audio.channels = 2  # Stereo
        output_audio.layout = 'stereo'

        # Copy video frames unchanged
        for frame in video_container.decode(video=0):
            for packet in output_video.encode(frame):
                output_container.mux(packet)

        # Flush video encoder
        for packet in output_video.encode():
            output_container.mux(packet)

        # Audio mixing via filter graph
        if video_audio:
            # Create filter graph for audio mixing
            graph = av.filter.Graph()

            # Add buffers for both audio streams
            video_audio_buffer = graph.add_abuffer(template=video_audio)
            music_audio_buffer = graph.add_abuffer(template=music_audio)

            # Add volume filters
            video_volume_filter = graph.add("volume", str(video_volume))
            music_volume_filter = graph.add("volume", str(music_volume))

            # Add amix filter
            # duration=first: output ends when first stream ends (video duration)
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

            # Process audio frames
            # Need to interleave frames from both sources
            # For simplicity, decode both fully (for short clips)
            video_frames = list(video_container.decode(audio=0))
            music_frames = list(music_container.decode(audio=0))

            # Push frames through graph
            for vf, mf in zip(video_frames, music_frames):
                graph.push(vf)
                graph.push(mf)
                while True:
                    try:
                        mixed_frame = graph.pull()
                        for packet in output_audio.encode(mixed_frame):
                            output_container.mux(packet)
                    except (av.BlockingIOError, av.EOFError):
                        break
        else:
            # No video audio - just add music
            music_container.seek(trim_music_start_ms)
            for frame in music_container.decode(audio=0):
                for packet in output_audio.encode(frame):
                    output_container.mux(packet)

        # Flush audio encoder
        for packet in output_audio.encode():
            output_container.mux(packet)

        return output_path

    finally:
        video_container.close()
        music_container.close()
        output_container.close()
```

### Pattern 3: Beat-Synced Segment Assembly

**What:** Trim and concatenate video segments with beat-synchronized cuts
**When to use:** Template sequences with music sync
**Example:**
```python
# Source: FFmpeg trim/concat filters + Phase 3 beat snapping
# https://shotstack.io/learn/use-ffmpeg-to-trim-video/
# https://ayosec.github.io/ffmpeg-filters-docs/6.0/Filters/Multimedia/concat.html

import av
import numpy as np
from dataclasses import dataclass
from typing import List

@dataclass
class VideoSegment:
    """Definition of a video segment to extract."""
    start_ms: int
    end_ms: int
    effects: dict = None  # Optional: {'slow_motion': 0.5, 'lut': 'path/to/lut.cube'}

def assemble_beat_synced_reel(
    source_path: str,
    output_path: str,
    segments: List[VideoSegment],
    beats: np.ndarray,
    snap_tolerance_ms: int = 50
):
    """Assemble video segments with beat snapping for smooth music sync.

    Strategy:
    1. Snap segment boundaries to nearest beats within tolerance
    2. Extract each segment (with effects if specified)
    3. Concatenate segments using concat filter

    Args:
        source_path: Source video file
        output_path: Output file path
        segments: List of VideoSegment definitions
        beats: Array of beat times in seconds (from Phase 3 beat detection)
        snap_tolerance_ms: Snap distance in milliseconds (50ms = tight sync)

    Note:
        Uses beat snapping from Phase 3 for professional music sync.
        All segments are trimmed from source, then concatenated.
    """
    from .beat_snapper import BeatSnapper

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

    # Extract segments to temporary files
    import tempfile
    temp_files = []

    for i, seg in enumerate(snapped_segments):
        temp_fd, temp_path = tempfile.mkstemp(suffix='.mp4', prefix=f'seg{i}_')
        import os
        os.close(temp_fd)
        temp_files.append(temp_path)

        # Extract segment with trim
        _extract_segment(source_path, temp_path, seg)

    try:
        # Concatenate segments using concat demuxer
        # Create concat list file
        list_fd, list_path = tempfile.mkstemp(suffix='.txt', prefix='concat_')
        with os.fdopen(list_fd, 'w') as f:
            for temp_file in temp_files:
                f.write(f"file '{temp_file}'\n")

        # Use FFmpeg concat demuxer for fast concatenation
        # This avoids re-encoding if all segments have same codec/params
        input_container = av.open(list_path, format='concat', options={'safe': '0'})
        output_container = av.open(output_path, mode='w')

        try:
            # Copy streams
            for stream in input_container.streams:
                if stream.type == 'video':
                    output_stream = output_container.add_stream(template=stream)
                elif stream.type == 'audio':
                    output_stream = output_container.add_stream(template=stream)

            # Mux packets
            for packet in input_container.demux():
                if packet.dts is not None:
                    output_container.mux(packet)

            return output_path

        finally:
            input_container.close()
            output_container.close()
            os.remove(list_path)

    finally:
        # Clean up temp files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)

def _extract_segment(source_path: str, output_path: str, segment: VideoSegment):
    """Extract single video segment with optional effects."""
    container = av.open(source_path)
    output = av.open(output_path, mode='w')

    try:
        video_stream = container.streams.video[0]
        audio_stream = container.streams.audio[0] if container.streams.audio else None

        # Create output streams
        output_video = output.add_stream('h264_videotoolbox', rate=video_stream.average_rate)
        output_video.width = video_stream.width
        output_video.height = video_stream.height
        output_video.pix_fmt = 'yuv420p'

        output_audio = None
        if audio_stream:
            output_audio = output.add_stream(audio_stream.codec_context.name, rate=audio_stream.rate)

        # Seek to start
        container.seek(segment.start_ms * 1000)  # Seek in microseconds

        # Decode and copy frames within segment
        end_us = segment.end_ms * 1000

        for frame in container.decode(video=0):
            if frame.time is None:
                continue
            frame_us = int(frame.time * 1000000)
            if frame_us > end_us:
                break

            for packet in output_video.encode(frame):
                output.mux(packet)

        # Copy audio
        if audio_stream and output_audio:
            container.seek(segment.start_ms * 1000)
            for frame in container.decode(audio=0):
                if frame.time is None:
                    continue
                frame_us = int(frame.time * 1000000)
                if frame_us > end_us:
                    break

                for packet in output_audio.encode(frame):
                    output.mux(packet)

        # Flush encoders
        for packet in output_video.encode():
            output.mux(packet)
        if output_audio:
            for packet in output_audio.encode():
                output.mux(packet)

    finally:
        container.close()
        output.close()
```

### Pattern 4: One-Click Template Sequences

**What:** Predefined timing patterns for common reel structures (goal → b-roll → slow-mo → celebration)
**When to use:** EX-04 - Quick export with standard template
**Example:**
```python
# Source: Video editing template patterns research
# https://vidionix.com/sequences-101-the-building-blocks-of-professional-video-editing/

from dataclasses import dataclass
from typing import List
from .edit_session import EditSession, VideoSegment

@dataclass
class TemplateSequence:
    """Definition of a one-click template sequence."""
    name: str
    description: str
    segments: List[dict]  # Segment definitions with timing patterns

# Standard templates for lacrosse highlight reels
TEMPLATES = {
    'goal_celebration': TemplateSequence(
        name="Goal + Celebration",
        description="Lead-up to goal → slow-mo goal moment → celebration",
        segments=[
            {
                'type': 'leadup',
                'duration_ms': 3000,  # 3 seconds before goal
                'before_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'goal',
                'duration_ms': 2000,  # 2 seconds of goal moment
                'at_timestamp': 'goal_moment',
                'effects': {'slow_motion': 0.5}  # 2x slow-mo
            },
            {
                'type': 'celebration',
                'duration_ms': 4000,  # 4 seconds of celebration
                'at_timestamp': 'celebration_start',
                'effects': None
            }
        ]
    ),

    'full_play': TemplateSequence(
        name="Full Play Sequence",
        description="Approach → goal → slow-mo replay → celebration",
        segments=[
            {
                'type': 'approach',
                'duration_ms': 5000,
                'before_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'goal',
                'duration_ms': 1500,
                'at_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'replay',
                'duration_ms': 3000,
                'at_timestamp': 'goal_moment',
                'effects': {'slow_motion': 0.25}  # 4x slow-mo replay
            },
            {
                'type': 'celebration',
                'duration_ms': 3000,
                'at_timestamp': 'celebration_start',
                'effects': None
            }
        ]
    )
}

def apply_template(session: EditSession, template_name: str) -> List[VideoSegment]:
    """Apply template sequence to edit session timestamps.

    Converts template definitions into concrete VideoSegment objects
    based on session timestamps (goal_moment_ms, celebration_start_ms).

    Args:
        session: EditSession with marked timestamps
        template_name: Name of template from TEMPLATES dict

    Returns:
        List of VideoSegment objects ready for assembly

    Raises:
        ValueError: If required timestamps not marked in session
    """
    if not session.is_ready_for_export():
        raise ValueError("Session must have goal_moment and celebration_start marked")

    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")

    segments = []

    for seg_def in template.segments:
        # Calculate start/end times based on template timing
        if 'before_timestamp' in seg_def:
            # Segment ends at timestamp
            end_ms = getattr(session, seg_def['before_timestamp'] + '_ms')
            start_ms = end_ms - seg_def['duration_ms']

        elif 'at_timestamp' in seg_def:
            # Segment starts at timestamp
            start_ms = getattr(session, seg_def['at_timestamp'] + '_ms')
            end_ms = start_ms + seg_def['duration_ms']

        else:
            raise ValueError(f"Segment must specify 'before_timestamp' or 'at_timestamp'")

        # Create VideoSegment
        segments.append(VideoSegment(
            start_ms=max(0, start_ms),  # Clamp to video start
            end_ms=end_ms,
            effects=seg_def.get('effects')
        ))

    return segments
```

### Pattern 5: Export with Instagram/TikTok Encoding Settings

**What:** Encode with platform-optimized settings (1080p 9:16, H.264, 3-5 Mbps)
**When to use:** Final export for social platforms (EX-01, EX-02, EX-03)
**Example:**
```python
# Source: Instagram/TikTok video specs research
# https://socialrails.com/blog/instagram-video-size-format-specifications-guide
# https://pixflow.net/blog/the-creators-cheat-sheet-best-video-formats-codecs-for-social-media/

import av
from typing import Optional, Callable

def export_for_instagram_reels(
    input_path: str,
    output_path: str,
    bitrate_mbps: float = 4.0,  # 3-5 Mbps recommended
    progress_callback: Optional[Callable[[int], None]] = None
):
    """Export video optimized for Instagram Reels.

    Instagram Reels settings (2026):
    - Resolution: 1080x1920 (9:16 vertical)
    - Codec: H.264 (VideoToolbox on macOS)
    - Bitrate: 3-5 Mbps (4 Mbps balanced)
    - Frame rate: 30 fps minimum (preserve source up to 60fps)
    - Audio: AAC 320kbps, 48kHz stereo
    - Format: MP4

    High bitrate (3-5 Mbps) preserves quality through Instagram's
    re-encoding process, which compresses to ~3.5 Mbps.

    Args:
        input_path: Source video (any resolution/aspect ratio)
        output_path: Output file path
        bitrate_mbps: Target bitrate in Mbps (3-5 recommended)
        progress_callback: Optional progress callback (0-100)

    Note:
        Assumes input is already processed (effects applied, segments assembled).
        This function handles crop to 9:16, scale to 1080x1920, and encoding.
    """
    container = av.open(input_path)
    output = av.open(output_path, mode='w')

    try:
        video_stream = container.streams.video[0]
        audio_stream = container.streams.audio[0] if container.streams.audio else None

        # Create filter graph for 9:16 crop + scale
        graph = create_vertical_crop_graph(video_stream, target_width=1080, target_height=1920)

        # Create output video stream with high bitrate
        try:
            output_video = output.add_stream('h264_videotoolbox', rate=30)  # 30fps for Instagram
            # VideoToolbox bitrate setting (bits per second)
            bitrate_bps = int(bitrate_mbps * 1_000_000)
            output_video.bit_rate = bitrate_bps
            output_video.options = {
                'q:v': '60',  # Quality 60/100 (balanced)
                'realtime': '0'  # Allow slower encoding for better quality
            }
        except av.FFmpegError:
            # Fallback to libx264
            output_video = output.add_stream('libx264', rate=30)
            output_video.bit_rate = int(bitrate_mbps * 1_000_000)
            output_video.options = {
                'crf': '20',  # CRF 20 = high quality
                'preset': 'slow'  # Slower = better compression
            }

        output_video.width = 1080
        output_video.height = 1920
        output_video.pix_fmt = 'yuv420p'

        # Create output audio stream (AAC 320kbps)
        output_audio = None
        if audio_stream:
            output_audio = output.add_stream('aac', rate=48000)
            output_audio.bit_rate = 320000  # 320 kbps
            output_audio.channels = 2
            output_audio.layout = 'stereo'

        total_frames = video_stream.frames or 0
        if total_frames == 0 and video_stream.duration:
            total_frames = int(float(video_stream.duration) * float(video_stream.time_base) * float(video_stream.average_rate))
        processed = 0

        # Process video through crop/scale filter
        for frame in container.decode(video=0):
            graph.push(frame)
            while True:
                try:
                    filtered = graph.pull()
                    for packet in output_video.encode(filtered):
                        output.mux(packet)
                    processed += 1
                    if progress_callback and total_frames > 0:
                        progress_callback(int(processed / total_frames * 90))
                except (av.BlockingIOError, av.EOFError):
                    break

        # Flush video
        for packet in output_video.encode():
            output.mux(packet)

        # Copy audio
        if audio_stream and output_audio:
            container.seek(0)
            for frame in container.decode(audio=0):
                for packet in output_audio.encode(frame):
                    output.mux(packet)

            # Flush audio
            for packet in output_audio.encode():
                output.mux(packet)

        if progress_callback:
            progress_callback(100)

        return output_path

    finally:
        container.close()
        output.close()


def export_for_tiktok(
    input_path: str,
    output_path: str,
    bitrate_mbps: float = 5.0,  # TikTok supports higher bitrate
    progress_callback: Optional[Callable[[int], None]] = None
):
    """Export video optimized for TikTok.

    TikTok settings (2026):
    - Resolution: 1080x1920 (9:16 vertical)
    - Codec: H.264
    - Bitrate: 5-10 Mbps (5 Mbps balanced, up to 10 for 60fps)
    - Frame rate: 30 or 60 fps
    - Audio: AAC 320kbps, 48kHz stereo
    - Format: MP4

    TikTok's processing is less aggressive than Instagram,
    so higher bitrate provides visible quality improvement.

    Args:
        input_path: Source video
        output_path: Output file path
        bitrate_mbps: Target bitrate in Mbps (5-10 recommended)
        progress_callback: Optional progress callback (0-100)
    """
    # TikTok uses same settings as Instagram but with higher bitrate tolerance
    return export_for_instagram_reels(
        input_path,
        output_path,
        bitrate_mbps=bitrate_mbps,
        progress_callback=progress_callback
    )
```

### Anti-Patterns to Avoid

- **Multiple re-encoding passes:** Encode effects + crop/scale + audio mix in single operation using filter_complex, not sequential files
- **Two-pass encoding:** Single-pass with adequate bitrate (3-5 Mbps) provides equivalent quality for modern codecs, avoids 2x processing time
- **Exporting from proxy:** Always export from source (4K) for maximum quality, apply crop/scale during export
- **Low bitrate "for platform":** Platforms re-encode anyway; export at 3-5 Mbps to survive compression
- **Manual beat alignment:** Use beat snapping with ±50ms tolerance (Phase 3), don't manually adjust frame-by-frame
- **Adding padding instead of cropping:** Crop 16:9 to 9:16 maximizes content; padding wastes vertical space on mobile

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio mixing | Custom audio sample manipulation | FFmpeg amix filter with volume pre-adjustment | Handles sample rate conversion, channel mixing, clipping prevention; custom mixing causes phase issues, click artifacts |
| Video segment concatenation | Manual packet copying | FFmpeg concat filter/demuxer | Handles timestamp discontinuities, stream alignment, GOP boundaries; manual concat causes seek issues |
| Aspect ratio conversion | Manual pixel manipulation | FFmpeg crop + scale filters | GPU-optimized, handles pixel format conversion, preserves quality; manual cropping loses chroma subsampling |
| Beat snapping | Frame-by-frame timing | Phase 3 BeatSnapper with ±50ms tolerance | Already implemented, ±50ms matches audio/video sync perception threshold (EBU R37 standard) |
| Platform-specific encoding | Manual codec settings per platform | Unified H.264 3-5 Mbps profile | Instagram/TikTok both accept H.264 1080p 9:16; single export works for both |
| Template sequences | Custom state management | Dataclass-based template definitions | Type-safe, serializable, easy to add new templates |

**Key insight:** PyAV + FFmpeg filters handle all export complexity. Don't build custom video/audio processing - compose FFmpeg filters via PyAV filter graphs.

## Common Pitfalls

### Pitfall 1: Quality Loss from Multiple Encoding Passes

**What goes wrong:** Applying effects, then cropping, then audio mixing in separate export passes degrades quality noticeably

**Why it happens:** Each decode/encode cycle loses information (lossy compression), cumulative loss visible after 3+ passes

**How to avoid:**
- Use PyAV filter_complex to chain all operations in single pass
- Order: effects (LUT, slow-mo) → crop/scale → audio mix → encode once
- Intermediate files only for segment assembly, not effects

**Warning signs:** Output looks softer/blurrier than source, color banding visible, file size smaller than expected

### Pitfall 2: Instagram/TikTok Further Compress Video

**What goes wrong:** Exported video looks great locally but appears low quality on Instagram/TikTok after upload

**Why it happens:** Platforms re-encode all uploads, compressing to their target bitrate (~3.5 Mbps Instagram, variable TikTok)

**How to avoid:**
- Export at 3-5 Mbps (Instagram) or 5-10 Mbps (TikTok) to give re-encoding "headroom"
- High bitrate export survives platform compression with less degradation
- Test upload, don't judge quality by local file

**Warning signs:** Local file looks perfect, uploaded version has compression artifacts, colors look washed out on platform

### Pitfall 3: Vertical Crop Cuts Off Action

**What goes wrong:** Center crop from 16:9 to 9:16 cuts off important action on sides of frame

**Why it happens:** Lacrosse action often spans full horizontal frame, center crop assumes centered composition

**How to avoid:**
- Allow user to adjust crop position (left/center/right bias)
- Add crop preview before export
- Consider smart crop (detect action zone) as future enhancement
- Document that vertical export may crop action

**Warning signs:** Goal scorer cut out of frame, ball/stick not visible, player partially visible

### Pitfall 4: Audio Mix Volume Clipping

**What goes wrong:** Audio distorts, sounds harsh or has digital artifacts after mixing

**Why it happens:** Total volume exceeds 1.0 (video audio 0.5 + music 0.7 = 1.2), causes clipping

**How to avoid:**
- Ensure `video_volume + music_volume <= 1.0`
- Use amix with `normalize=0` to preserve volume settings
- Default: video 0.3 + music 0.7 = 1.0 (no clipping)
- Allow user adjustment but warn if total > 1.0

**Warning signs:** Audio sounds crunchy, harsh transients, waveform shows flat-topped peaks

### Pitfall 5: Beat-Synced Cuts Feel "Off" Despite Correct Timing

**What goes wrong:** Video cuts land on beat markers but still feel late or disconnected from music

**Why it happens:** Beats may be 20-60ms late (onset detection finds peak, not attack), perception of "on beat" varies

**How to avoid:**
- Apply global timing offset (-40ms typical) to beat times before snapping
- Use `librosa.onset.onset_detect(backtrack=True)` to find preceding energy minimum
- Allow user to preview and adjust snap tolerance (50ms → 100ms for looser sync)
- Consider downbeat detection (strong vs weak beats) for more musical cuts

**Warning signs:** User reports cuts "feel late", cuts interrupt musical phrases, cuts on weak beats instead of downbeats

### Pitfall 6: Export Too Slow (>2 Minutes for 30-Second Clip)

**What goes wrong:** Export takes 5+ minutes for 30-second reel, user expects <2 minutes

**Why it happens:** No hardware acceleration, encoding from 4K source without optimization, multiple passes

**How to avoid:**
- Use VideoToolbox hardware encoder (h264_videotoolbox) on macOS
- Single-pass encoding (two-pass minimal benefit)
- Process proxy (720p) for preview, source (4K) for final export
- Show progress bar, allow background export

**Warning signs:** CPU at 100% during export, fans spin up, export time > 4x video duration, user cancels export

## Code Examples

Verified patterns from official sources:

### PyAV Filter Graph Chaining (Crop → Scale)
```python
# Source: PyAV GitHub issues #239, #392
# https://github.com/mikeboers/PyAV/issues/239
# https://snyk.io/advisor/python/av/functions/av.filter.Graph

import av

# Create filter graph with multiple chained filters
graph = av.filter.Graph()

# Add buffer with input stream template
buffer_src = graph.add_buffer(template=input_stream)

# Add filters in sequence
crop_filter = graph.add("crop", "ih*9/16:ih:(iw-ow)/2:0")  # Center crop to 9:16
scale_filter = graph.add("scale", "1080:1920")  # Scale to Instagram size

# Add sink
buffer_sink = graph.add("buffersink")

# Link filters: buffer -> crop -> scale -> sink
buffer_src.link_to(crop_filter)
crop_filter.link_to(scale_filter)
scale_filter.link_to(buffer_sink)

# Configure graph before use
graph.configure()

# Process frames
for frame in container.decode(video=0):
    graph.push(frame)
    try:
        filtered_frame = graph.pull()
        # Encode filtered frame...
    except (av.BlockingIOError, av.EOFError):
        break
```

### FFmpeg amix Filter with Volume Control
```bash
# Source: FFmpeg amix documentation
# https://ffmpeg.org/ffmpeg-filters.html

# Basic audio mixing with volume adjustment
ffmpeg -i video.mp4 -i music.mp3 \
  -filter_complex "[0:a]volume=0.3[a0];[1:a]volume=0.7[a1];[a0][a1]amix=inputs=2:duration=first:normalize=0" \
  -c:v copy -c:a aac output.mp4

# Explanation:
# [0:a]volume=0.3[a0]  - Reduce video audio to 30%
# [1:a]volume=0.7[a1]  - Reduce music to 70%
# amix=inputs=2:duration=first:normalize=0 - Mix 2 inputs, match video length, no normalization
```

### FFmpeg Trim and Concat for Segment Assembly
```bash
# Source: FFmpeg trim/concat documentation
# https://shotstack.io/learn/use-ffmpeg-to-trim-video/

# Extract multiple segments and concatenate
ffmpeg -i input.mp4 \
  -filter_complex \
  "[0:v]trim=start=5:end=8,setpts=PTS-STARTPTS[v1]; \
   [0:v]trim=start=15:end=20,setpts=PTS-STARTPTS[v2]; \
   [0:a]atrim=start=5:end=8,asetpts=PTS-STARTPTS[a1]; \
   [0:a]atrim=start=15:end=20,asetpts=PTS-STARTPTS[a2]; \
   [v1][a1][v2][a2]concat=n=2:v=1:a=1[outv][outa]" \
  -map "[outv]" -map "[outa]" output.mp4

# Note: setpts=PTS-STARTPTS resets timestamps after trim for concat
```

### VideoToolbox High Bitrate Encoding
```python
# Source: PyAV encoding examples + VideoToolbox docs
# https://pyav.basswood-io.com/docs/stable/cookbook/basics.html

import av

output = av.open('output.mp4', mode='w')

# Create VideoToolbox encoder with high bitrate
stream = output.add_stream('h264_videotoolbox', rate=30)
stream.width = 1080
stream.height = 1920
stream.pix_fmt = 'yuv420p'

# Set bitrate for Instagram/TikTok (4 Mbps)
stream.bit_rate = 4_000_000  # 4 Mbps

# VideoToolbox quality options
stream.options = {
    'q:v': '60',  # Quality 60/100 (higher = better)
    'realtime': '0'  # Allow slower encoding for quality
}
```

### Beat Snapping from Phase 3
```python
# Source: Phase 3 beat snapping implementation
# Already implemented in src/audio/beat_snapper.py

from audio.beat_snapper import BeatSnapper
import numpy as np

# Beat times from Phase 3 detection
beats = np.array([0.5, 1.0, 1.5, 2.0, 2.5])  # seconds

# Create snapper with ±50ms tolerance
snapper = BeatSnapper(beats, tolerance_ms=50)

# Snap cut point to nearest beat
cut_time = 1.03  # User marked cut at 1.03s
snapped_time = snapper.snap_to_beat(cut_time)
# Returns: 1.0 (snapped to beat at 1.0s, within 50ms tolerance)

cut_time2 = 1.15  # Marked at 1.15s
snapped_time2 = snapper.snap_to_beat(cut_time2)
# Returns: 1.15 (no snap, >50ms from nearest beats at 1.0s and 1.5s)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two-pass VBR encoding | Single-pass with adequate bitrate | 2018-2020 (H.264 maturity) | Minimal quality difference for modern codecs at 3-5 Mbps, 50% time savings |
| 4K exports for Instagram/TikTok | 1080p 9:16 standard | 2020+ (mobile-first platforms) | Platforms downsample to 1080p anyway; exporting 4K wastes bandwidth and processing |
| Manual audio mixing libraries | FFmpeg amix filter | Stable since FFmpeg 1.0 | Handles sample rate conversion, channel mixing automatically |
| Sequential effect passes | Single filter_complex operation | FFmpeg 2.0+ (2014) | No intermediate files, no quality loss from multiple encode cycles |
| Add bars for vertical video | Center crop to 9:16 | 2018+ (vertical video normalized) | Cropping maximizes content; bars waste screen space on mobile |
| Frame-by-frame beat sync | ±50ms magnetic snap | 2015+ (NLE standard) | Balances precision with user intent, matches perceptual sync threshold |

**Deprecated/outdated:**
- **320p/480p "mobile" exports:** Modern phones are 1080p+, platforms standardized on 1080p
- **H.263/MPEG-4 Part 2 codecs:** H.264 universal, better compression, hardware accelerated
- **Multiple export profiles per platform:** Instagram/TikTok both accept same H.264 1080p 9:16
- **Desktop-oriented 16:9 exports:** Vertical 9:16 is standard for Reels/TikTok/Stories

## Open Questions

Things that couldn't be fully resolved:

1. **PyAV filter_complex with multiple inputs**
   - What we know: filter_complex needed for audio mixing (video + music), PyAV supports add_abuffer for multiple audio sources
   - What's unclear: Proper frame synchronization pattern when pushing frames from two containers (video audio + music file)
   - Recommendation: Implement with careful frame timing, test with sample clips; may need to buffer frames or use filter timestamps

2. **Smart crop for vertical conversion**
   - What we know: Center crop works for centered compositions, may cut off action on edges
   - What's unclear: Feasibility of ML-based action detection for crop position (computationally expensive?)
   - Recommendation: Start with center crop + manual adjustment UI, defer smart crop to post-launch enhancement

3. **Export time for 4K source**
   - What we know: VideoToolbox provides 4-5x realtime encoding, 30-second clip = 6-8 seconds encode
   - What's unclear: Total time including effects, crop/scale, audio mix; whether <2 minutes achievable for 30-second 4K clip
   - Recommendation: Benchmark during implementation, optimize filter graph order, show accurate progress

4. **Beat snapping offset calibration**
   - What we know: Beats may be 20-60ms late, onset_detect(backtrack=True) improves accuracy
   - What's unclear: Whether global offset or per-beat adjustment needed for lacrosse reels
   - Recommendation: Apply -40ms global offset initially, add user calibration if feedback indicates timing issues

5. **Platform-specific bitrate sweet spot**
   - What we know: Instagram ~3.5 Mbps re-encode, TikTok variable compression
   - What's unclear: Optimal export bitrate that survives platform compression without wasting bandwidth
   - Recommendation: Default 4 Mbps for Instagram, 5 Mbps for TikTok; allow advanced users to adjust

## Sources

### Primary (HIGH confidence)

- [Instagram Video Size & Format Specs 2026: Complete Guide](https://socialrails.com/blog/instagram-video-size-format-specifications-guide) - Official specs: 1080x1920, H.264, 3.5 Mbps, AAC 320kbps
- [Instagram Video Sizes, Dimensions & Formats 2026](https://www.socialpilot.co/instagram-marketing/instagram-video-size-specifications) - Detailed encoding settings and best practices
- [FFmpeg Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html) - Authoritative reference for crop, scale, amix, trim, concat filters
- [PyAV GitHub Issue #239: Filter Examples](https://github.com/mikeboers/PyAV/issues/239) - Working code examples for filter graph usage
- [How to Use FFmpeg to Crop Video | Cloudinary](https://cloudinary.com/guides/video-effects/ffmpeg-crop-video) - Crop filter syntax and best practices
- [FFmpeg amix Filter Documentation](https://ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/amix.html) - amix parameters and volume control

### Secondary (MEDIUM confidence)

- [Best Video Format & Codec for Social Media 2026](https://pixflow.net/blog/the-creators-cheat-sheet-best-video-formats-codecs-for-social-media/) - Platform comparison, H.264 recommendation
- [Use FFmpeg to Crop/Resize Videos — Shotstack](https://shotstack.io/learn/crop-resize-videos-ffmpeg/) - Practical crop/scale examples
- [Extract, Replace, and Mix Audio Tracks in FFmpeg](https://www.ffmpeg.media/articles/extract-replace-mix-audio-tracks) - Audio mixing patterns
- [How to Trim Video Using FFmpeg — Shotstack](https://shotstack.io/learn/use-ffmpeg-to-trim-video/) - Trim/concat for segment assembly
- [Snyk: PyAV filter.Graph Examples](https://snyk.io/advisor/python/av/functions/av.filter.Graph) - Community usage patterns
- [Single-Pass vs Two-Pass VBR - Streaming Learning Center](https://streaminglearningcenter.com/encoding/single-two-pass-vbr.html) - Encoding performance comparison
- [12 Best AI Beat-Sync Tools 2026 - OpusClip](https://www.opus.pro/blog/best-ai-beat-sync) - Beat snapping implementation patterns
- [Sequences 101: Video Editing - Vidionix](https://vidionix.com/sequences-101-the-building-blocks-of-professional-video-editing/) - Template sequence structure

### Tertiary (LOW confidence - needs validation)

- [Living mixing video & audio by using PyAv (GitHub Gist)](https://gist.github.com/Meonardo/953369cb00a224179125bd981d219bc9) - Audio mixing example (lacks volume control)
- [9:16 Aspect Ratio Conversion for IGTV with FFmpeg](https://www.linkedin.com/pulse/916-aspect-ratio-conversion-instagram-igtv-ffmpeg-zoltan-gasz) - Vertical conversion (2019, may be outdated)
- WebSearch results: "video editing template sequences one-click export patterns" - General patterns, no PyAV-specific examples

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PyAV 16.1.0 established in Phases 1-3, FFmpeg filters verified in official docs
- Architecture patterns: MEDIUM-HIGH - Filter graph patterns verified with examples, audio mixing needs validation
- Instagram/TikTok settings: HIGH - Multiple authoritative sources confirm 1080p 9:16, H.264, 3-5 Mbps
- Beat snapping: HIGH - Phase 3 implementation already complete, ±50ms tolerance verified
- Template sequences: MEDIUM - Pattern established but implementation needs testing

**Research date:** 2026-01-25
**Valid until:** ~60 days (Instagram/TikTok specs stable, FFmpeg filters stable, PyAV 16.1.0 mature)

**Caveats:**
- PyAV filter_complex with multiple audio inputs needs implementation validation
- Export time benchmark required to verify <2 minute target
- Platform re-encoding quality needs testing with actual uploads
- Beat snapping timing offset may need user calibration
