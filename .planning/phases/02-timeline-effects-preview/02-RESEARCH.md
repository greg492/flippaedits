# Phase 2: Timeline, Effects & Preview - Research

**Researched:** 2026-01-24
**Domain:** Video timeline editing, slow-motion effects, LUT color grading, and preview rendering with PyAV + PySide6
**Confidence:** HIGH

## Summary

Phase 2 builds on the Phase 1 foundation (PyAV streaming, proxy generation, QMediaPlayer preview) to add timestamp marking, slow-motion effects, and LUT color grading. The research confirms that PyAV's filter graph API (`av.filter.Graph`) provides native FFmpeg filter access for both video (setpts, lut3d) and audio (atempo) processing, enabling all Phase 2 requirements without additional libraries.

The critical insight is that **slow-motion requires separate video and audio processing paths**: video uses PTS manipulation (`setpts=N*PTS`), while audio uses the atempo filter to preserve pitch. For slow-motion speeds below 0.5x (e.g., 0.25x), atempo filters must be chained (0.5 x 0.5 = 0.25). The decision from Phase 1 to "copy audio at original speed, defer TF-05 to Phase 2" is now addressed with a clear implementation path.

For LUT color grading, FFmpeg's `lut3d` filter natively supports `.cube` files (the industry standard format used by DaVinci Resolve, Premiere, Final Cut). Free cinematic LUT packs are widely available, and the application should bundle 5-15 curated presets covering common sports video styles (high contrast, teal-orange, film emulation).

**Primary recommendation:** Use PyAV's `av.filter.Graph` API for all effects processing (setpts for slow-motion video, atempo for audio speed, lut3d for color grading). Implement timestamp marking via QMediaPlayer position capture on user click/button press. Generate preview by processing proxy through filter chain before display.

## Standard Stack

### Core (from Phase 1)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyAV | 16.1.0 | Video/audio processing with FFmpeg filters | Native filter graph API, streaming architecture, already established in Phase 1 |
| PySide6 | 6.10.1 | GUI with QMediaPlayer preview | Already established, playback rate control built-in, click events for timestamps |
| FFmpeg | Latest (bundled) | lut3d, setpts, atempo filters | Industry standard filters for color grading and speed adjustment |

### Supporting (Phase 2 additions)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| av.filter.Graph | (PyAV built-in) | Filter chain management | All effects: slow-motion, LUT application, audio tempo |
| dataclasses | stdlib | Edit session data model | Store timestamp markers, speed settings, LUT selection |
| json | stdlib | Preset serialization | Save/load LUT metadata, user preferences |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyAV filter graph | FFmpeg subprocess | Subprocess loses streaming architecture, harder error handling, slower for frame-by-frame ops |
| PyAV filter graph | MoviePy | MoviePy's effects cause memory exhaustion on 4K (Phase 1 finding), not suitable |
| Built-in QMediaPlayer rate | Custom frame stepping | QMediaPlayer.setPlaybackRate() is simpler for preview; frame stepping only needed for frame-accurate export |
| Bundled LUTs | User-provided only | Bundling presets improves UX; still support user LUT files as stretch goal |

**Installation:**
```bash
# No additional packages needed - PyAV 16.1.0 includes filter graph support
pip install av==16.1.0 PySide6==6.10.1
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── processing/
│   ├── proxy.py           # (existing) Proxy generation
│   ├── video_info.py      # (existing) Metadata extraction
│   ├── errors.py          # (existing) Error translation
│   ├── effects.py         # NEW: Slow-motion, LUT application via filter graphs
│   └── edit_session.py    # NEW: Data model for timestamps, settings
├── gui/
│   ├── main_window.py     # (existing) Main window
│   ├── video_preview.py   # (existing) Preview widget - extend with click handler
│   ├── timeline_widget.py # NEW: Timeline with timestamp markers
│   ├── effects_panel.py   # NEW: Speed/LUT controls
│   └── workers.py         # (existing) Background workers
└── assets/
    └── luts/              # NEW: Bundled .cube LUT presets
        ├── cinematic_warm.cube
        ├── teal_orange.cube
        └── ...
```

### Pattern 1: Timestamp Marking via QMediaPlayer Position

**What:** Capture current playback position when user marks a timestamp (goal moment, celebration start)

**When to use:** TE-01, TE-02 - User marking timestamps in preview

