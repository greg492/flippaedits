---
phase: 03-music-sync
plan: 03
subsystem: ui/music
tags: [music-ui, waveform, beat-markers, drag-drop, qt-widgets]

dependencies:
  requires:
    - 03-01-PLAN.md (beat detection worker)
    - 03-02-PLAN.md (MusicPlayer and WaveformCache)
    - 02-03-PLAN.md (Timeline widget patterns)
    - 02-04-PLAN.md (signal-based widget integration)
  provides:
    - MusicPanel widget with playback and waveform display
    - Beat marker visualization on timeline
    - Drag-drop audio file import
  affects:
    - 03-04-PLAN.md (will integrate MusicPanel into MainWindow)
    - 03-05-PLAN.md (will use trim controls for music export)

tech-stack:
  added:
    - None (used existing PySide6, librosa, numpy)
  patterns:
    - QPainter batch drawing for waveform performance
    - Qt drag-drop event handling
    - Signal-based widget communication
    - Visual intensity differentiation for beat markers

key-files:
  created:
    - src/gui/music_panel.py (MusicPanel and WaveformDisplay widgets)
  modified:
    - src/gui/timeline_widget.py (added beat marker rendering)
    - src/gui/__init__.py (exported new widgets)

decisions:
  - "WaveformDisplay batch QLine drawing: Draw all waveform lines in single drawLines() call for performance"
  - "Beat markers below timeline: Positioned below bar to avoid overlap with goal/celebration triangles"
  - "Intensity threshold 0.7: Strong beats (>0.7) shown as diamonds, weak (<=0.7) as dots for clear differentiation"
  - "Drop hint in controls: Shows 'Drop MP3 or WAV' message when no music loaded, hides after successful load"
  - "Blue beat markers: Use #4284f4 blue to contrast with green goal and orange celebration markers"

metrics:
  duration: 4 minutes
  completed: 2026-01-25
---

# Phase 03 Plan 03: Music UI Panel & Beat Visualization Summary

MusicPanel widget with waveform display, playback controls, drag-drop import, and beat marker overlay on timeline

## What Was Built

### 1. MusicPanel Widget (Task 1)
**File:** `src/gui/music_panel.py` (342 lines)

**Components:**
- **WaveformDisplay:** Custom widget rendering audio waveform with beat marker overlay
  - QPainter batch drawing for performance (all waveform lines in single drawLines call)
  - Beat markers as vertical lines (height and opacity vary with intensity)
  - Position indicator (white line showing playback position)
  - Trim region dimming (ready for future trim feature)

- **MusicPanel:** Main control panel
  - Drag-drop for MP3/WAV files
  - Play/Pause button connected to MusicPlayer
  - Volume slider (0-100%, default 70%)
  - Position label (MM:SS / MM:SS format)
  - Drop hint label (hides after successful load)

**Integration:**
- Uses `MusicPlayer` from 03-02 for playback
- Uses `WaveformCache` from 03-02 for visualization
- Uses `librosa.load()` to read audio for waveform generation
- Emits signals: `music_loaded`, `beats_detected`, `volume_changed`, `trim_changed`, `playback_requested`

### 2. Beat Markers on Timeline (Task 2)
**File:** `src/gui/timeline_widget.py` (additions)

**Methods Added:**
- `set_beat_markers(beat_times_sec, intensities, duration_sec)` - Convert beat times to timeline positions
- `clear_beat_markers()` - Remove all beat markers from display

**Rendering Logic:**
- **Strong beats (intensity > 0.7):** Blue diamonds, 6px size, opacity 200*intensity
- **Weak beats (intensity ≤ 0.7):** Blue dots, 3px size, opacity 120*intensity
- **Position:** Below timeline bar (y = bar_y + bar_height + offset) to avoid overlap with goal/celebration triangles

**Visual Design:**
```
Timeline Bar: ════════════════════════════
Goal:         ▼ (green triangle above)
Celebration:  ▼ (orange triangle above)
Beats:           ◆  •  ◆  • (diamonds + dots below)
```

### 3. Module Exports (Task 3)
**File:** `src/gui/__init__.py`

Added exports:
- `MusicPanel` - Main music control widget
- `WaveformDisplay` - Waveform visualization widget

## Technical Decisions

### Design Choices

**1. Batch Drawing for Waveform Performance**
- **Decision:** Use `painter.drawLines([QLine(...), ...])` to draw all waveform lines in single call
- **Rationale:** QPainter batch operations significantly faster than individual drawLine() calls
- **Implementation:** Build list of QLine objects, then call drawLines() once per frame
- **Alternative rejected:** Individual drawLine() calls per sample (too slow for real-time rendering)

**2. Beat Marker Positioning Below Timeline**
- **Decision:** Render beat markers below timeline bar at y = bar_y + bar_height + offset
- **Rationale:** Avoids visual overlap with goal (green) and celebration (orange) markers above bar
- **Implementation:** Strong beats at offset +2px, weak beats at offset +4px
- **Alternative rejected:** Above bar positioning (conflicts with existing timestamp markers)

**3. Intensity Threshold for Visual Differentiation**
- **Decision:** Strong beats (>0.7) as diamonds, weak beats (≤0.7) as dots
- **Rationale:** Clear visual hierarchy matches user's "hit the beat" workflow
- **Implementation:**
  - Strong: 6px diamond with QPolygonF, opacity 200*intensity
  - Weak: 3px circle with drawEllipse, opacity 120*intensity
- **Alternative rejected:** Single marker type with only opacity variation (less visually distinct)

