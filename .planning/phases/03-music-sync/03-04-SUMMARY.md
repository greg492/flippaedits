---
phase: 03-music-sync
plan: 04
subsystem: audio-integration
tags: [pyside6, beat-snapping, music-workflow, threading, signal-slots]

# Dependency graph
requires:
  - phase: 03-03
    provides: "MusicPanel widget with waveform visualization and beat markers"
  - phase: 03-02
    provides: "Audio playback infrastructure and WaveformCache"
  - phase: 03-01
    provides: "BeatDetectorWorker with background beat detection"
provides:
  - BeatSnapper class with 50ms magnetic snap tolerance
  - Complete music workflow in MainWindow (import → detect → snap → playback)
  - Beat detection worker integration with QThread
  - Beat intensity calculation using MusicTrack parameters
  - Beat snapping for goal/celebration timestamp marking
affects: [03-05-beat-editing, 03-06-final-assembly]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "QThread worker pattern for long-running beat detection"
    - "Magnetic snap algorithm with tolerance window"
    - "Signal-based music workflow orchestration"
    - "Sample rate/hop length propagation from worker to UI"

key-files:
  created:
    - src/audio/beat_snapper.py
  modified:
    - src/gui/main_window.py
    - src/audio/__init__.py

key-decisions:
  - "50ms snap tolerance (stricter than 100ms success criteria for professional sync)"
  - "Beat snapping only when music loaded (beat_snapper existence check)"
  - "Intensity calculation uses MusicTrack.sample_rate/hop_length (not hardcoded)"
  - "QThread cleanup before starting new detection (prevents thread leaks)"
  - "Beat markers update both timeline and music panel (dual visualization)"

patterns-established:
  - "Magnetic snap pattern: find nearest → check tolerance → snap or preserve original"
  - "Music workflow: drag-drop → show status → start worker → update session → create snapper → update UI"
  - "Worker pattern: create worker + thread → moveToThread → connect signals → start thread"
  - "Parameter propagation: BeatDetectorWorker emits sr/hop_length → stored in MusicTrack → used in intensity calculation"

# Metrics
duration: 4min
completed: 2026-01-25
---

# Phase 3 Plan 4: Music Integration & Beat Snapping Summary

**Complete music workflow with magnetic beat snapping (50ms tolerance) and background beat detection via QThread worker**

## Performance

- **Duration:** 4 min
- **Started:** 2026-01-25T07:53:18Z
- **Completed:** 2026-01-25T07:56:59Z (includes 03-05 commit that contained Task 2 code)
- **Tasks:** 3 (2 auto + 1 checkpoint)
- **Files modified:** 3

## Accomplishments
- Users can drag-drop MP3/WAV files to import music
- Beat detection runs automatically in background (non-blocking UI)
- Beat markers appear on timeline after detection (strong/weak differentiation)
- Video cut timestamps snap magnetically to beats within 50ms tolerance
- Music playback works with synchronized beat visualization
- Sample rate and hop length properly propagate from worker through MusicTrack

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BeatSnapper with magnetic snap algorithm** - `327021f` (feat)
   - Implemented BeatSnapper class with 50ms tolerance
   - Added snap_to_beat algorithm using numpy for efficiency
   - Convenience methods for millisecond inputs
   - Exported from audio module

2. **Task 2: Integrate music panel into MainWindow** - `f1f8c94` (feat, labeled as 03-05)
   - Added MusicPanel widget to main layout (hidden until video loads)
   - Connected music_loaded signal to trigger beat detection
   - Implemented _start_beat_detection with QThread worker pattern
   - Added _on_beats_detected handler to create snapper and update UI
   - Implemented _calculate_beat_intensities using MusicTrack parameters
   - Updated _on_goal_marked and _on_celebration_marked with beat snapping
   - Beat markers update both timeline and music panel waveform

3. **Task 3: Human verification checkpoint** - User approved
   - Verified music import via drag-drop works
   - Confirmed beat detection completes within expected time
   - Validated beat markers appear on timeline
   - Tested beat snapping for timestamp marking
   - Confirmed music playback and volume control functional

## Files Created/Modified
- `src/audio/beat_snapper.py` - BeatSnapper class with magnetic snap algorithm and tolerance checking
- `src/gui/main_window.py` - Music panel integration, beat detection workflow, worker threading, intensity calculation, beat snapping for markers
- `src/audio/__init__.py` - Exported BeatSnapper class

## Decisions Made
- **50ms snap tolerance:** Stricter than 100ms success criteria, based on EBU R37 audio-video sync perception threshold (40-60ms)
- **Conditional snapping:** Only snap when beat_snapper exists (music loaded), preserves normal behavior otherwise
- **MusicTrack parameter usage:** Intensity calculation uses sample_rate and hop_length from MusicTrack (not hardcoded defaults)
- **QThread cleanup:** Clean up existing worker before starting new detection to prevent thread leaks
- **Dual visualization:** Beat markers update both timeline (TimelineMarkerDisplay) and music panel (WaveformDisplay)
- **Signal-based workflow:** Music loaded → status shown → worker started → beats detected → snapper created → UI updated

## Deviations from Plan

None - plan executed exactly as written.

Note: Task 2 code was committed in f1f8c94 which was labeled "feat(03-05)" but contained the MainWindow integration work specified in 03-04 Task 2. This is documented here as Task 2 completion.

## Issues Encountered

None - all components integrated smoothly. QThread worker pattern worked as expected for non-blocking beat detection.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for manual beat editing (Plan 03-05):**
- ✅ Beat detection operational with background worker
- ✅ Beat markers visible on timeline and waveform
- ✅ Beat snapping functional for timestamp marking (50ms tolerance)
- ✅ BeatSnapper available for editing workflows
- ✅ EditSession stores complete MusicTrack with beats and parameters
- ✅ Music playback synchronized with visualization

**03-05 can now add:**
- Interactive beat editing (add/remove beats with mouse)
- Trim controls for music start/end adjustment
- Beat marker clicking on timeline
- Hover feedback for interactive elements

**Ready for final assembly (Plan 03-06):**
- ✅ Complete music workflow operational
- ✅ Beat snapping available for precise sync
- ✅ Music track data stored in EditSession
- Note: Final assembly will use trimmed music region and edited beat array for music-synced cuts

---
*Phase: 03-music-sync*
*Completed: 2026-01-25*