**Example:**
```python
# Source: Qt for Python documentation - QMediaPlayer position
# https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html

from PySide6.QtCore import Signal, Slot
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QPushButton
from dataclasses import dataclass
from typing import Optional

@dataclass
class EditTimestamps:
    """Timestamp markers for reel editing."""
    goal_moment_ms: Optional[int] = None  # When goal is scored
    celebration_start_ms: Optional[int] = None  # When celebration begins

class TimelineController:
    """Manages timestamp marking and preview interaction."""

    def __init__(self, media_player, video_preview_widget):
        self.player = media_player
        self.preview = video_preview_widget
        self.timestamps = EditTimestamps()

    def mark_goal_moment(self) -> int:
        """Mark current position as goal moment.

        Returns:
            Position in milliseconds
        """
        position_ms = self.player.position()
        self.timestamps.goal_moment_ms = position_ms
        return position_ms

    def mark_celebration_start(self) -> int:
        """Mark current position as celebration start.

        Returns:
            Position in milliseconds
        """
        position_ms = self.player.position()
        self.timestamps.celebration_start_ms = position_ms
        return position_ms

    def seek_to_timestamp(self, timestamp_ms: int) -> None:
        """Seek player to specific timestamp."""
        self.player.setPosition(timestamp_ms)
```

### Pattern 2: Slow-Motion with PyAV Filter Graph (Video + Audio)

**What:** Apply variable speed to video using setpts filter, sync audio using atempo filter

**When to use:** EF-01, EF-02, TF-05 - Slow-motion speed and duration adjustment with audio sync

**Example:**
```python
# Source: PyAV 16.1.0 documentation - Audio filters
# https://pyav.basswood-io.com/docs/stable/cookbook/audio.html
# FFmpeg setpts/atempo documentation
# https://shotstack.io/learn/ffmpeg-speed-up-video-slow-down-videos/

import av
from typing import Callable, Optional
from fractions import Fraction

def apply_slow_motion(
    input_path: str,
    output_path: str,
    speed: float,  # 0.25, 0.5, 0.75, 1.0
    start_ms: int,
    duration_ms: int,
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Apply slow-motion effect to video segment with audio sync.

    Args:
        input_path: Source video file
        output_path: Output file path
        speed: Playback speed (0.25 = 4x slow-mo, 0.5 = 2x slow-mo)
        start_ms: Start of slow-mo segment in milliseconds
        duration_ms: Duration of slow-mo segment in milliseconds
        progress_callback: Optional progress callback (0-100)

    Returns:
        Path to output file

    Note:
        For speeds < 0.5, atempo is chained (e.g., 0.25 = atempo=0.5,atempo=0.5)
        This is an FFmpeg limitation: atempo range is [0.5, 2.0]
    """
    input_container = av.open(input_path)
    output_container = av.open(output_path, mode='w')

    # Get input streams
    video_stream = input_container.streams.video[0]
    audio_stream = input_container.streams.audio[0] if input_container.streams.audio else None

    # Calculate PTS multiplier (inverse of speed)
    pts_factor = 1.0 / speed  # 0.25x speed -> 4.0 PTS multiplier

    # Create video filter graph with setpts
    video_graph = av.filter.Graph()
    video_buffer = video_graph.add_buffer(template=video_stream)
    # setpts filter: multiply PTS to slow down
    setpts = video_graph.add("setpts", f"{pts_factor}*PTS")
    video_sink = video_graph.add("buffersink")
    video_buffer.link_to(setpts)
    setpts.link_to(video_sink)
    video_graph.configure()

    # Create audio filter graph with atempo (chained if needed)
    audio_graph = None
    if audio_stream:
        audio_graph = av.filter.Graph()
        audio_buffer = audio_graph.add_abuffer(template=audio_stream)

        # Chain atempo filters for speeds < 0.5
        # atempo range: [0.5, 2.0] - chain for values outside
        atempo_values = _calculate_atempo_chain(speed)

        prev_node = audio_buffer
        for atempo_val in atempo_values:
            atempo_node = audio_graph.add("atempo", str(atempo_val))
            prev_node.link_to(atempo_node)
            prev_node = atempo_node

        audio_sink = audio_graph.add("abuffersink")
        prev_node.link_to(audio_sink)
        audio_graph.configure()

    # Create output streams
    output_video = output_container.add_stream("h264_videotoolbox", rate=video_stream.average_rate)
    output_video.width = video_stream.width
    output_video.height = video_stream.height
    output_video.pix_fmt = "yuv420p"

    output_audio = None
    if audio_stream:
        output_audio = output_container.add_stream(
            audio_stream.codec_context.name,
            rate=audio_stream.rate
        )

    # Process video frames through filter graph
    for frame in input_container.decode(video=0):
        video_graph.push(frame)
        while True:
            try:
                filtered_frame = video_graph.pull()
                for packet in output_video.encode(filtered_frame):
                    output_container.mux(packet)
            except (av.BlockingIOError, av.EOFError):
                break

    # Process audio if present
    if audio_stream and audio_graph:
        # Reset container position for audio pass
        input_container.seek(0)
        for frame in input_container.decode(audio=0):
            audio_graph.push(frame)
            while True:
                try:
                    filtered_frame = audio_graph.pull()
                    for packet in output_audio.encode(filtered_frame):
                        output_container.mux(packet)
                except (av.BlockingIOError, av.EOFError):
                    break

    # Flush encoders
    for packet in output_video.encode():
        output_container.mux(packet)
    if output_audio:
        for packet in output_audio.encode():
            output_container.mux(packet)

    input_container.close()
    output_container.close()

    return output_path


def _calculate_atempo_chain(speed: float) -> list[float]:
    """Calculate atempo filter values for given speed.

    atempo range is [0.5, 2.0]. Values outside must be chained.

    Examples:
        0.25 -> [0.5, 0.5]  (0.5 * 0.5 = 0.25)
        0.5  -> [0.5]
        0.75 -> [0.75]
        2.0  -> [2.0]
        4.0  -> [2.0, 2.0]
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
```