**4. Drop Hint in Controls Row**
- **Decision:** Show "Drop MP3 or WAV file here" message in controls, hide after successful load
- **Rationale:** Clear affordance for drag-drop without cluttering waveform display area
- **Implementation:** QLabel in controls HBoxLayout, `.hide()` called in _load_music_file()
- **Alternative rejected:** Overlay text on waveform (visually cluttered after music loads)

**5. Blue Color for Beat Markers**
- **Decision:** Use QColor(66, 133, 244) (#4284f4 blue) for all beat markers
- **Rationale:** Distinct from green goal and orange celebration markers
- **Implementation:** Same blue in waveform overlay and timeline markers for consistency
- **Alternative rejected:** Red markers (too similar to error/warning indicators)

### Integration Patterns

**Signal-Based Architecture (from 02-04):**
- MusicPanel emits `music_loaded(path, duration_ms)` → MainWindow starts beat detection
- MusicPanel emits `beats_detected(beats, intensities)` → MainWindow forwards to timeline
- MusicPanel emits `volume_changed(float)` → Future: persist user preference
- MusicPanel emits `playback_requested(bool)` → Future: sync with video playback

**Drag-Drop Event Handling:**
- `dragEnterEvent()`: Accept only if MIME data contains .mp3 or .wav URLs
- `dropEvent()`: Extract file path, call `_load_music_file()`
- Error handling: Display error message in drop hint label (red italic text)

**Librosa Integration:**
- `librosa.load(file_path, sr=None, mono=True)` reads audio
- Creates `WaveformCache(y, sr)` for visualization
- Duration calculated as `len(y) / sr`
- Player loaded separately via `MusicPlayer.load(file_path)`

## Deviations from Plan

None - plan executed exactly as written.

All three tasks completed with exact specifications:
1. MusicPanel widget with drag-drop, playback, volume, waveform display
2. Beat markers added to TimelineMarkerDisplay with intensity differentiation
3. Module exports updated to include new widgets

## Code Quality

### Performance Considerations
- **Waveform batch drawing:** Single `drawLines()` call per frame
- **Beat marker culling:** Only renders markers within visible timeline range
- **WaveformCache reuse:** No redundant peak calculation per frame

### Error Handling
- Try-except around `librosa.load()` with user-visible error message
- Graceful handling of missing files or corrupt audio data
- Error displayed in drop hint area (no modal dialogs)

### Testing Coverage
All verification checks passed:
1. MusicPanel signals verified (music_loaded, beats_detected, volume_changed)
2. Drag-drop methods present (dragEnterEvent, dropEvent, _load_music_file)
3. MusicPlayer instantiation verified (_player attribute)
4. WaveformDisplay.paintEvent implementation confirmed
5. TimelineMarkerDisplay.set_beat_markers() tested with numpy arrays
6. GUI module exports verified

## Integration Points

### With Existing Code
- **MusicPlayer (03-02):** Used for playback control and duration tracking
- **WaveformCache (03-02):** Used for waveform visualization with zoom support
- **TimelineMarkerDisplay (02-03):** Extended with beat marker rendering
- **EffectsPanel (02-01):** Styling patterns followed for consistency

### For Future Plans
- **03-04 (MainWindow Integration):**
  - Connect `music_loaded` signal to spawn BeatDetectionWorker
  - Connect `beats_detected` signal to timeline.marker_display.set_beat_markers()
  - Add MusicPanel to MainWindow layout (below timeline widget)

- **03-05 (Music Export & Trim):**
  - Use MusicPanel trim controls (currently dimmed but ready)
  - Export trimmed music segment with final reel
  - Sync music trim start with goal timestamp

## Files Changed

### Created
- `src/gui/music_panel.py` (342 lines)
  - `WaveformDisplay(QWidget)` - Waveform visualization with beat overlay
  - `MusicPanel(QWidget)` - Main music control panel

### Modified
- `src/gui/timeline_widget.py` (+69 lines)
  - Added numpy and QPolygonF imports
  - Added `_beat_positions` and `_beat_intensities` instance variables
  - Added `set_beat_markers()` and `clear_beat_markers()` methods
  - Updated `paintEvent()` to render beat markers below timeline bar

- `src/gui/__init__.py` (+3 lines)
  - Added `MusicPanel` and `WaveformDisplay` to imports
  - Added both to `__all__` list

## Verification Results

All success criteria met:

1. ✅ MusicPanel shows waveform area, play/pause, volume slider
2. ✅ MusicPanel accepts drag-drop of MP3/WAV files
3. ✅ Dropped files trigger music_loaded signal with path and duration
4. ✅ MusicPlayer instance connected to play/pause button
5. ✅ WaveformDisplay uses QPainter batch operations for performance
6. ✅ Beat markers rendered on TimelineMarkerDisplay below timeline bar
7. ✅ Strong vs weak beats visually distinguishable (diamonds vs dots)
8. ✅ All components follow existing codebase patterns (signals, styling)

## Next Phase Readiness

**Phase 3 Progress:**
- Plan 03-01: ✅ Beat detection worker (13 min)
- Plan 03-02: ✅ Music playback & waveform infrastructure (19 min)
- Plan 03-03: ✅ Music UI panel & beat visualization (4 min) ← **CURRENT**
- Plan 03-04: 🔲 MainWindow integration
- Plan 03-05: 🔲 Music export & trim controls

**Blockers:** None

**Ready for 03-04:**
- MusicPanel widget ready to add to MainWindow layout
- Signals defined for beat detection workflow integration
- TimelineMarkerDisplay ready to receive beat data
- All imports and exports in place

**Notes:**
- Very fast execution (4 minutes) due to clear specification and existing patterns
- Reused MusicPlayer and WaveformCache from 03-02 without modification
- Followed EffectsPanel and TimelineWidget styling conventions exactly
- QPainter batch operations ensure smooth waveform rendering at 60fps
