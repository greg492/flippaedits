# Requirements

**Project:** Lacrosse Reel Auto-Editor
**Created:** 2026-01-24
**Status:** v1 scope defined

## v1 Requirements

### Video Import (VI)

- [ ] **VI-01**: User can drag-and-drop MP4/MOV video files into the app
- [ ] **VI-02**: System supports 4K 60fps footage from DSLR/mirrorless cameras
- [ ] **VI-03**: System supports 4K 120fps footage from DSLR/mirrorless cameras

### Timeline & Editing (TE)

- [x] **TE-01**: User can mark timestamp for goal moment (when ball hits net/shooter's motion)
- [x] **TE-02**: User can mark timestamp for celebration start (2-3 seconds after goal)
- [ ] **TE-03**: System generates 720p proxy files for smooth 4K preview without lag
- [ ] **TE-04**: User can scrub through 4K footage smoothly using proxy playback

### Music Integration (MU)

- [x] **MU-01**: User can import music file (MP3 or WAV format)
- [x] **MU-02**: System detects beats in music track automatically using librosa
- [x] **MU-03**: System syncs video cuts to detected music beats for transitions

### Effects & Adjustments (EF)

- [x] **EF-01**: User can adjust slow-motion speed (e.g., 0.25x, 0.5x, 0.75x)
- [x] **EF-02**: User can adjust slow-motion duration (how many seconds of slow-mo)
- [x] **EF-03**: System provides 5-15 LUT presets for color grading (cinematic sports looks)
- [x] **EF-04**: User can select and apply LUT preset before export

### Export (EX)

- [ ] **EX-01**: System exports video as 1080p resolution (not 4K - Instagram/TikTok standard)
- [ ] **EX-02**: System exports in 9:16 vertical aspect ratio for Instagram Reels and TikTok
- [ ] **EX-03**: System uses high bitrate (3Mbps) to preserve quality through platform re-compression
- [ ] **EX-04**: User can apply one-click template: goal → b-roll → slow-mo → celebration sequence
- [ ] **EX-05**: System renders final video with music, effects, and edits in single pass (no quality loss)

### GUI & Usability (GUI)

- [ ] **GUI-01**: App has simple drag-drop interface suitable for non-technical user
- [ ] **GUI-02**: All video processing runs on background thread (GUI never freezes)
- [ ] **GUI-03**: User sees progress indicator during processing (proxy generation, export)
- [ ] **GUI-04**: System shows clear, user-friendly error messages (not technical FFmpeg errors)
- [x] **GUI-05**: User can preview edited reel before export

### Technical Foundation (TF)

- [ ] **TF-01**: System uses PyAV for video processing (streaming, not array-based)
- [ ] **TF-02**: System uses FFmpeg with VideoToolbox for Mac hardware acceleration
- [ ] **TF-03**: System processes effects in single-pass pipeline (load → effects → encode once)
- [ ] **TF-04**: System copies external drive files to internal temp storage before processing
- [ ] **TF-05**: System maintains audio sync through slow-motion and speed changes

---

## v2 Requirements (Deferred)

Features deferred to post-v1:

- [ ] **VI-04**: External drive support — Copy to internal storage manually for v1
- [ ] **TE-05**: Undo/redo — Single preview/export flow for v1, add undo later
- [ ] **TE-06**: Trim/cut controls — Manual timestamp marking sufficient for v1
- [ ] **EX-06**: Batch export multiple videos — Single video processing for v1
- [ ] **EF-05**: Advanced color grading controls — LUT presets sufficient for v1
- [ ] **AI-01**: Automatic goal detection via computer vision — Manual timestamps for v1
- [ ] **AI-02**: Automatic celebration detection via player reactions — Manual timestamps for v1
- [ ] **EX-07**: Multi-platform export (multiple aspect ratios) — Single 9:16 format for v1

---

## Out of Scope

Features explicitly excluded from this project with rationale:

- **Multi-track timeline** — Anti-feature: causes complexity for non-technical users. Simple sequence is faster.
- **100+ transition effects** — Anti-feature: decision paralysis. Curated beat-synced transitions are sufficient.
- **4K export option** — Anti-pattern: Instagram/TikTok only support 1080p. Exporting 4K causes worse quality due to platform downscaling.
- **Manual keyframe animation** — Anti-feature: too technical for target user. Preset effects are simpler and faster.
- **Real-time collaboration** — Out of scope: single-user tool, no need for multi-user editing.
- **Screen recording** — Out of scope: different use case. Focus is editing existing DSLR footage.
- **Web interface** — Out of scope: Mac desktop app for v1. Web version could be v3+.
- **Support for saves/assists/checks** — Out of scope for v1: Goals only first, expand to other highlights in v2.

---

## Traceability

Mapping requirements to roadmap phases (populated during roadmap creation):

| Requirement | Phase | Notes |
|-------------|-------|-------|
| VI-01 | Phase 1 | Foundation & Core Processing |
| VI-02 | Phase 1 | Foundation & Core Processing |
| VI-03 | Phase 1 | Foundation & Core Processing |
| TE-01 | Phase 2 | Timeline, Effects & Preview |
| TE-02 | Phase 2 | Timeline, Effects & Preview |
| TE-03 | Phase 1 | Foundation & Core Processing (proxy system) |
| TE-04 | Phase 1 | Foundation & Core Processing (proxy system) |
| MU-01 | Phase 3 | Music Sync |
| MU-02 | Phase 3 | Music Sync |
| MU-03 | Phase 3 | Music Sync |
| EF-01 | Phase 2 | Timeline, Effects & Preview |
| EF-02 | Phase 2 | Timeline, Effects & Preview |
| EF-03 | Phase 2 | Timeline, Effects & Preview |
| EF-04 | Phase 2 | Timeline, Effects & Preview |
| EX-01 | Phase 4 | Export & Polish |
| EX-02 | Phase 4 | Export & Polish |
| EX-03 | Phase 4 | Export & Polish |
| EX-04 | Phase 4 | Export & Polish |
| EX-05 | Phase 4 | Export & Polish |
| GUI-01 | Phase 1 | Foundation & Core Processing |
| GUI-02 | Phase 1 | Foundation & Core Processing |
| GUI-03 | Phase 1 | Foundation & Core Processing |
| GUI-04 | Phase 1 | Foundation & Core Processing |
| GUI-05 | Phase 2 | Timeline, Effects & Preview |
| TF-01 | Phase 1 | Foundation & Core Processing |
| TF-02 | Phase 1 | Foundation & Core Processing |
| TF-03 | Phase 1 | Foundation & Core Processing |
| TF-04 | Phase 1 | Foundation & Core Processing |
| TF-05 | Phase 1 | Foundation & Core Processing |

**Coverage:** 30/30 v1 requirements mapped (100%)

---

## Success Criteria

v1 is successful when:
- User can create a 20-second lacrosse highlight reel in **under 2 minutes** (vs 5-10 minutes manually)
- Video exports at 1080p 9:16 with no visible quality loss
- GUI never freezes during processing
- Beat sync accuracy is within ±100ms of music beats
- User can process 10-20 reels per week without performance degradation

---

*Requirements defined: 2026-01-24*
*Total v1 requirements: 30 across 6 categories*
*Traceability updated: 2026-01-24*
