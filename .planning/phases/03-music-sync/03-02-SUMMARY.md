---
phase: 03-music-sync
plan: 02
subsystem: audio
tags: [QMediaPlayer, Qt, numpy, waveform, audio-playback, visualization]

# Dependency graph
requires:
  - phase: 02-timeline-effects-preview
    provides: Signal-based widget patterns, QPainter custom rendering, EditSession integration
  - phase: 03-01
    provides: BeatDetectorWorker and librosa infrastructure
provides:
  - MusicPlayer wrapper for QMediaPlayer with millisecond-accurate position control
  - WaveformCache for downsampled audio peak visualization
  - Signal-based audio playback patterns for timeline synchronization
affects: [03-03, 03-04, music-ui, timeline-integration]

# Tech tracking
tech-stack:
  added: [numpy>=1.24.0,<2.4]
  patterns: [Signal forwarding with @Slot decorators, Downsampled waveform caching, QMediaPlayer async duration handling]

key-files:
  created:
    - src/audio/music_player.py
    - src/audio/waveform_cache.py
  modified:
    - src/audio/__init__.py
    - pyproject.toml

key-decisions:
  - "Use @Slot decorators for signal forwarding (PySide6 requirement)"
  - "Constrain numpy to <2.4 for numba compatibility (librosa dependency)"
  - "Add 'from __future__ import annotations' for Python 3.13 type hint compatibility"
  - "LRU cache eviction at 10 entries for waveform peaks"

patterns-established:
  - "Signal forwarding pattern: Connect QMediaPlayer signals to slot methods that emit wrapper signals"
  - "Waveform downsampling: Min/max peaks per pixel for QPainter rendering"
  - "Async duration handling: Duration available via signal, not constructor"

# Metrics
duration: 19min
completed: 2026-01-25
---

# Phase 03 Plan 02: Music Playback & Waveform Infrastructure Summary

**QMediaPlayer wrapper with signal-based position tracking and downsampled waveform cache for millisecond-accurate timeline synchronization**

## Performance

- **Duration:** 19 min
- **Started:** 2026-01-25T07:21:03Z
- **Completed:** 2026-01-25T07:40:59Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- MusicPlayer wrapper provides millisecond-accurate position control with QMediaPlayer
- WaveformCache downsamples audio from sample rate to pixel resolution for efficient rendering
- Signal-based patterns integrate with existing timeline widget architecture
- Python 3.13 and numpy 2.3.5 compatibility ensured for all audio modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MusicPlayer wrapper class** - `f9ad5dd` (feat)
2. **Task 2: Create WaveformCache for visualization** - `5508f16` (feat)
3. **Task 3: Update audio module exports** - No separate commit (completed by Plan 03-01 in parallel)

**Bug fixes:**
- Python 3.13 type hint compatibility - `4b5dd93` (fix)
- Numpy version constraint for numba - `4d11256` (fix)

## Files Created/Modified
- `src/audio/music_player.py` - MusicPlayer wrapper for QMediaPlayer with position/duration/volume control
- `src/audio/waveform_cache.py` - WaveformCache for downsampled min/max peaks with caching
- `src/audio/__init__.py` - Module exports for MusicPlayer, WaveformCache, BeatDetectorWorker (from Plan 01)
- `pyproject.toml` - Added numpy>=1.24.0,<2.4 and librosa>=0.11.0 dependencies

## Decisions Made

**1. Use @Slot decorators for signal forwarding**
- Rationale: PySide6 requires slot methods to forward QMediaPlayer signals to wrapper signals
- Impact: Prevents "Failed to connect signal" runtime errors
- Pattern: Connect internal signal → slot method → emit wrapper signal

**2. Constrain numpy to <2.4 for numba compatibility**
- Rationale: librosa depends on numba 0.63.1 which requires numpy<2.4
- Impact: Prevents dependency conflicts and ensures stable audio processing
- Solution: Updated pyproject.toml with numpy>=1.24.0,<2.4

**3. Add 'from __future__ import annotations' for Python 3.13**
- Rationale: Python 3.13 + numpy 2.3.5 can't access np.ndarray at module level in type hints
- Impact: Prevents AttributeError on module import
- Pattern: Defer type hint evaluation to avoid runtime attribute access

