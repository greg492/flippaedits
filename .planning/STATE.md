# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** Transform raw lacrosse footage into client-ready social media reels in under 2 minutes with the user's signature editing style, cutting production time from 5-10 minutes to under 2 minutes per reel.

**Current focus:** Phase 4 - Export & Polish

## Current Position

Phase: 4 of 4 (Export & Polish)
Plan: 0 of ? in current phase
Status: Planning
Last activity: 2026-01-25 — Completed Phase 3 verification (all success criteria met)

Progress: [█████████████] Phase 3 complete (13/13 plans verified)

## Performance Metrics

**Velocity:**
- Total plans completed: 13
- Average duration: 38 minutes
- Total execution time: 8.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 4 | 7h 25m | 111 min |
| 2 | 4 | 14m | 3.5 min |
| 3 | 5 | 42m | 8.4 min |

**Recent Trend:**
- Last 5 plans: 03-02 (19 min), 03-03 (4 min), 03-04 (4 min), 03-05 (1.4 min)
- Trend: Phase 3 extremely efficient; beat detection/music integration averaged 8.4 minutes per plan

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Manual timestamps for v1 (not AI detection) — User needs working system ASAP, manual marking still saves massive time
- Python + FFmpeg/MoviePy for video processing — Best ecosystem for video manipulation, handles 4K efficiently
- PyAV over MoviePy for production — Research confirms streaming architecture required to avoid memory exhaustion on 150MB+ files
- Use setuptools build backend (01-01) — Standard Python packaging tool with good PyPI integration
- Three-module architecture (01-01) — Separate processing/gui/storage concerns for clean development
- PyAV streaming architecture (01-02) — container.decode() iteration, never to_ndarray() in loops to avoid memory exhaustion
- VideoToolbox with fallback (01-02) — Try h264_videotoolbox, except FFmpegError -> libx264 for robust HW acceleration
- Multi-core decoding enabled (01-02) — thread_type='AUTO' for 5x speedup per research
- VideoToolbox quality q:v=50 (01-02) — Medium quality for 720p proxies balancing size vs fidelity
- Audio copied at original speed (01-02) — TF-05 sync through speed changes deferred to Phase 2
- QMediaPlayer for preview (01-04) — Use PySide6's QMediaPlayer instead of custom PyAV rendering for simplicity
- TemporaryDirectory pattern (01-04) — tempfile.TemporaryDirectory with prefix='lacrosse_' for automatic cleanup
- External drive detection via /Volumes/ (01-04) — macOS-specific path check for v1, acceptable for initial release
- PyAV audio stream explicit codec (01-04) — PyAV 16.1.0 requires codec name as positional argument in add_stream()
- Disk space checks before proxy (01-04) — Explicit verification prevents mysterious FFmpeg failures on low disk space
- EditSession as central data structure (02-01) — All editing state flows through EditSession (timestamps, paths, effects)
- SlowMotionSettings validates speed (02-01) — Enforce (0.25, 0.5, 0.75, 1.0) to match FFmpeg atempo capabilities
- LUT registry JSON for UI (02-01) — Separate metadata file enables dropdown population without parsing .cube files
- Identity-based LUTs for v1 (02-01) — Generated minimal valid .cube files, professional LUTs can replace later
- PTS manipulation over setpts filter for video (02-02) — Direct PTS adjustment simpler than filter graph for video speed
- Atempo filter chaining for speeds < 0.5x (02-02) — FFmpeg atempo range [0.5, 2.0], chain multiple for extreme slow-motion
- Tetrahedral interpolation default for LUTs (02-02) — Best quality interpolation, minimal performance impact on modern hardware
- Sequential effects via temp file (02-02) — LUT → temp → slow-motion allows progress reporting per effect
- Timeline custom QPainter for markers (02-03) — Simpler than QGraphicsView for fixed horizontal timeline
- Signal-based widget integration (02-03) — Widgets emit signals rather than directly modifying EditSession for flexibility
- Four speed options in UI (02-03) — Dropdown limited to 0.25x, 0.5x, 0.75x, 1.0x matching FFmpeg atempo capabilities
- PreviewController for effects rendering (02-04) — Separate class manages preview generation with apply_effects_chain
- EditSession in MainWindow (02-04) — Single instance updated via signal handlers from timeline and effects widgets
- Progressive UI reveal (02-04) — Drop zone → video preview → editing controls shown as user progresses
- Preview button state validation (02-04) — Enabled only when session.is_ready_for_preview() returns True
- QObject worker pattern for beat detection (03-01) — Use QObject + moveToThread instead of QRunnable for progress signals
- Include sr and hop_length in finished signal (03-01) — Downstream intensity calculations need exact values from detection
- Fallback beat grid at 130 BPM (03-01) — Generate evenly-spaced beats if librosa detection fails (tempo=0 or empty)
- Librosa median aggregation (03-01) — Use np.median for onset_strength, more robust than mean for hip-hop/trap
- MusicTrack stores sample_rate and hop_length (03-01) — Required for accurate beat intensity frame mapping
- @Slot decorators for signal forwarding (03-02) — PySide6 requires slot methods to forward QMediaPlayer signals to wrapper signals
- Numpy constrained to <2.4 (03-02) — Librosa's numba dependency incompatible with numpy 2.4+, constrain to >=1.24.0,<2.4
- Future annotations for Python 3.13 (03-02) — Use 'from __future__ import annotations' to avoid np.ndarray type hint errors
- LRU cache eviction at 10 entries (03-02) — WaveformCache limits memory with simple dict.popitem() when exceeding 10 zoom levels
- WaveformDisplay batch QLine drawing (03-03) — Draw all waveform lines in single drawLines() call for performance
- Beat markers below timeline (03-03) — Positioned below bar to avoid overlap with goal/celebration triangles
- Intensity threshold 0.7 (03-03) — Strong beats (>0.7) shown as diamonds, weak (<=0.7) as dots for clear differentiation
- Drop hint in controls (03-03) — Shows 'Drop MP3 or WAV' message when no music loaded, hides after successful load
- Blue beat markers (03-03) — Use #4284f4 blue to contrast with green goal and orange celebration markers
- 50ms snap tolerance (03-04) — Stricter than 100ms success criteria, based on EBU R37 audio-video sync perception threshold
- Beat snapping conditional on music loaded (03-04) — Only snap when beat_snapper exists, preserves normal behavior otherwise
- Intensity calculation uses MusicTrack parameters (03-04) — Uses sample_rate and hop_length from MusicTrack, not hardcoded defaults
- QThread cleanup before new detection (03-04) — Prevents thread leaks when reloading music
- Left-click removes, right-click adds beats (03-05) — Standard editing pattern for destructive vs additive actions
- 8px hit zone for beat clicks (03-05) — Generous tolerance for precise clicking on thin beat markers
- Yellow hover highlight (03-05) — High contrast with blue markers for clear visual feedback on interactive beats
- beats_changed signal separate from beats_detected (03-05) — Distinguishes manual edits from auto-detection for proper propagation

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 Complete - All Success Criteria Met:**
- ✅ Drag-and-drop 4K video import functional
- ✅ Hardware-accelerated proxy generation working
- ✅ Video preview with smooth scrubbing operational
- ✅ GUI never freezes during processing
- ✅ User-friendly progress indicators implemented

