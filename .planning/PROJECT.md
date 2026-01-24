# Lacrosse Reel Auto-Editor

## What This Is

A Mac desktop application that automatically edits lacrosse highlight videos into 20-second social media reels. The user provides raw footage (1-2 minutes, 4K 60-120fps from DSLR), manually marks key timestamps (goal moment, celebration), uploads music, and the system outputs a professionally-edited vertical reel (9:16) following the signature style: goal → b-roll (player reactions/teammates) → slow-motion replay → celebration. Built for a professional lacrosse videographer who creates 10-20 reels per week for players, teams, and clubs.

## Core Value

Transform raw lacrosse footage into client-ready social media reels in under 2 minutes with the user's signature editing style, cutting production time from 5-10 minutes to under 2 minutes per reel.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can drag-and-drop video file (MP4/MOV, 4K 60-120fps) into Mac app
- [ ] User can mark timestamps for: goal moment, celebration start
- [ ] User can upload music track (MP3/WAV)
- [ ] System syncs video cuts to music beat points/transitions
- [ ] System applies editing sequence: goal → b-roll → slow-mo → celebration
- [ ] User can adjust slow-motion speed and duration before export
- [ ] User can adjust color grading/filters before export
- [ ] System exports vertical 9:16 video optimized for Instagram Reels and TikTok
- [ ] Exported video is ~20 seconds, ready to post
- [ ] Simple GUI with drag-drop interface (non-technical user friendly)

### Out of Scope

- AI/ML automatic scene detection — Manual timestamps for v1 to ship faster
- Multiple action types (saves, assists, checks) — Goals only for v1, add others later
- Multi-platform export formats — Single 9:16 vertical format for v1
- Web interface — Mac desktop app only for v1
- Batch processing multiple videos — Single video processing for v1
- Full timeline editor — Preview and adjust, but not full manual editing
- Real-time preview during processing — Process and show result after completion

## Context

**Business Context:**
- User is a professional lacrosse videographer shooting with DSLR/mirrorless cameras
- Creates 10-20 reels per week for players, parents, teams, and clubs (paid service)
- Currently manually edits in DaVinci Resolve, taking 5-10 minutes per reel
- Season is active NOW — needs working system ASAP
- Footage stored on external drive (NAS server)
- Example reels available at: `/Volumes/BACKUP/2025/05 DELIVERABLES/06 JUNE/GREAT 8/` and Google Drive: https://drive.google.com/drive/folders/1v1QYiywShM606lPzpiEooimVPK1Uafj8

**Technical Context:**
- Input: 4K 60fps or 4K 120fps, MP4/MOV from DSLR/mirrorless
- Output: 9:16 vertical, Instagram Reels and TikTok compatible
- File sizes: Final reels are 47M-157M
- User is not technical — needs simple click-and-go interface
- Mac environment (macOS)

**Editing Style Pattern:**
1. **Goal moment** — Show the scoring action (ball hitting net, shooter's motion)
2. **B-roll** — Player who scored and their reaction with teammates
3. **Slow-motion replay** — Replay of the goal at reduced speed
4. **Celebration (celly)** — 2-3 seconds after goal, player reactions

**Detection Cues for Future AI (v2+):**
- Goal: Ball hits net (visual), shooter's motion, audio cue (crowd noise/whistle)
- Celebration: Right after goal (2-3 seconds), excited player movements/reactions

## Constraints

- **Timeline**: ASAP — lacrosse season is currently active, user needs this working soon
- **Tech Stack**: Python for video processing (MoviePy/FFmpeg), simple Mac GUI (can use Python with Tkinter or similar)
- **User Technical Level**: Non-technical user — must be simple drag-drop interface, no command line
- **Input Format**: 4K 60fps or 4K 120fps, MP4/MOV files
- **Output Format**: 9:16 vertical video for Instagram Reels and TikTok
- **Storage**: External drive storage, large file sizes (150MB+ per reel)
- **Performance**: Processing time should be reasonable for 4K footage (ideally under 2 minutes)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Manual timestamps for v1 (not AI detection) | User needs working system ASAP, manual marking is faster to build and still saves massive time vs full manual editing | — Pending |
| Mac desktop app (not web) | User requested desktop app, works with local file system and external drives, no upload bandwidth concerns | — Pending |
| Python + FFmpeg/MoviePy for video processing | Best ecosystem for video manipulation, well-documented, handles 4K efficiently | — Pending |
| Goals only for v1 | Start with most common/profitable content type, add saves/assists/checks later | — Pending |
| Single 9:16 export format | User posts to Instagram Reels and TikTok (both 9:16), keeps v1 simple | — Pending |
| User controls slow-mo speed and color grading | User wants these specific adjustments, they're part of their artistic signature | — Pending |

---
*Last updated: 2026-01-24 after initialization*
