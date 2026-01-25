---
phase: 04-export-polish
plan: 01
subsystem: export
tags: [pyav, ffmpeg, video-export, audio-mixing, beat-snapping, templates]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: PyAV streaming architecture with VideoToolbox acceleration
  - phase: 02-timeline-effects
    provides: EditSession data model with timestamps and effects
  - phase: 03-music-sync
    provides: BeatSnapper for beat-synced cuts
provides:
  - Template sequences (goal_celebration, full_play) for one-click export patterns
  - Segment assembly with beat-synchronized cuts using BeatSnapper
  - Audio mixing with volume control via FFmpeg amix filter
affects: [04-02-vertical-export, 04-03-export-dialog, final-assembly]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Template-based video assembly with predefined timing patterns
    - PyAV concat demuxer for segment assembly
    - FFmpeg amix filter for audio mixing with volume control
    - Beat snapping applied to segment boundaries for music sync

key-files:
  created:
    - src/processing/template_sequences.py
  modified:
    - src/processing/export.py
    - src/processing/__init__.py

key-decisions:
  - "Use template sequences with before_timestamp/at_timestamp for timing patterns"
  - "Apply beat snapping to segment boundaries during assembly"
  - "Validate total audio volume <= 1.0 to prevent clipping"
  - "Extract segments to temp files then concatenate with FFmpeg concat demuxer"

patterns-established:
  - "Template sequences define reusable timing patterns for reel structures"
  - "VideoSegment dataclass represents time ranges with optional effects"
  - "Beat snapping with 50ms tolerance applied automatically during assembly"
  - "Audio mixing via PyAV filter graphs with amix filter and volume filters"

# Metrics
duration: 9min
completed: 2026-01-25
---

# Phase 04 Plan 01: Template Sequences & Export Engine Backend Summary

**Template-based video assembly with beat-synced cuts and audio mixing via PyAV filter graphs**

## Performance

- **Duration:** 9 minutes
- **Started:** 2026-01-25T16:57:17Z
- **Completed:** 2026-01-25T17:07:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Template sequences (goal_celebration, full_play) convert session timestamps to segment lists
- Segment assembly with automatic beat snapping for professional music sync
- Audio mixing combines video audio and music track with volume control
- All functions exported from processing module for GUI integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create template sequences with apply_template function** - `9fe14c0` (feat)
2. **Task 2: Create segment assembly and audio mixing functions** - `1a71340` (feat)

## Files Created/Modified
- `src/processing/template_sequences.py` - TemplateSequence and VideoSegment dataclasses, TEMPLATES dict with 2 presets, apply_template function
- `src/processing/export.py` - extract_segment, assemble_segments, mix_audio functions with PyAV and FFmpeg filters
- `src/processing/__init__.py` - Updated exports to include template_sequences and export functions

## Decisions Made

**Template timing patterns:**
- Used `before_timestamp` (segment ends at timestamp) and `at_timestamp` (segment starts at timestamp) for flexible timing definitions
- Clamped start_ms to 0 to prevent negative timestamps when leadup extends before video start

**Beat snapping during assembly:**
- Applied BeatSnapper to segment boundaries during assemble_segments for automatic music sync
- Used 50ms snap tolerance from Phase 3 for professional feel

**Audio mixing implementation:**
- Created PyAV filter graph with volume filters + amix filter (inputs=2, duration=first, normalize=0)
- Validated total volume <= 1.0 at function entry to prevent clipping
- Interleaved pushing frames from both sources (video audio + music) to filter graph

**Segment assembly approach:**
- Extracted segments to temporary files (allows effects per segment)
- Used FFmpeg concat demuxer for fast concatenation without re-encoding
- Cleaned up temp files in finally block

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation followed research patterns from 04-RESEARCH.md. PyAV filter graphs for audio mixing worked as documented.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 04-02 (Vertical Export):**
- Segment assembly complete, ready to add vertical crop/scale filters
- Audio mixing functional, can be integrated with vertical export pipeline
- Template sequences can be used by export dialog

**Ready for 04-03 (Export Dialog):**
- TEMPLATES dict provides preset options for UI dropdown
- apply_template function ready for button click handlers
- assemble_segments and mix_audio ready for export workflow

**Implementation notes:**
- extract_segment includes slow-motion effect support via PTS adjustment
- Audio mixing handles case where video has no audio (music-only output)
- All functions use progress_callback pattern for UI feedback

---
*Phase: 04-export-polish*
*Completed: 2026-01-25*