**Phase 2 Complete - All Success Criteria Met:**
- ✅ User can mark timestamps for goal moment and celebration start with simple clicks
- ✅ User can adjust slow-motion speed (0.25x, 0.5x, 0.75x)
- ✅ User can select from 10 cinematic LUT presets and see effects applied in preview
- ✅ User can preview edited reel with all effects applied before export
- ✅ Preview playback runs smoothly using proxy files

**Phase 3 Readiness:**
- ✅ Audio stream handling working (copied to proxy) - ready for beat detection
- ✅ Video info provides fps and duration for beat detection calculations
- ✅ EditSession stores timestamps and effects - ready to store beat detection results
- ✅ Timeline widget can be extended to display beat markers (add new marker type)
- ✅ Effects application working - can be included in final assembly
- Potential tuning needed: Beat detection parameters for sports highlight music (120-140 BPM EDM/hip-hop)

**Phase 4 Readiness:**
- ✅ Proxy generation pattern can be adapted for final export encoding
- ✅ Error handling and user feedback patterns established
- Note: Instagram/TikTok export specs may change; export preset system should support easy updates

**Phase 2 Complete - All Success Criteria Verified:**
- ✅ User can mark goal and celebration timestamps with Timeline buttons
- ✅ User can adjust slow-motion speed (4 options: 0.25x, 0.5x, 0.75x, 1.0x)
- ✅ User can select from 10 cinematic LUT presets for color grading
- ✅ User can preview edited reel with effects applied before export
- ✅ Preview uses proxy files for smooth playback
- Note: 7 manual tests documented in VERIFICATION.md for visual/UX quality assurance

**No blockers** - Phase 2 verified, ready for Phase 3 (Music Sync)

## Session Continuity

Last session: 2026-01-25 08:04 UTC
Stopped at: Completed 03-04-PLAN.md (Music Integration & Beat Snapping)
Resume file: None

---
*Next step: Continue Phase 3 with `/gsd:execute-phase 3` for next plan or `/gsd:plan-phase 3` to review roadmap*