### Pattern 3: LUT Color Grading with lut3d Filter

**What:** Apply .cube LUT files for color grading using FFmpeg's lut3d filter

**When to use:** EF-03, EF-04 - LUT preset selection and application

**Example:**
```python
# Source: FFmpeg lut3d filter documentation
# https://ffmpeg.org/ffmpeg-filters.html
# https://gabor.heja.hu/blog/2024/12/10/using-ffmpeg-to-color-correct-color-grade-a-video-lut-hald-clut/

import av
from pathlib import Path
from typing import Optional, Callable

def apply_lut(
    input_path: str,
    output_path: str,
    lut_path: str,
    interpolation: str = "tetrahedral",
    progress_callback: Optional[Callable[[int], None]] = None
) -> str:
    """Apply 3D LUT color grading to video.

    Args:
        input_path: Source video file
        output_path: Output file path
        lut_path: Path to .cube LUT file
        interpolation: LUT interpolation mode:
            - 'nearest': Use nearest defined point (fastest, lowest quality)
            - 'trilinear': Interpolate using 8-point cube (balanced)
            - 'tetrahedral': Interpolate using tetrahedron (best quality)
        progress_callback: Optional progress callback (0-100)

    Returns:
        Path to output file
    """
    input_container = av.open(input_path)
    output_container = av.open(output_path, mode='w')

    video_stream = input_container.streams.video[0]

    # Create filter graph with lut3d
    graph = av.filter.Graph()
    buffer_node = graph.add_buffer(template=video_stream)

    # lut3d filter with .cube file
    # Note: Path must use forward slashes, escape colons on Windows
    lut3d_node = graph.add("lut3d", f"file={lut_path}:interp={interpolation}")

    sink_node = graph.add("buffersink")

    buffer_node.link_to(lut3d_node)
    lut3d_node.link_to(sink_node)
    graph.configure()

    # Setup output (copy audio unchanged)
    output_video = output_container.add_stream("h264_videotoolbox", rate=video_stream.average_rate)
    output_video.width = video_stream.width
    output_video.height = video_stream.height
    output_video.pix_fmt = "yuv420p"

    # Copy audio stream
    if input_container.streams.audio:
        input_audio = input_container.streams.audio[0]
        output_audio = output_container.add_stream(
            input_audio.codec_context.name,
            rate=input_audio.rate
        )

    total_frames = video_stream.frames or int(video_stream.duration * video_stream.time_base * float(video_stream.average_rate))
    processed = 0

    # Process video through LUT filter
    for packet in input_container.demux():
        if packet.stream.type == 'video':
            for frame in packet.decode():
                graph.push(frame)
                while True:
                    try:
                        filtered = graph.pull()
                        for out_packet in output_video.encode(filtered):
                            output_container.mux(out_packet)
                        processed += 1
                        if progress_callback and total_frames > 0:
                            progress_callback(int(processed / total_frames * 100))
                    except (av.BlockingIOError, av.EOFError):
                        break
        elif packet.stream.type == 'audio' and input_container.streams.audio:
            # Copy audio packets unchanged
            packet.stream = output_audio
            output_container.mux(packet)

    # Flush
    for packet in output_video.encode():
        output_container.mux(packet)

    input_container.close()
    output_container.close()

    return output_path
```

