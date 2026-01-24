# Architecture Research

**Domain:** Mac Desktop Video Editing Automation
**Researched:** 2026-01-24
**Confidence:** MEDIUM

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GUI Layer (AppKit/PyObjC)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ File Mgmt UI │  │ Timeline UI  │  │ Effects UI   │  │ Preview UI  │ │
│  │ (drag-drop)  │  │              │  │              │  │ (playback)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
├─────────┼──────────────────┼──────────────────┼──────────────────┼──────┤
│         │          Async Task Queue (Celery/TaskIQ)              │      │
│         │                        ↓                                │      │
│         └────────────────────────┴────────────────────────────────┘      │
├─────────────────────────────────────────────────────────────────────────┤
│                      Processing Engine Layer                             │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Video         │  │ Music Sync    │  │ Effects      │  │ Export    │ │
│  │ Processor     │  │ Engine        │  │ Processor    │  │ Renderer  │ │
│  │ (FFmpeg)      │  │ (Beat detect) │  │ (Filters)    │  │ (9:16)    │ │
│  └───────┬───────┘  └───────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
├──────────┼──────────────────┼──────────────────┼──────────────────┼─────┤
│          │          Processing Pipeline Coordination               │     │
│          └────────────────────────┬────────────────────────────────┘     │
├─────────────────────────────────────────────────────────────────────────┤
│                      Storage & Cache Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ Source Files │  │ Proxy Cache  │  │ Preview      │  │ Final       │ │
│  │ (Original)   │  │ (Lower res)  │  │ Renders      │  │ Exports     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **GUI Layer** | User interactions, file drag-drop, simple controls for non-technical users, preview playback | PyObjC + AppKit (native Mac controls), single-threaded event loop |
| **Async Task Queue** | Decouples GUI from long-running video processing, maintains responsiveness, manages background jobs | Celery with Redis backend, or TaskIQ for modern async support |
| **Video Processor** | 4K 60-120fps processing, slow-mo, trimming, format conversion, hardware acceleration | FFmpeg via ffmpeg-python bindings, NVIDIA VPF for GPU accel, or VidGear framework |
| **Music Sync Engine** | Audio analysis, beat detection, tempo tracking, auto-sync markers | Librosa for beat detection, onset detection algorithms, ML models for musical structure |
| **Effects Processor** | Color grading (LUTs), transitions, filters, compositing | FFmpeg filters, custom Python processing, GPU-accelerated transforms |
| **Export Renderer** | 9:16 vertical format optimization, social media presets (1080x1920), final encoding | FFmpeg with NVENC/Metal hardware encoding, preset templates for TikTok/Reels |
| **Proxy/Cache System** | Generate lower-res proxies for smooth editing, cache processed segments, manage memory | NVMe SSD storage, automated proxy generation with hardware acceleration |

## Recommended Project Structure

```
video-automation-app/
├── src/
│   ├── gui/                    # GUI Layer (PyObjC/AppKit)
│   │   ├── __init__.py
│   │   ├── main_window.py      # Main application window
│   │   ├── file_manager.py     # Drag-drop file handling
│   │   ├── timeline_view.py    # Timeline UI component
│   │   ├── preview_player.py   # Video preview/playback
│   │   └── effects_panel.py    # Effects controls UI
│   │
│   ├── processing/             # Processing Engine Layer
│   │   ├── __init__.py
│   │   ├── video_processor.py  # Core video processing (FFmpeg wrapper)
│   │   ├── beat_detector.py    # Music sync and beat detection
│   │   ├── effects_engine.py   # Effects and color grading
│   │   └── export_engine.py    # Final rendering and export
│   │
│   ├── tasks/                  # Async Task Definitions
│   │   ├── __init__.py
│   │   ├── processing_tasks.py # Celery/TaskIQ task definitions
│   │   └── callbacks.py        # Progress callbacks to GUI
│   │
│   ├── models/                 # Data Models
│   │   ├── __init__.py
│   │   ├── project.py          # Project data structure
│   │   ├── timeline.py         # Timeline and clip data
│   │   └── effects.py          # Effects parameters
│   │
│   ├── storage/                # Storage Layer
│   │   ├── __init__.py
│   │   ├── proxy_manager.py    # Proxy generation/management
│   │   ├── cache_manager.py    # Cache coordination
│   │   └── file_manager.py     # File I/O operations
│   │
│   └── utils/                  # Utilities
│       ├── __init__.py
│       ├── hardware_detect.py  # Detect GPU/Metal capabilities
│       └── config.py           # App configuration
│
├── tests/                      # Tests
├── resources/                  # Static resources
│   ├── luts/                   # Color grading LUTs
│   └── presets/                # Export presets
│
├── requirements.txt
├── setup.py
└── config.yaml                 # App configuration
```

