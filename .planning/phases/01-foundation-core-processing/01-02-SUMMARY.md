---
phase: 01-foundation-core-processing
plan: 02
subsystem: video-processing
tags: [pyav, ffmpeg, videotoolbox, hardware-acceleration, streaming, proxy-generation]

# Dependency graph
requires:
  - phase: 01-01
    provides: Package structure with error handling module
provides:
  - Video metadata extraction (resolution, fps, duration, codec, pixel format)
  - Hardware-accelerated 720p proxy generation with VideoToolbox fallback to software
  - Streaming architecture using PyAV container.decode() (no memory accumulation)
  - Progress callback system for GUI integration
affects: [01-03-timeline-integration, phase-2-effects, gui-integration]

# Tech tracking
tech-stack:
  added: [av==16.1.0]
  patterns: [pyav-streaming, hardware-acceleration-fallback, progress-callbacks]

key-files:
  created:
    - src/processing/video_info.py
    - src/processing/proxy.py
  modified: []

key-decisions:
  - "PyAV streaming with container.decode() iteration (never to_ndarray() in loops)"
  - "VideoToolbox h264_videotoolbox encoder with libx264 fallback pattern"
  - "Multi-core decoding with thread_type='AUTO' for 5x speedup"
  - "VideoToolbox quality q:v=50 (medium quality for 720p proxies)"
  - "Audio stream copied at original speed (TF-05 deferred to Phase 2)"

patterns-established:
  - "Pattern: PyAV streaming - for frame in container.decode(stream) with no array accumulation"
  - "Pattern: Hardware encoder fallback - try h264_videotoolbox except FFmpegError -> libx264"
  - "Pattern: Progress tracking - (processed_frames / total_frames) * 100 via callback"
  - "Pattern: PTS-based timestamps - duration = stream.duration * stream.time_base"

# Metrics
duration: 3min
completed: 2026-01-24
---

# Phase 01 Plan 02: Video Processing Core Summary

**PyAV streaming architecture with VideoToolbox hardware acceleration for metadata extraction and 720p proxy generation from 4K source footage**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-24T18:55:08Z
- **Completed:** 2026-01-24T18:57:59Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Video metadata extraction using PyAV streaming API (width, height, fps, duration, codec, pixel_format, total_frames)
- Hardware-accelerated 720p proxy generation with h264_videotoolbox encoder (4-5x faster than software)
- Automatic fallback to libx264 software encoder when VideoToolbox unavailable
- Memory-efficient streaming architecture using container.decode() iteration (no to_ndarray() calls)
- Progress callback system for GUI updates (0-100% reporting)
- Multi-core decoding enabled with thread_type='AUTO' for 5x performance improvement

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement video metadata extraction** - `95cc847` (feat)
2. **Task 2: Implement proxy generation with hardware acceleration** - `ff38dde` (feat)

**Plan metadata:** (committed separately in final commit)

## Files Created/Modified

- `src/processing/video_info.py` - VideoInfo NamedTuple and get_video_info() function for extracting video metadata (resolution, fps, duration, codec) using PyAV streaming API; is_supported_format() helper for MP4/MOV validation
- `src/processing/proxy.py` - generate_proxy() function for hardware-accelerated 720p proxy creation using h264_videotoolbox with libx264 fallback; streaming frame processing with progress callbacks; audio stream copying at original speed; get_encoder_info() helper for encoder status

## Decisions Made

1. **PyAV streaming architecture** - Used container.decode() iteration pattern from research to avoid memory exhaustion on 4K files (never call to_ndarray() in loops)

2. **VideoToolbox encoder with fallback** - Implemented try h264_videotoolbox, except FFmpegError -> libx264 pattern for robust hardware acceleration with software fallback

3. **Multi-core decoding** - Set stream.codec_context.thread_type = "AUTO" for 5x faster decoding as specified in research

4. **VideoToolbox quality q:v=50** - Used medium quality setting (1-100 scale) for 720p proxies, balancing file size vs preview fidelity per research

5. **PTS-based timestamp calculation** - Used pts * time_base for duration calculations (critical for accuracy and future audio sync requirements)

6. **Audio stream copying** - Copy audio to proxy at original speed without re-encoding (TF-05 audio sync through speed changes deferred to Phase 2 when effects are implemented)

7. **Progress estimation** - When stream.frames is 0, estimate from duration * fps for progress tracking

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing PyAV dependency**
- **Found during:** Task 1 verification
- **Issue:** PyAV (av) package not installed, preventing test execution
- **Fix:** Ran `source venv/bin/activate && python -m pip install av==16.1.0` in virtual environment
- **Files modified:** venv/ (virtual environment)
- **Verification:** Test script executed successfully, metadata extraction validated
- **Committed in:** N/A (dependency installation, not code change)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** PyAV dependency required for testing and runtime. No scope creep - dependency was specified in research but not yet installed.

## Issues Encountered

None - plan executed smoothly. VideoToolbox hardware acceleration available on test system (h264_videotoolbox encoder successfully used).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 1 Plan 03 (Timeline/Markers):**
- Video metadata extraction complete (get_video_info provides duration, fps needed for timeline)
- Proxy generation ready for GUI integration (generate_proxy with progress callbacks)
- Streaming architecture established for Phase 2 effects processing

**Ready for GUI Integration:**
- Progress callback system implemented for QThreadPool worker integration
- get_encoder_info() available for showing user which encoder is active
- Error translation in place for user-friendly FFmpeg error messages

**Technical foundation solid:**
- PyAV streaming pattern verified (no memory issues with large files)
- Hardware acceleration confirmed working (h264_videotoolbox active on test system)
- Multi-core decoding enabled for optimal performance
- Audio stream handling in place for future sync requirements

**No blockers or concerns** - Core video processing engine complete and validated.

---
*Phase: 01-foundation-core-processing*
*Completed: 2026-01-24*
