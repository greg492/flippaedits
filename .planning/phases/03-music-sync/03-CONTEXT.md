# Phase 3: Music Sync - Context

**Gathered:** 2026-01-25
**Status:** Ready for planning

<domain>
## Phase Boundary

User imports music track (MP3/WAV), system automatically detects beats using librosa, displays visual beat markers on timeline, and enables video cuts to sync with music transitions. This phase brings rhythm and energy to highlight reels through automatic beat detection and synchronization.

Music integration only - video assembly/export workflow is Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Beat Detection & Visualization
- **Detection algorithm**: Onset strength (default) - detects sudden energy increases, catches main beats and snares, works well for high-energy hip-hop/trap music
- **Beat markers**: Diamonds/dots directly on timeline bar - compact and clear visualization
- **Beat intensity levels**: Visual intensity differentiation - strong beats (downbeats) appear larger/brighter than weak beats to help user identify music structure
- **Detection trigger**: Automatic on import - beats detected immediately when music file is loaded for fast workflow with no extra steps

### Music-Video Synchronization Approach
- **Timestamp-beat interaction**: Claude's discretion - determine best approach for how Phase 2 manual timestamps (goal/celebration) interact with detected beat points
- **Cut synchronization**: Major transitions only - main cuts happen on beats, but preserve exact timing for critical moments (e.g., exact goal frame)
- **Snap tolerance**: Strict (±50ms) - tighter sync than success criteria, only snap if very close to beat, otherwise keep original timing
- **Sync preview**: Yes - playback with music - preview shows video with music track playing so user can see and hear the sync before export

### Music File Handling & Preview
- **UI placement**: Bottom of timeline widget - music controls integrated into timeline area with waveform below video timeline
- **Music playback**: Yes - play/pause controls - user can listen to music alone to pick the right section before editing
- **Music trimming**: Yes - start/end point selection - user marks which part of song to use (reels rarely use full song, often just the drop section)
- **Volume control**: Yes - slider control - adjust music volume relative to video audio to balance crowd noise with music

### Beat Editing & Adjustment
- **Manual editing**: Yes - full editing - user can click to add beats or click to remove them (algorithm isn't perfect, user has final say)
- **Global settings**: No global settings - algorithm auto-adapts, manual beat add/remove capabilities are sufficient
- **Detection feedback**: Simple status message - just "Detecting beats..." then "Done" - minimal distraction without progress details
- **Detection failures**: Auto-fallback to grid - if detection fails or produces poor results, generate evenly-spaced beat grid based on estimated BPM (better than nothing)

### Claude's Discretion
- How Phase 2 manual timestamps interact with beat points (snap automatically, keep exact, or suggest)
- Exact waveform visualization design and colors
- Beat marker sizing and opacity for intensity levels
- Music trimming UI controls (handles, region selection, etc.)
- Volume slider range and default mix ratio
- Beat grid generation algorithm for fallback mode

</decisions>

<specifics>
## Specific Ideas

- Music is typically high-energy hip-hop/trap for lacrosse highlights
- Reels rarely use the full song - users will want to select a 20-30 second section (often the "drop")
- Strong beat differentiation helps users understand song structure when selecting sections
- ±50ms snap tolerance is stricter than the ±100ms success criteria - prioritizing tight sync quality
- Music preview capability is important for selecting the right section before editing
- Volume balance matters - crowd audio from gameplay vs music track levels

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 03-music-sync*
*Context gathered: 2026-01-25*