### Structure Rationale

- **gui/:** Completely separate GUI logic from processing. PyObjC/AppKit code is notoriously stateful and Mac-specific, so isolating it allows the processing layer to be portable and testable.
- **processing/:** Pure Python video processing logic. Each processor is independent and composable. Can be tested without GUI and potentially reused in CLI tools.
- **tasks/:** Async task definitions bridge GUI and processing layers. Enables responsive UI by offloading heavy work to background workers.
- **models/:** Data structures represent project state. Separating models from GUI and processing enables easier serialization for save/load functionality.
- **storage/:** Centralized file management, proxy generation, and caching. Critical for handling 150MB+ files efficiently without overwhelming memory.

## Architectural Patterns

### Pattern 1: Producer-Consumer with Task Queue

**What:** GUI acts as Producer submitting tasks; background workers act as Consumers processing video operations asynchronously.

**When to use:** Essential for video processing to maintain GUI responsiveness. Video operations (trimming, effects, export) can take seconds to minutes.

**Trade-offs:**
- **Pros:** Non-blocking UI, scalable (can add more workers), enables progress reporting
- **Cons:** Added complexity (message broker required), harder to debug, requires careful state management

**Example:**
```python
# GUI Layer - Producer
from tasks.processing_tasks import process_video_task

def on_apply_effects_clicked(self, video_path, effects_params):
    # Submit task and return immediately
    task = process_video_task.delay(video_path, effects_params)
    self.show_progress_dialog(task.id)

# Processing Layer - Consumer
@celery_app.task(bind=True)
def process_video_task(self, video_path, effects_params):
    processor = VideoProcessor()
    processor.apply_effects(video_path, effects_params,
                           progress_callback=lambda p: self.update_state(state='PROGRESS', meta={'progress': p}))
    return {'status': 'complete', 'output_path': '/path/to/output.mp4'}
```

### Pattern 2: Proxy Workflow for Large Files

**What:** Generate low-resolution proxy files for editing; use original high-res files only for final export.

**When to use:** Essential when working with 4K 60fps+ footage or files 150MB+. Enables smooth timeline scrubbing and preview.

**Trade-offs:**
- **Pros:** Dramatically improves editing performance, reduces memory pressure, enables lower-spec hardware
- **Cons:** Requires upfront processing time, additional storage (typically 10-20% of original), complexity in switching between proxy/original

**Example:**
```python
class ProxyManager:
    def generate_proxy(self, source_path, target_resolution=(960, 540)):
        """Generate H.264 proxy at lower resolution with hardware acceleration."""
        proxy_path = self._get_proxy_path(source_path)

        # Use FFmpeg with hardware acceleration (Metal on Mac)
        (
            ffmpeg
            .input(source_path)
            .output(proxy_path,
                   vcodec='h264_videotoolbox',  # Metal hardware encoding
                   s=f'{target_resolution[0]}x{target_resolution[1]}',
                   crf=28)  # Lower quality for faster processing
            .run()
        )

        return proxy_path
```

### Pattern 3: Pipeline-Based Processing

**What:** Chain video operations as a pipeline where output of one stage feeds input of next. Buffer between stages to handle variable processing speeds.

**When to use:** For multi-step video processing (trim → effects → music sync → export). Prevents memory overflow and enables parallelization.

**Trade-offs:**
- **Pros:** Memory efficient (streaming), parallelizable, composable operations
- **Cons:** More complex error handling, harder to debug middle stages, requires careful buffer sizing

**Example:**
```python
class ProcessingPipeline:
    def __init__(self):
        self.stages = []

    def add_stage(self, processor_func):
        self.stages.append(processor_func)

    def execute(self, input_path, output_path):
        """Execute pipeline with intermediate buffering."""
        current_path = input_path

        for i, stage in enumerate(self.stages):
            intermediate_path = f'/tmp/stage_{i}_output.mp4'
            stage(current_path, intermediate_path)
            current_path = intermediate_path

        # Final stage outputs to desired path
        shutil.move(current_path, output_path)

# Usage
pipeline = ProcessingPipeline()
pipeline.add_stage(lambda inp, out: trim_video(inp, out, start=5, end=30))
pipeline.add_stage(lambda inp, out: apply_color_grade(inp, out, lut='cinematic'))
pipeline.add_stage(lambda inp, out: sync_to_beat(inp, out, audio_path='music.mp3'))
pipeline.add_stage(lambda inp, out: export_vertical(inp, out, resolution=(1080, 1920)))
pipeline.execute('source.mp4', 'final.mp4')
```

