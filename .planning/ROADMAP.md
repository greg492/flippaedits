# Roadmap: Lacrosse Reel Auto-Editor

## Overview

This roadmap transforms raw 4K lacrosse footage into beat-synced social media reels in 4 phases. We start by building a solid foundation with hardware-accelerated video processing and proxy workflow to handle large files, then layer on timeline editing with effects, music beat sync, and finally platform-optimized export. Each phase delivers complete, verifiable capabilities that build toward the core value: turn 5-10 minute manual editing workflows into under 2 minutes with signature editing style automation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Core Processing** - Video engine, proxy workflow, and GUI shell
- [ ] **Phase 2: Timeline, Effects & Preview** - Manual editing controls with LUT presets
- [ ] **Phase 3: Music Sync** - Beat detection and automatic cut alignment
- [ ] **Phase 4: Export & Polish** - Platform-optimized rendering

## Phase Details

### Phase 1: Foundation & Core Processing
**Goal**: User can import 4K lacrosse footage, app generates proxies automatically, and GUI remains responsive during all operations

**Depends on**: Nothing (first phase)

**Requirements**: TF-01, TF-02, TF-03, TF-04, TF-05, VI-01, VI-02, VI-03, TE-03, TE-04, GUI-01, GUI-02, GUI-03, GUI-04

**Success Criteria** (what must be TRUE):
  1. User can drag-and-drop 4K 60fps or 4K 120fps MP4/MOV files into the app
  2. System automatically generates 720p proxy files for smooth preview without user intervention
  3. User can scrub through 4K footage smoothly with no lag or stuttering
  4. GUI never freezes during video processing (all operations run on background threads)
  5. User sees progress indicators with clear messages (not technical FFmpeg errors)

**Plans**: 4 plans

Plans:
- [ ] 01-01-PLAN.md - Project setup, package structure, FFmpeg error translation
- [ ] 01-02-PLAN.md - Video processing core (metadata extraction, proxy generation)
- [ ] 01-03-PLAN.md - GUI foundation with drag-drop, threading, progress indicators
- [ ] 01-04-PLAN.md - Integration (temp manager, video preview, complete workflow)

### Phase 2: Timeline, Effects & Preview
**Goal**: User can mark goal/celebration timestamps, apply slow-motion and color grading, and preview edited reel before export

**Depends on**: Phase 1 (requires video processor and proxy system)

**Requirements**: TE-01, TE-02, EF-01, EF-02, EF-03, EF-04, GUI-05

**Success Criteria** (what must be TRUE):
  1. User can mark timestamps for goal moment and celebration start with simple clicks
  2. User can adjust slow-motion speed (0.25x, 0.5x, 0.75x) and duration
  3. User can select from 5-15 cinematic LUT presets and see effects applied in preview
  4. User can preview edited reel with all effects applied before committing to export
  5. Preview playback runs smoothly using proxy files

**Plans**: TBD

Plans:
- [ ] Plan details will be created during `/gsd:plan-phase 2`

### Phase 3: Music Sync
**Goal**: User can import music track, system detects beats automatically, and video cuts sync to music transitions

**Depends on**: Phase 2 (requires timeline and effects system)

**Requirements**: MU-01, MU-02, MU-03

**Success Criteria** (what must be TRUE):
  1. User can import music file (MP3 or WAV) with drag-and-drop
  2. System detects beats in music track automatically within 10 seconds
  3. Timeline shows visual beat markers aligned with detected music beats
  4. Video cuts snap to beat points with ±100ms accuracy for professional sync feel

**Plans**: TBD

Plans:
- [ ] Plan details will be created during `/gsd:plan-phase 3`

### Phase 4: Export & Polish
**Goal**: User can export final reel as 1080p 9:16 vertical video optimized for Instagram Reels and TikTok in under 2 minutes total workflow time

**Depends on**: Phase 3 (requires complete editing pipeline with music)

**Requirements**: EX-01, EX-02, EX-03, EX-04, EX-05

**Success Criteria** (what must be TRUE):
  1. User can apply one-click "lacrosse highlight" template (goal → b-roll → slow-mo → celebration)
  2. System exports video as 1080p 9:16 vertical format with high bitrate (3Mbps minimum)
  3. Exported video includes music, effects, and edits with no quality loss or audio sync drift
  4. User sees progress indicator during export with estimated time remaining
  5. Complete workflow (import → mark → effects → music → export) takes under 2 minutes

**Plans**: TBD

Plans:
- [ ] Plan details will be created during `/gsd:plan-phase 4`

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Core Processing | 0/4 | Planned | - |
| 2. Timeline, Effects & Preview | 0/TBD | Not started | - |
| 3. Music Sync | 0/TBD | Not started | - |
| 4. Export & Polish | 0/TBD | Not started | - |

---
*Roadmap created: 2026-01-24*
*Depth: Quick (4 phases derived from 30 requirements)*