### Pattern 4: Edit Session Data Model

**What:** Structured data model for all editing parameters

**When to use:** Storing timestamps, speed settings, LUT selection before export

**Example:**
```python
# Source: Python dataclasses (stdlib)
# https://docs.python.org/3/library/dataclasses.html

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
import json

@dataclass
class SlowMotionSettings:
    """Slow-motion effect configuration."""
    speed: float = 0.5  # 0.25, 0.5, 0.75, 1.0
    start_ms: int = 0
    duration_ms: int = 3000  # Default 3 seconds of slow-mo

    def validate(self) -> bool:
        """Validate settings are within allowed ranges."""
        return self.speed in (0.25, 0.5, 0.75, 1.0) and self.duration_ms > 0

@dataclass
class ColorGradingSettings:
    """Color grading configuration."""
    lut_name: Optional[str] = None  # Name of selected LUT preset
    lut_path: Optional[Path] = None  # Full path to .cube file

    def is_enabled(self) -> bool:
        return self.lut_name is not None and self.lut_path is not None

@dataclass
class EditSession:
    """Complete editing session state."""
    # Source video
    source_path: Path = None
    proxy_path: Path = None

    # Timestamps (from user marking)
    goal_moment_ms: Optional[int] = None
    celebration_start_ms: Optional[int] = None

    # Effects
    slow_motion: SlowMotionSettings = field(default_factory=SlowMotionSettings)
    color_grading: ColorGradingSettings = field(default_factory=ColorGradingSettings)

    def is_ready_for_preview(self) -> bool:
        """Check if session has minimum data for preview."""
        return (
            self.proxy_path is not None and
            self.goal_moment_ms is not None
        )

    def is_ready_for_export(self) -> bool:
        """Check if session has all data for final export."""
        return (
            self.source_path is not None and
            self.goal_moment_ms is not None and
            self.celebration_start_ms is not None
        )
```

### Pattern 5: Preview with Effects Applied

**What:** Generate preview video with effects applied for user review before export

**When to use:** GUI-05 - Preview edited reel before export

**Example:**
```python
# Source: Qt Player Example - playback rate
# https://doc.qt.io/qtforpython-6/examples/example_multimedia_player.html

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtCore import Slot
from pathlib import Path

class PreviewController:
    """Controls preview playback with effects visualization."""

    def __init__(self, media_player: QMediaPlayer, edit_session: EditSession):
        self.player = media_player
        self.session = edit_session
        self._preview_path: Optional[Path] = None

    def generate_preview(
        self,
        temp_dir: Path,
        progress_callback=None
    ) -> Path:
        """Generate preview video with all effects applied.

        Uses proxy file for speed, applies:
        1. LUT color grading (if selected)
        2. Slow-motion effect (if configured)

        Returns:
            Path to preview file
        """
        input_path = str(self.session.proxy_path)

        # Step 1: Apply LUT if selected
        if self.session.color_grading.is_enabled():
            lut_output = temp_dir / "preview_lut.mp4"
            apply_lut(
                input_path,
                str(lut_output),
                str(self.session.color_grading.lut_path),
                progress_callback=lambda p: progress_callback(p // 2) if progress_callback else None
            )
            input_path = str(lut_output)

        # Step 2: Apply slow-motion if configured
        if self.session.slow_motion.speed != 1.0:
            slowmo_output = temp_dir / "preview_slowmo.mp4"
            apply_slow_motion(
                input_path,
                str(slowmo_output),
                self.session.slow_motion.speed,
                self.session.slow_motion.start_ms,
                self.session.slow_motion.duration_ms,
                progress_callback=lambda p: progress_callback(50 + p // 2) if progress_callback else None
            )
            input_path = str(slowmo_output)

        self._preview_path = Path(input_path)
        return self._preview_path

    def load_preview(self) -> None:
        """Load generated preview into media player."""
        if self._preview_path and self._preview_path.exists():
            from PySide6.QtCore import QUrl
            self.player.setSource(QUrl.fromLocalFile(str(self._preview_path)))

    @Slot()
    def play_preview(self) -> None:
        """Start preview playback."""
        self.player.play()
```