### Pattern 4: Separation of Concerns (GUI ↔ Backend)

**What:** Strict boundary between GUI layer (PyObjC/AppKit) and processing layer (Python). Communication only via well-defined interfaces (task queue, data models).

**When to use:** Always. Essential for maintainability, testability, and enabling future GUI alternatives (CLI, web interface).

**Trade-offs:**
- **Pros:** Testable backend without GUI, parallel development, easier debugging, reusable components
- **Cons:** More boilerplate code, requires discipline to maintain boundaries

**Example:**
```python
# Processing Layer - Pure Python, no GUI dependencies
class VideoProcessor:
    def process(self, source_path, operations, progress_callback=None):
        """Pure processing logic with callback for progress."""
        for i, op in enumerate(operations):
            op.apply(source_path)
            if progress_callback:
                progress_callback(int((i + 1) / len(operations) * 100))

# GUI Layer - PyObjC/AppKit
class TimelineViewController(NSViewController):
    def apply_effects(self):
        operations = self._build_operations_from_ui()
        task = process_video_task.delay(self.video_path, operations)
        self._monitor_task_progress(task.id)

    def _monitor_task_progress(self, task_id):
        # Poll task state and update progress bar
        pass
```

## Data Flow

### Request Flow

```
[User Drags File] → [File Manager UI]
        ↓
[Validate & Generate Proxy] → [Proxy Manager]
        ↓
[Display in Timeline] ← [Timeline UI]
        ↓
[User Adds Effects] → [Effects Panel UI]
        ↓
[Submit Processing Task] → [Task Queue] → [Video Processor Worker]
        ↓                                          ↓
[Update Progress UI] ←─────[Progress Callback]───┘
        ↓
[Preview Result] → [Preview Player]
        ↓
[User Clicks Export] → [Export Task] → [Export Engine Worker]
        ↓                                      ↓
[Show Completion] ←──────[Task Complete]──────┘
        ↓
[Open in Finder] → [Final 9:16 MP4]
```

### Processing Pipeline Data Flow

```
Source Video (4K 60fps)
    ↓
[Proxy Generation] → Proxy Video (960x540 H.264)
    ↓ (editing with proxy)
[Timeline Edits]
    ↓ (trim, split, arrange)
[Beat Detection] → Audio Analysis → Beat Markers
    ↓
[Music Sync] → Align cuts to beats
    ↓
[Effects Application]
    ├─ Color Grading (LUT)
    ├─ Transitions
    └─ Filters
    ↓
[Export Preparation]
    ├─ Switch to original high-res source
    ├─ Apply 9:16 crop/scale
    └─ Render with hardware acceleration
    ↓
Final Export (1080x1920 H.264/HEVC)
```

### State Management

```
[Project Model]
    ↓ (save/load)
[File System] → project.json
    ↓
[Timeline Model]
    ├─ Clips (source, in/out points, effects)
    ├─ Audio tracks
    └─ Beat markers
    ↓
[Effects Model]
    ├─ Color grade settings
    ├─ Transition types
    └─ Filter parameters
    ↓
[Export Settings]
    ├─ Format (9:16 vertical)
    ├─ Resolution (1080x1920)
    └─ Codec (H.264/HEVC)
```

### Key Data Flows

1. **File Ingestion Flow:** Source file → Validation → Proxy generation → Timeline display. Critical to validate file format/codec early and generate proxy asynchronously to avoid blocking UI.

2. **Beat Sync Flow:** Audio file → FFT/onset detection → Beat timestamps → Timeline markers → Auto-cut alignment. Processing audio separately from video enables faster iteration on sync points.

3. **Effects Preview Flow:** Proxy video + Effects params → Quick render (low quality) → Preview player. Using proxies for preview enables real-time feedback; full quality only rendered on export.