**4. LRU cache eviction at 10 entries for waveform peaks**
- Rationale: Multiple zoom levels cache separately; limit memory usage
- Impact: Prevents unbounded cache growth for long audio files
- Implementation: Simple dict.popitem() when cache exceeds 10 entries

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added numpy dependency**
- **Found during:** Task 2 (WaveformCache creation)
- **Issue:** numpy not in dependencies, ModuleNotFoundError on import
- **Fix:** Added numpy>=1.24.0 to pyproject.toml and installed via pip
- **Files modified:** pyproject.toml
- **Verification:** WaveformCache import succeeds
- **Committed in:** 5508f16 (Task 2 commit)

**2. [Rule 3 - Blocking] Added librosa dependency**
- **Found during:** Task 3 (audio module integration)
- **Issue:** librosa required by beat_detector but not in dependencies
- **Fix:** Added librosa>=0.11.0 to pyproject.toml
- **Files modified:** pyproject.toml
- **Verification:** beat_detector imports successfully
- **Committed in:** 5508f16 (Task 2 commit - combined with numpy)

**3. [Rule 1 - Bug] Fixed Python 3.13 type hint compatibility**
- **Found during:** Task 3 verification
- **Issue:** AttributeError: module 'numpy' has no attribute 'ndarray' in beat_detector.py and waveform_cache.py
- **Fix:** Added 'from __future__ import annotations' to both files
- **Files modified:** src/audio/beat_detector.py, src/audio/waveform_cache.py
- **Verification:** All imports work without AttributeError
- **Committed in:** 4b5dd93 (separate bug fix commit)

**4. [Rule 1 - Bug] Constrained numpy version for numba**
- **Found during:** Bug fix verification
- **Issue:** numba 0.63.1 (librosa dependency) incompatible with numpy 2.4.1
- **Fix:** Updated numpy constraint to '>=1.24.0,<2.4' in pyproject.toml
- **Files modified:** pyproject.toml
- **Verification:** pip install succeeds without conflicts
- **Committed in:** 4d11256 (separate bug fix commit)

**5. [Rule 1 - Bug] Cleaned up corrupt numpy installation**
- **Found during:** Dependency installation
- **Issue:** ~umpy directory from failed installation causing warnings
- **Fix:** Removed corrupt directory, reinstalled numpy 2.3.5
- **Files modified:** venv/lib/python3.13/site-packages/ (cleanup)
- **Verification:** No more pip warnings about invalid distributions
- **Committed in:** No commit needed (environment cleanup only)

---

**Total deviations:** 5 auto-fixed (4 blocking, 1 bug)
**Impact on plan:** All auto-fixes necessary for correct operation. Dependencies were missing from initial plan, and Python 3.13/numpy compatibility issues required immediate resolution to proceed.

## Issues Encountered

**1. Parallel execution coordination**
- Plan 03-01 and 03-02 ran in parallel (Wave 1)
- Plan 03-01 created beat_detector.py and updated __init__.py
- Plan 03-02 updated __init__.py independently
- Resolution: Plan 03-01's updates already covered Task 3 requirements
- No conflicts - final state correct

**2. Python 3.13 + numpy 2.x type hint incompatibility**
- numpy 2.3.5/2.4.1 with Python 3.13 can't access np.ndarray in type annotations at module level
- Standard solution: from __future__ import annotations (PEP 563)
- Applied to all audio module files for consistency

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 3 continuation:**
- MusicPlayer provides position tracking for timeline sync (position_changed signal)
- WaveformCache provides efficient visualization data for timeline widget
- Both classes follow signal-based patterns compatible with existing GUI architecture
- QMediaPlayer handles MP3/WAV playback with volume control
- Async duration loading pattern established for UI responsiveness

**Integration points:**
- Timeline widget can consume position_changed for playback indicator
- Timeline paintEvent can use WaveformCache.get_peaks() for waveform rendering
- Music controls can use MusicPlayer.play/pause/seek_ms for user interaction
- EditSession can store MusicPlayer instance for session-wide music state

**Performance considerations:**
- Waveform cache limits memory with 10-entry LRU eviction
- QMediaPlayer operates on main thread (Qt requirement)
- No blocking operations in MusicPlayer methods

**No blockers** - Music playback infrastructure ready for UI integration

---
*Phase: 03-music-sync*
*Completed: 2026-01-25*