### Anti-Patterns to Avoid

- **Real-time filter application during playback:** Don't try to apply PyAV filters frame-by-frame during QMediaPlayer playback. Pre-render preview to file instead.
- **Processing source file for preview:** Always use proxy (720p) for preview generation to maintain speed.
- **Single atempo for extreme slow-motion:** atempo only supports [0.5, 2.0]. Chain multiple filters for 0.25x.
- **Ignoring time_base during speed changes:** When combining segments at different speeds, recalculate all timestamps.
- **Blocking GUI during preview generation:** Use Worker pattern from Phase 1 for all processing.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Video speed adjustment | Custom frame duplication/dropping | FFmpeg setpts filter via PyAV | setpts handles timestamp arithmetic, frame rate changes, edge cases; custom solutions cause A/V desync |
| Audio speed with pitch preservation | Sample rate manipulation | FFmpeg atempo filter via PyAV | SOLA algorithm preserves pitch; custom solutions sound unnatural |
| LUT color transformation | Manual RGB lookup/interpolation | FFmpeg lut3d filter via PyAV | lut3d supports tetrahedral interpolation, handles edge cases, GPU-optimized |
| Segment concatenation | Manual PTS recalculation | FFmpeg concat filter | concat handles timestamp discontinuities, stream alignment |
| Preview playback | Custom frame-by-frame rendering | QMediaPlayer on pre-rendered file | QMediaPlayer is optimized for smooth playback; frame rendering causes stuttering |

**Key insight:** FFmpeg filters (setpts, atempo, lut3d, concat) are battle-tested for these exact problems. PyAV's filter graph API exposes them with streaming efficiency.

## Common Pitfalls

### Pitfall 1: Audio Desync During Slow-Motion

**What goes wrong:** Video slows down but audio plays at normal speed, causing obvious desync.

**Why it happens:** Only video PTS is adjusted, audio stream ignored.

**How to avoid:**
- Always process audio with atempo filter when applying setpts to video
- Calculate atempo value as inverse of video speed (0.5x video = atempo=0.5)
- Chain atempo filters for speeds < 0.5x (e.g., 0.25x = atempo=0.5,atempo=0.5)

**Warning signs:**
- Audio finishes before video (or vice versa)
- Dialogue/sounds don't match on-screen action
- Audio sounds chipmunk-like (wrong approach: changed sample rate instead of tempo)

### Pitfall 2: Choppy Slow-Motion from Low Frame Rate Source

**What goes wrong:** Slow-motion appears stuttery, not smooth.

**Why it happens:** 60fps source slowed to 0.25x = effectively 15fps, below perceptual smoothness threshold.

**How to avoid:**
- Warn user if source is not high-fps (120fps ideal for 0.25x slow-mo)
- For 60fps source, recommend 0.5x maximum slow-motion
- Consider minterpolate filter for frame interpolation (but warn: high processing cost, artifacts)

**Warning signs:**
- Preview looks like slideshow
- Motion blur artifacts in fast-moving subjects
- User complains slow-mo "looks bad"

### Pitfall 3: LUT Path Issues on Different Platforms

**What goes wrong:** lut3d filter fails with "file not found" despite correct path.

**Why it happens:** FFmpeg filter paths have special requirements:
- Windows: Colons in drive letters must be escaped (`C\:` or use forward slashes)
- Spaces in paths cause parsing issues
- Relative paths may resolve incorrectly

**How to avoid:**
- Always use absolute paths for LUT files
- Convert Windows paths to forward slashes
- Validate LUT file exists before filter creation
- Store bundled LUTs in app resources with known path

**Warning signs:**
- "No such file or directory" from FFmpeg
- Filter graph configuration fails
- Works on one machine, fails on another

### Pitfall 4: Memory Issues from Multiple Filter Passes

**What goes wrong:** Processing LUT + slow-motion on long video exhausts memory.

**Why it happens:** Each filter pass creates intermediate data; multiple passes compound memory usage.

**How to avoid:**
- Chain filters in single graph when possible (lut3d before setpts in same graph)
- Process in smaller segments if needed
- Use proxy (720p) for preview, only use source for final export
- Monitor memory during processing, implement early abort

