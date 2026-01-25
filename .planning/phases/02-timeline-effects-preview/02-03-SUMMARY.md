---
phase: 02-timeline-effects-preview
plan: 03
subsystem: gui
tags: [PySide6, timeline, effects, ui-controls, markers]
status: complete
requires: [02-01, 02-02]
provides:
  - Timeline widget with visual timestamp markers
  - Effects panel with speed and LUT controls
  - Signal-based integration for EditSession
affects: [02-04]
tech-stack:
  added: []
  patterns:
    - Qt custom painting for timeline visualization
    - Signal-slot pattern for UI events
    - Dropdown population from LUT registry
key-files:
  created:
    - src/gui/timeline_widget.py
    - src/gui/effects_panel.py
  modified:
    - src/gui/__init__.py
decisions:
  - Timeline uses custom QPainter for visual markers (green for goal, orange for celebration)
  - Speed dropdown limited to 4 options matching FFmpeg atempo capabilities
  - Effects panel emits signals instead of direct EditSession coupling for flexibility
metrics:
  duration: 3 minutes
  completed: 2026-01-25
---

# Phase 2 Plan 3: Timeline Preview Integration Summary

**One-liner:** Timeline widget with visual timestamp markers and effects panel with speed/LUT dropdowns

## What Was Built

Created the timeline and effects control widgets that give users the UI to mark important moments and configure effects:

1. **TimelineWidget** - Timestamp marking interface
   - "Mark Goal" and "Mark Celebration" buttons capture current playback position
   - TimelineMarkerDisplay custom widget with QPainter for visual timeline bar
   - Green triangles for goal markers, orange triangles for celebration markers
   - Current position indicator (vertical line)
   - Time labels showing timestamp for each marker (MM:SS format)
   - Clear markers button to reset
   - Emits `goal_marked`, `celebration_marked`, `markers_cleared` signals

2. **EffectsPanel** - Speed and color grading controls
   - Speed dropdown with 4 options (0.25x, 0.5x, 0.75x, 1.0x)
   - LUT preset dropdown populated from `lut_registry.json` via `load_lut_registry()`
   - Shows LUT description text when preset selected
   - "Generate Preview" button (disabled by default)
   - Emits `speed_changed`, `lut_changed`, `preview_requested` signals

3. **GUI Package Exports** - Updated `src/gui/__init__.py`
   - Exported TimelineWidget, TimelineMarkerDisplay, EffectsPanel
   - Clean __all__ list for easy importing

## Key Design Decisions

**Timeline visualization approach:**
- Custom QPainter implementation for timeline bar instead of using QGraphicsView
- Simpler implementation for fixed horizontal timeline with limited marker types
- Markers as triangles pointing down from top of bar (clear visual distinction)

**Signal-based integration:**
- Widgets emit signals rather than directly modifying EditSession
- Allows flexible wiring in MainWindow - widgets don't know about data structures
- Follows Qt best practices for decoupled UI components

**Speed options alignment:**
- Four speeds match FFmpeg atempo filter capabilities (0.25x, 0.5x, 0.75x, 1.0x)
- Consistent with SlowMotionSettings validation from 02-01
- User-friendly labels like "Slowest (0.25x)"

**LUT dropdown population:**
- Loads from `lut_registry.json` at widget initialization
- Graceful fallback if registry fails to load (keeps "None" option)
- Shows description text to help users understand each preset's look

## Deviations from Plan

None - plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | eec93d8 | Create timeline widget with timestamp marking |
| 2 | 81787bd | Create effects panel with speed and LUT controls |
| 3 | 3b5b76d | Update GUI package exports |

## Integration Points

**Inputs (dependencies):**
- `src/processing/lut_loader.py` - LUTPreset dataclass, load_lut_registry()
- PySide6 Qt framework - QWidget, QPainter, signals/slots

**Outputs (provides to future plans):**
- TimelineWidget.goal_marked signal → MainWindow can update EditSession.goal_moment_ms
- TimelineWidget.celebration_marked signal → MainWindow can update EditSession.celebration_start_ms
- EffectsPanel.speed_changed signal → MainWindow can update EditSession.slow_motion.speed
- EffectsPanel.lut_changed signal → MainWindow can update EditSession.lut_preset
- EffectsPanel.preview_requested signal → MainWindow can trigger preview generation (02-04)

**Visual design notes:**
- Timeline bar: gray background (#e0e0e0), 12px height, with 10px margins
- Goal marker: green (#4CAF50), 12px triangle
- Celebration marker: orange (#FF9800), 12px triangle
- Current position: dark gray (#333333), 2px vertical line
- Speed dropdown: 150px min width, rounded corners, hover state
- LUT dropdown: 200px min width, description in italic gray below

## File Statistics

- **Created:** 2 files
  - `src/gui/timeline_widget.py` (289 lines) - TimelineWidget, TimelineMarkerDisplay
  - `src/gui/effects_panel.py` (211 lines) - EffectsPanel with speed/LUT controls

- **Modified:** 1 file
  - `src/gui/__init__.py` - Added widget exports

## Next Phase Readiness

**Ready for 02-04 (Timeline Integration in MainWindow):**
- ✅ TimelineWidget ready to connect to VideoPreviewWidget.position_changed signal
- ✅ Effects panel signals ready to update EditSession state
- ✅ Preview button exists and emits signal (can trigger preview generation)
- ✅ All widgets exported from src.gui for easy integration

**Integration requirements for 02-04:**
- MainWindow needs to instantiate TimelineWidget and EffectsPanel
- Connect VideoPreviewWidget.position_changed → TimelineWidget.update_position
- Connect timeline/effects signals to EditSession property updates
- Enable timeline marking buttons when video loads
- Enable preview button when timestamps are marked

## Testing Notes

**Verification performed:**
- Import tests confirm widgets can be imported
- Class structure inspection confirms all required buttons/signals exist
- Speed options verified (4 total matching FFmpeg capabilities)
- Signal declarations verified on both widget classes

**Not tested (requires QApplication):**
- Widget instantiation and visual rendering
- Signal emissions on button clicks
- LUT registry loading (requires assets directory)
- QPainter timeline rendering

These will be integration-tested in 02-04 when widgets are added to MainWindow.

## Performance

- **Duration:** 3 minutes
- **Task breakdown:** 3 tasks (create timeline widget, create effects panel, update exports)
- **Commits:** 3 atomic commits (1 per task)
- **Files created:** 2
- **Files modified:** 1
- **Lines added:** ~514 lines of UI code

---

*Completed 2026-01-25 02:52 UTC*