4. **Export Flow:** Original source + Timeline edits + Effects → Processing pipeline → Hardware-accelerated encoding → 9:16 MP4 output. Switching from proxy to original only at export time maximizes quality while maintaining editing performance.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Single user, 1-5 projects** | Monolithic app with local task queue (single worker). Proxy files optional for <4K footage. Local SSD storage sufficient. |
| **Single user, 10+ projects or 4K+ footage** | Must implement proxy workflow. Multi-worker task queue (2-4 workers) for parallel processing. NVMe SSD required. Implement cache management to avoid filling disk. |
| **Multiple users or cloud processing** | Distributed task queue with Redis backend. Separate worker machines with GPU acceleration. Network storage (NAS with 10GbE). Implement project locking to prevent conflicts. |

### Scaling Priorities

1. **First bottleneck: Memory exhaustion with large files (150MB+)**
   - **Symptoms:** App crashes or freezes when loading/processing large 4K files
   - **Fix:** Implement proxy workflow immediately. Stream video processing (don't load entire file into memory). Use FFmpeg's streaming APIs rather than loading frames into Python arrays.
   - **Build order implication:** Proxy system must be built before processing large files in Phase 2.

2. **Second bottleneck: Slow export times**
   - **Symptoms:** Export takes 5-10x real-time for 4K 60fps footage
   - **Fix:** Hardware acceleration (Metal on Mac via VideoToolbox, or NVIDIA NVENC if available). Ensure FFmpeg is compiled with hardware encoding support. Consider two-pass encoding for better quality/size ratio.
   - **Build order implication:** Hardware acceleration detection should be built early in Phase 2 to inform codec selection.

3. **Third bottleneck: UI freezing during processing**
   - **Symptoms:** Timeline unresponsive during effects application or export
   - **Fix:** Ensure all processing happens in background workers (task queue). Implement polling-based progress updates (not blocking calls). Consider using asyncio for GUI updates rather than threads.
   - **Build order implication:** Task queue architecture must be in place before adding any heavy processing in Phase 3.

## Anti-Patterns

### Anti-Pattern 1: Loading Entire Video into Memory

**What people do:** Load entire video file into numpy array or similar structure for processing.

**Why it's wrong:** For 4K 60fps video, even 10 seconds is ~500MB uncompressed. A typical 1-minute reel would require 3GB+ of RAM, causing memory exhaustion and crashes.

**Do this instead:** Use FFmpeg's streaming capabilities. Process video frame-by-frame or in small chunks. Let FFmpeg handle decoding and only process frames as needed.

```python
# WRONG
frames = load_entire_video(video_path)  # Loads 3GB into memory!
for frame in frames:
    process_frame(frame)

# RIGHT
for frame in ffmpeg_stream_frames(video_path):
    process_frame(frame)
    # Frame is released from memory after processing
```

### Anti-Pattern 2: Blocking GUI Thread with Processing

**What people do:** Call video processing functions directly from GUI event handlers (button clicks).

**Why it's wrong:** Video processing takes seconds to minutes. GUI becomes completely unresponsive (beachball cursor on Mac), user can't cancel, and OS may mark app as "Not Responding."

**Do this instead:** Always submit processing tasks to background workers via task queue. Update GUI with progress callbacks.

```python
# WRONG - GUI Layer
def on_export_clicked(self):
    output_path = export_video(self.project)  # Blocks for 2 minutes!
    self.show_success_dialog(output_path)

# RIGHT - GUI Layer
def on_export_clicked(self):
    task = export_video_task.delay(self.project)
    self.show_progress_dialog(task.id)
```

### Anti-Pattern 3: No Proxy Workflow for 4K Footage

**What people do:** Edit directly with full 4K 60fps source files, no proxy generation.

**Why it's wrong:** Scrubbing timeline is laggy (1-2 FPS), preview playback stutters, effects previews take 10+ seconds. User experience is terrible and productivity suffers.

**Do this instead:** Generate proxies automatically on import. Use 960x540 or 1280x720 H.264 proxies for editing. Switch to original files only for final export.

```python
# Implementation
class FileManager:
    def import_file(self, source_path):
        # Start proxy generation in background immediately
        if self._is_high_res(source_path):  # 4K or higher
            proxy_task = generate_proxy_task.delay(source_path)
            self.project.add_clip(source_path, proxy_task_id=proxy_task.id)
        else:
            self.project.add_clip(source_path)
```

### Anti-Pattern 4: Synchronous Beat Detection Blocking Import

**What people do:** Analyze audio and detect beats synchronously when importing a music file, before showing it in the UI.

**Why it's wrong:** Beat detection on a 3-minute song can take 5-30 seconds. User is left staring at a loading spinner with no feedback. If detection fails, entire import fails.

**Do this instead:** Import music file immediately and show in UI. Run beat detection asynchronously in background. Update UI with markers when detection completes. Allow manual beat marking as fallback.

```python
# WRONG
def import_music(self, audio_path):
    beats = detect_beats(audio_path)  # Blocks for 30 seconds
    self.timeline.add_audio_track(audio_path, beat_markers=beats)

# RIGHT
def import_music(self, audio_path):
    self.timeline.add_audio_track(audio_path)  # Show immediately
    task = detect_beats_task.delay(audio_path)
    task.then(lambda beats: self.timeline.add_beat_markers(beats))
```

### Anti-Pattern 5: Hardcoded Export Settings

**What people do:** Hardcode 9:16 vertical export settings (1080x1920, H.264, specific bitrate) directly in export code.

**Why it's wrong:** Different social platforms have different requirements (TikTok vs Instagram Reels vs YouTube Shorts). Hardcoded settings make it impossible to adjust without code changes. User can't customize for their workflow.

**Do this instead:** Create preset system with JSON/YAML configs. Allow user to select preset or customize. Separate export settings from export logic.

```python
# Export presets stored in resources/presets/
# tiktok.json
{
  "name": "TikTok Vertical",
  "resolution": [1080, 1920],
  "aspect_ratio": "9:16",
  "codec": "h264",
  "bitrate": "5000k",
  "fps": 60
}

# Export engine uses presets
class ExportEngine:
    def export(self, project, preset_name='tiktok'):
        preset = self.load_preset(preset_name)
        # Use preset settings...
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **FFmpeg** | Command-line subprocess or ffmpeg-python library | Core dependency. Ensure FFmpeg compiled with hardware acceleration (VideoToolbox for Mac). Use ffmpeg-python for complex filter graphs. |
| **Librosa** | Python library import | For beat detection and audio analysis. Heavy dependency (~100MB with scipy/numpy). Consider lazy loading. |
| **Celery/TaskIQ** | Python library with Redis/RabbitMQ broker | For async task queue. TaskIQ more modern with native async support; Celery more mature ecosystem. |
| **PyObjC** | Python library, bridges to macOS AppKit | Core GUI framework. Large API surface, refer to docs frequently. Memory management can be tricky (Objective-C reference counting). |
| **Hardware Acceleration** | FFmpeg VideoToolbox (Metal) or NVIDIA NVENC | Critical for export performance. Must detect capabilities at runtime (not all Macs have discrete GPUs). |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **GUI ↔ Processing** | Task Queue (async messaging) | Strict separation. GUI never calls processing directly. All communication via task submission + progress callbacks. |
| **Processing ↔ Storage** | Direct Python function calls | Processing layer can directly call storage functions (load/save files, manage cache). Storage layer is stateless utility functions. |
| **GUI ↔ Models** | Direct Python object access | GUI reads/writes data models directly. Models are plain Python classes (dataclasses) with no business logic. |
| **Beat Detection ↔ Timeline** | Return beat timestamps as list | Beat detector returns `List[float]` of timestamps in seconds. Timeline converts to markers and manages display. |
| **Effects Engine ↔ Video Processor** | Pipeline chaining | Effects engine generates FFmpeg filter graph. Video processor executes it via FFmpeg. Composable and testable independently. |

## Build Order Implications

Based on architecture and dependencies, suggested build order:

### Phase 1: Foundation (Must build first)
1. **Data Models** - Project, Timeline, Clip structures. Everything depends on these.
2. **Storage Layer** - File I/O, basic cache management. Needed before any video loading.
3. **Basic GUI Shell** - PyObjC/AppKit main window and basic layout. Needed to test anything visually.

**Rationale:** These are foundational with no dependencies. Data models are used by everything. Storage is required before loading videos. GUI shell needed to see anything work.

### Phase 2: Core Processing (Build after foundation)
1. **Video Processor Core** - FFmpeg integration, basic video loading/playback
2. **Proxy System** - Generate proxies for large files (critical dependency!)
3. **Hardware Acceleration Detection** - Detect Metal/GPU capabilities early

**Rationale:** Video processor is core to app. Proxy system must be built before working with large files (150MB+). Hardware detection informs codec choices downstream.

**Critical dependency:** Proxy system must be complete before moving to Phase 3. Without it, large files will cause memory issues in effects processing.

### Phase 3: Effects & Editing (Build after core processing)
1. **Timeline UI** - Drag, trim, arrange clips
2. **Effects Engine** - Color grading, transitions, filters
3. **Preview Player** - Playback with effects applied

**Rationale:** Timeline needs video processor to display clips. Effects engine needs processor for applying filters. Preview needs both to show results.

**Dependency note:** Effects engine depends on proxy system being stable. Effects are applied to proxies during editing, originals only at export.

### Phase 4: Music Sync (Build after effects)
1. **Beat Detection** - Audio analysis, tempo tracking
2. **Music Sync Engine** - Auto-align cuts to beats
3. **Timeline Markers** - Visual beat indicators in UI

**Rationale:** Music sync builds on top of timeline and effects. Beat detection is CPU-intensive but independent, can be developed in parallel with timeline work.

**Defer reason:** Beat sync is a "nice to have" feature. Core editing workflow (trim, effects, export) should work without it. Build this after core functionality is solid.

### Phase 5: Export & Polish (Build last)
1. **Export Engine** - 9:16 format, hardware-accelerated encoding
2. **Export Presets** - TikTok, Instagram Reels, YouTube Shorts
3. **Progress Reporting** - Detailed export progress UI

**Rationale:** Export requires all processing components to be complete. Export settings depend on effects and timeline being finalized. Polish can only happen after core functionality works.

**Critical dependency:** Export must switch from proxy to original source files. This requires proxy system to maintain mapping between proxy and original paths.

## Cross-Phase Dependencies

- **Proxy Manager** (Phase 2) → Used by Timeline (Phase 3), Effects (Phase 3), Export (Phase 5)
- **Video Processor** (Phase 2) → Used by Effects (Phase 3), Beat Detection (Phase 4), Export (Phase 5)
- **Task Queue** (Phase 2) → Used by Effects (Phase 3), Beat Detection (Phase 4), Export (Phase 5)
- **Timeline Model** (Phase 1) → Used by Timeline UI (Phase 3), Music Sync (Phase 4), Export (Phase 5)

## Key Architecture Decisions for Roadmap

1. **Task Queue is Critical Early:** Without async task queue, any processing will block GUI. Must be in place by end of Phase 2 before adding effects or export.

2. **Proxy Workflow is Non-Negotiable:** For 150MB+ files (especially 4K 60-120fps), proxy system must be built before serious editing features. Attempting to edit full-res files will result in poor UX and potential crashes.

3. **Hardware Acceleration Must Be Detected Early:** Export performance depends heavily on hardware encoding (Metal/VideoToolbox on Mac). Detection code should be built in Phase 2 to inform codec selection in Phases 3-5.

4. **Beat Detection Can Be Deferred:** Music sync is a differentiating feature but not core to basic editing workflow. Can be built in Phase 4 after core editing (trim, effects, export) is working.

5. **Effects as Composable Pipeline:** Effects engine should be designed as composable filter graph (FFmpeg-style). This enables reuse, testing, and future extensibility without refactoring.

## Sources

- [VidGear High-performance Video Processing Framework](https://github.com/abhiTronix/vidgear)
- [NVIDIA Video Processing Framework (VPF)](https://github.com/NVIDIA/VideoProcessingFramework)
- [Video Pipeline Architecture Documentation](https://video-pipeline.readthedocs.io/en/latest/Architecture.html)
- [FFmpeg Python Bindings Documentation](https://kkroening.github.io/ffmpeg-python/)
- [PyObjC AppKit Framework Documentation](https://pyobjc.readthedocs.io/en/latest/apinotes/AppKit.html)
- [Python Task Queue Solutions (Celery, TaskIQ)](https://www.fullstackpython.com/task-queues.html)
- [Beat Detection and Music Sync Tools (2026)](https://www.opus.pro/blog/best-ai-beat-sync)
- [9:16 Vertical Video Specifications](https://edicionvideopro.com/en/editing-techniques/916-aspect-ratio-guide-vertical-video-for-tiktok-reels/)
- [Proxy Workflow Best Practices](https://blog.frame.io/2024/07/29/updated-guide-premiere-pro-proxies-and-proxy-workflows/)
- [4K Video Processing Python Performance](https://developer.nvidia.com/blog/whats-new-in-pynvvideocodec-2-0-for-python-gpu-accelerated-video-processing/)

---
*Architecture research for: Mac Desktop Video Editing Automation*
*Researched: 2026-01-24*