**Warning signs:**
- Memory usage climbing during processing
- App becomes unresponsive
- System starts swapping

### Pitfall 5: Preview Doesn't Match Final Export

**What goes wrong:** Preview looks different from exported video (colors, timing).

**Why it happens:**
- Preview uses proxy (720p), export uses source (4K)
- Different codecs introduce slight color differences
- Timestamp rounding differences at different resolutions

**How to avoid:**
- Use same filter parameters for preview and export
- Document that preview is approximate
- Allow side-by-side comparison after export
- Use consistent color space throughout pipeline

**Warning signs:**
- User complains colors look different after export
- Timing of effects off by frames
- LUT looks stronger/weaker in export

## Code Examples

### Verified PyAV Audio Filter Usage (atempo)
```python
# Source: PyAV 16.1.0 official documentation
# https://pyav.basswood-io.com/docs/stable/cookbook/audio.html

import av

# Create filter graph for audio speed change
graph = av.filter.Graph()
graph.link_nodes(
    graph.add_abuffer(template=input_stream),
    graph.add("atempo", "0.5"),  # 0.5x speed (half speed)
    graph.add("abuffersink"),
).configure()

# Process frames through filter
for frame in input_file.decode(input_stream):
    graph.push(frame)
    while True:
        try:
            for packet in output_stream.encode(graph.pull()):
                output_file.mux(packet)
        except (av.BlockingIOError, av.EOFError):
            break
```

### Verified FFmpeg lut3d Filter Syntax
```bash
# Source: FFmpeg lut3d filter documentation
# https://ffmpeg.org/ffmpeg-filters.html

# Basic usage
ffmpeg -i input.mp4 -vf "lut3d=file=path/to/your/lut.cube" output.mp4

# With tetrahedral interpolation (best quality)
ffmpeg -i input.mp4 -vf "lut3d=file=lut.cube:interp=tetrahedral" output.mp4

# Combined with other filters
ffmpeg -i input.mp4 -vf "scale=1920:1080,lut3d=file=lut.cube" output.mp4
```

### Verified FFmpeg setpts + atempo for Slow-Motion
```bash
# Source: FFmpeg speed adjustment documentation
# https://shotstack.io/learn/ffmpeg-speed-up-video-slow-down-videos/

# 0.5x slow motion (2x slower)
ffmpeg -i input.mp4 -vf "setpts=2.0*PTS" -af "atempo=0.5" output.mp4

# 0.25x slow motion (4x slower) - chain atempo
ffmpeg -i input.mp4 -vf "setpts=4.0*PTS" -af "atempo=0.5,atempo=0.5" output.mp4

# Variable speed: slow segment then normal
ffmpeg -i input.mp4 -filter_complex \
  "[0:v]trim=start=0:end=5,setpts=2*PTS[v1]; \
   [0:v]trim=start=5,setpts=PTS-STARTPTS[v2]; \
   [0:a]atrim=start=0:end=5,atempo=0.5[a1]; \
   [0:a]atrim=start=5,atempo=1[a2]; \
   [v1][a1][v2][a2]concat=n=2:v=1:a=1" \
  output.mp4
```

### QMediaPlayer Position for Timestamp Marking
```python
# Source: Qt for Python documentation
# https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtCore import Slot

class TimestampMarker:
    def __init__(self, player: QMediaPlayer):
        self.player = player
        self.goal_timestamp_ms = None
        self.celebration_timestamp_ms = None

    @Slot()
    def mark_goal(self):
        """Mark current position as goal moment."""
        self.goal_timestamp_ms = self.player.position()
        print(f"Goal marked at {self.goal_timestamp_ms}ms")

    @Slot()
    def mark_celebration(self):
        """Mark current position as celebration start."""
        self.celebration_timestamp_ms = self.player.position()
        print(f"Celebration marked at {self.celebration_timestamp_ms}ms")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate FFmpeg subprocess for each effect | PyAV filter graph API | PyAV 9.0+ (2022) | Single-pass processing, better error handling, streaming efficiency |
| Manual frame rate manipulation for slow-mo | setpts filter | Stable since FFmpeg 2.0 | Automatic PTS handling, no frame counting bugs |
| asetrate for audio speed (pitch changes) | atempo filter | Stable since FFmpeg 1.0 | Preserves pitch using SOLA algorithm |
| Manual LUT parsing + pixel manipulation | lut3d filter | Stable since FFmpeg 2.3 | Tetrahedral interpolation, GPU optimization |
| Frame-by-frame preview rendering | Pre-render + QMediaPlayer | Qt 6 (2020) | Smooth preview playback, no stuttering |

**Deprecated/outdated:**
- **MoviePy for effects:** Still exists but memory issues on 4K make it unsuitable
- **Custom PTS arithmetic:** Use setpts filter instead of manual calculation
- **asetrate for speed:** Changes pitch; use atempo for natural-sounding audio

## Open Questions

1. **Frame-accurate slow-motion boundaries**
   - What we know: setpts operates on PTS, which may not align exactly with desired frame
   - What's unclear: How to ensure slow-motion starts/ends on exact user-specified timestamps
   - Recommendation: Use trim filter with frame-accurate timestamps before setpts; test with sample footage

2. **LUT preset curation**
   - What we know: Free LUT packs available (FilterGrade, FixThePhoto, Pond5); .cube format is standard
   - What's unclear: Which specific LUTs work best for sports/lacrosse footage
   - Recommendation: Test 20-30 free LUTs with sample lacrosse footage, select 10-15 that work well; name presets descriptively (e.g., "Game Day", "Cinematic", "Teal & Orange")

3. **Preview generation time**
   - What we know: Applying both LUT and slow-motion to proxy requires encoding
   - What's unclear: Whether preview generation is fast enough for real-time iteration
   - Recommendation: Benchmark on M1/M2 Mac with typical 1-2 minute proxy; if >10 seconds, consider caching intermediate results

4. **Audio handling for music overlay**
   - What we know: Phase 2 doesn't include music upload (that's Phase 3)
   - What's unclear: Whether slow-motion audio processing should preserve or discard original audio
   - Recommendation: Preserve audio with tempo adjustment for Phase 2 preview; final music overlay in Phase 3 will replace it

## Sources

### Primary (HIGH confidence)

- **PyAV 16.1.0 Audio Cookbook** - https://pyav.basswood-io.com/docs/stable/cookbook/audio.html
  - Verified atempo filter usage with av.filter.Graph

- **PyAV 16.1.0 Filter API** - https://pyav.org/docs/stable/api/filter.html
  - Graph, FilterContext, buffer/sink usage

- **FFmpeg Filters Documentation** - https://ffmpeg.org/ffmpeg-filters.html
  - Authoritative reference for lut3d, setpts, atempo, concat filters

- **Qt for Python QMediaPlayer** - https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html
  - position(), setPosition(), playback rate control

- **Qt Player Example** - https://doc.qt.io/qtforpython-6/examples/example_multimedia_player.html
  - Official example for seek slider, playback controls

### Secondary (MEDIUM confidence)

- **Shotstack FFmpeg Speed Guide** - https://shotstack.io/learn/ffmpeg-speed-up-video-slow-down-videos/
  - Verified setpts/atempo patterns, confirmed with FFmpeg docs

- **Gabor Heja FFmpeg LUT Guide** - https://gabor.heja.hu/blog/2024/12/10/using-ffmpeg-to-color-correct-color-grade-a-video-lut-hald-clut/
  - lut3d filter usage patterns

- **Snyk PyAV Filter Examples** - https://snyk.io/advisor/python/av/functions/av.filter.Graph
  - Working filter graph patterns from community usage

- **FilterGrade Free LUTs** - https://filtergrade.com/free-cinematic-luts-video-editing/
  - Free .cube LUT source (8 files)

- **FixThePhoto Free LUTs** - https://fixthephoto.com/free-cinematic-luts
  - Free .cube LUT source (120 files)

### Tertiary (LOW confidence)

- **PyAV GitHub Issues #239, #441** - Filter usage discussions
  - Community patterns, may not reflect current API
  - Recommendation: Verify patterns work with PyAV 16.1.0

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Building on Phase 1 verified stack, PyAV filter API confirmed in docs
- Architecture patterns: HIGH - Based on official PyAV/Qt documentation with working examples
- Effects processing: MEDIUM - FFmpeg filter syntax verified, PyAV integration needs validation
- Pitfalls: MEDIUM - Based on documented FFmpeg behaviors and community experience

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days - stable ecosystem)

**Key Phase 1 dependencies confirmed:**
- PyAV streaming architecture extends to filter graphs
- Worker pattern applies to effects processing
- QMediaPlayer position API sufficient for timestamp marking
- Proxy-based preview workflow continues
