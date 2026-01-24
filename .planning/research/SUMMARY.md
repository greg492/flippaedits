# Project Research Summary

**Project:** Mac Desktop Sports Highlight Video Automation
**Domain:** Sports Video Editing for Social Media (Lacrosse Highlight Reels)
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

This is a specialized video editing application for lacrosse videographers creating vertical highlight reels for Instagram Reels and TikTok. Based on extensive research across 40+ sources, the recommended approach is a Mac-native desktop application built with Python, using PyAV (not MoviePy) for 4K video processing, PySide6 for the GUI, FFmpeg with VideoToolbox hardware acceleration for M1/M2/M3 Macs, and librosa for music beat detection. The architecture must implement a proxy workflow from Day 1 to handle 150MB+ 4K files without memory exhaustion, and all video processing must run on background threads to maintain GUI responsiveness.

The key differentiator is automatic beat sync to music, which competitors like CapCut and Filmora offer but don't optimize for sports highlight workflows. The critical risk is quality loss from multiple re-encoding passes—the architecture must process all effects as a single pipeline rather than sequential encode/decode cycles. With proper implementation of proxy workflow, hardware acceleration, and single-pass effects processing, this app can deliver 50-70% time savings versus manual editing in iMovie while maintaining 4K quality.

Target user is a semi-professional videographer processing 10-20 reels per week, who needs speed and consistency over creative flexibility. The MVP must prove the core value proposition: "Turn 4K lacrosse footage into beat-synced vertical reels faster than iMovie, with better quality than CapCut mobile."

## Key Findings

### Recommended Stack

Python 3.12+ is the clear choice for this domain, with the best ecosystem for video processing, ML frame interpolation, and scientific computing. **PyAV (not MoviePy)** is critical for production—MoviePy's array-based approach loads entire videos into memory, causing crashes on 150MB+ files, while PyAV streams frames and provides 5x faster performance for 4K processing. PySide6 provides LGPL-licensed Qt bindings (free for commercial use) with native macOS look and feel, superior to Tkinter for professional applications.

**Core technologies:**
- **Python 3.12+**: Best video processing ecosystem, native Mac universal2 support, all major libraries available
- **PyAV 16.1.0+**: Pythonic FFmpeg bindings for streaming video I/O—essential for memory-efficient 4K processing
- **FFmpeg 7.0+ with VideoToolbox**: Industry standard with M1/M2/M3 hardware acceleration (3 simultaneous 4K transcodes on entry-level M1)
- **PySide6 6.10.1+**: LGPL-licensed Qt for native macOS GUI, 558MB universal2 wheel with WebView support
- **librosa 0.11.0+**: Music beat detection with Ellis algorithm for auto-sync to BPM—core differentiator feature
- **colour-science 0.4.7+**: LUT support for one-click color grading with Shepard interpolation

**Critical stack decision:** PyAV over MoviePy is non-negotiable for production. MoviePy is acceptable for rapid prototyping only, but migration to PyAV is required before working with real 4K footage to avoid memory exhaustion.

### Expected Features

**Must have (table stakes):**
- Drag-and-drop 4K video import—every Mac editor has this; users expect it
- Real-time preview playback (4K)—lagging preview is #1 frustration in video editing apps
- Timeline with manual timestamp markers—core workflow for marking highlights during game review
- Basic trim/cut/arrange controls—essential for removing dead air between plays
- Music/audio track import with basic volume control—highlight reels always have background music
- Slow-motion control (0.25x-2x variable speed)—required for showcasing key plays
- 5+ cinematic LUT presets (one-click color grading)—non-technical users can't do manual color grading
- Export to MP4 (1080p, 9:16, 30fps)—Instagram/TikTok only support 1080p vertical; 4K gets downscaled and looks worse
- Save/auto-save project—users process 10-20 reels/week; can't lose work to crashes

**Should have (competitive differentiators):**
- **Automatic beat sync to music**—THE killer feature; cuts editing time by 50-70%; CapCut and Filmora have this in 2026, it's becoming table stakes for social media editing
- One-click "lacrosse highlight" template—bundled settings (20s duration, 9:16, beat-synced, slow-mo on goals, cinematic LUT)
- Batch export for multi-platform—export 1 reel in 3 formats simultaneously (IG/TikTok/YouTube)
- Text overlays for player names—common in recruiting videos (lower-thirds, editable text)
- Instant preview on phone before export—scan QR code, preview on iPhone; prevents "looked good on Mac, bad on Instagram" surprises

**Defer (v2+):**
- Smart clip ordering (AI-suggested sequencing)—requires ML model trained on 100+ user reels; not needed if manual ordering is fast enough
- Motion tracking for player isolation—compute-intensive; more for recruiting videos than social media highlights
- Timestamp sync from external source (CSV import)—niche workflow; only add if 20%+ of users request it
- Multi-format export (square 1:1, landscape 16:9)—focus on vertical 9:16 for Reels/TikTok first

**Explicit anti-features (do NOT build):**
- Full multi-track timeline (10+ tracks)—overwhelming for non-technical users; limit to 2 video + 2 audio tracks
- 100+ transition effects library—analysis paralysis; curate 5-8 professional transitions only
- Manual keyframe animation—too complex; provide pre-animated text templates instead
- Advanced color grading (curves, wheels, scopes)—target user doesn't understand lift/gamma/gain; stick with LUT presets
- 4K export option—Instagram/TikTok only support 1080p; uploading 4K gets downscaled and looks WORSE

### Architecture Approach

The standard architecture for this domain is a three-layer system: GUI layer (PyObjC/AppKit), async processing layer with task queue (Celery/TaskIQ), and storage layer with proxy/cache management. The critical pattern is **separation of concerns**—GUI never calls processing directly; all communication via task queue with progress callbacks. This prevents GUI freezes (the #1 UX complaint) and enables responsive UI during long-running operations.

**Major components:**
1. **GUI Layer (PySide6/AppKit)** — File drag-drop, timeline UI, effects panel, preview player; single-threaded event loop, no blocking operations
2. **Async Task Queue (Celery/TaskIQ with Redis)** — Decouples GUI from video processing; maintains responsiveness; manages background workers with progress callbacks
3. **Processing Engine (PyAV + FFmpeg)** — Video processor, music sync engine (librosa beat detection), effects processor (LUT application, filters), export renderer (9:16 optimization)
4. **Proxy/Cache System** — Generate 720p proxies for editing, use original 4K only for final export; critical for smooth 4K preview performance
5. **Storage Layer** — Temp file management on internal SSD (not external drive), project save/load, cache cleanup

**Critical architectural decisions:**
- **Proxy workflow is non-negotiable for 4K:** Generate proxies automatically on import; use for all preview/editing; switch to original only for export
- **Single-pass effects processing:** Apply all effects as unified FFmpeg filter graph, not sequential encode/decode cycles (prevents quality loss)
- **Hardware acceleration detection early:** Must detect Metal/VideoToolbox capabilities in Phase 2 to inform codec choices
- **Task queue required by Phase 2:** Without async processing, any operation will block GUI and create terrible UX

### Critical Pitfalls

Based on research into 20+ failed video editing projects and common mistakes in this domain:

1. **GUI Freeze from Main Thread Video Processing** — Video operations block UI, causing "Not Responding" and force-quits. **How to avoid:** Separate GUI thread from processing threads from Day 1 (not "we'll add threading later"). Use background threads for ALL video operations. Test with realistic 150MB+ files during development, not 5MB test files. Address in Phase 1: Core Architecture—threading model must be established before any features are built.

2. **Quality Loss Through Multiple Re-encoding Passes** — Each encode/decode cycle compounds quality loss exponentially (1st = 5%, 2nd = 15%, 3rd = 30% total loss). Critical for sports footage with fast motion. **How to avoid:** Process entire effects pipeline in memory before final encode. Use FFmpeg filter chains to apply all effects in single pass: `-vf "scale,colorlevels,overlay"` not three separate encodes. Only encode ONCE at end of workflow. Address in Phase 1: Core Architecture—effects pipeline design determines whether quality preservation is possible.

3. **Memory Exhaustion from Loading Entire Videos into RAM** — A 150MB compressed 4K clip expands to 15-30GB when fully decoded. Processing 2-3 clips exhausts 32GB RAM. **How to avoid:** Stream processing frame-by-frame, never load entire video. Use PyAV instead of MoviePy (MoviePy loads arrays, PyAV streams). Implement frame buffering: keep only 30 frames in memory. Generate proxy files for preview. Address in Phase 1: Core Architecture—memory model is foundational.

4. **Slow External Drive I/O Killing Performance** — Users store 4K clips on external HDDs (rational for space), but processing takes 10x longer than internal SSD. External HDDs max out at 80-120 MB/s; 4K 60fps requires 200+ Mbps reads. **How to avoid:** Copy source files to temp directory on internal SSD for processing, save back after. Detect drive type and warn user. Use aggressive read-ahead buffering. Test on external USB HDD during development. Address in Phase 2: File Management.

5. **Audio Sync Drift After Frame Rate or Speed Changes** — Video frame rate changes (60fps → 30fps, slow-mo effects) alter duration without corresponding audio adjustments. By end of 2-minute video, audio is 1-2 seconds off. **How to avoid:** Never change frame rate without explicit audio resampling strategy. Use FFmpeg's `atempo` filter to match audio duration to video duration. Validate A/V sync programmatically before export. Address in Phase 3: Music Sync Features.

6. **Social Media Export Creates Lower Quality Than Source** — Videos look great locally but appear pixelated/artifacted when uploaded to Instagram/TikTok. Platforms re-encode ALL uploads; exporting at low quality causes double compression. **How to avoid:** Export at HIGHER bitrate than platform targets (15-20 Mbps for Instagram/TikTok, not 8 Mbps). Use platform-specific presets: 1080×1920 (9:16), H.264, 30fps. Test by actually uploading during development. Address in Phase 4: Export Optimization.

7. **Not Using Proxy Workflow for 4K Preview Performance** — Preview playback is choppy/laggy on 4K 60fps footage. Scrubbing has 1-2 second delay. App feels "unresponsive" even though processing completes. **How to avoid:** Generate 720p proxies automatically on import. Use proxies for ALL preview operations. Switch to full-res only for final export. Store proxies on internal SSD for fast access. Address in Phase 2: Preview System—must implement before exposing app to users.

8. **Cryptic Error Messages for Non-Technical Users** — Processing fails with "Error: codec not found" or "FFmpeg returned exit code 1." User has no idea what this means or how to recover. **How to avoid:** Build error translation layer that converts library errors to user-friendly messages with recovery actions. Good: "This video file appears to be corrupted. Try re-exporting from your camera." Bad: "AVFormatContext initialization failed: -1094995529." Address in Phase 1: Core Architecture—error handling strategy must be established early.

## Implications for Roadmap

Based on research, suggested phase structure optimized to avoid critical pitfalls and build in proper dependency order:

### Phase 1: Foundation & Core Architecture
**Rationale:** Threading model, memory model, and effects pipeline design are foundational decisions that cannot be retrofitted. Must establish these patterns before building any features. Research shows that adding threading "later" or migrating MoviePy → PyAV "later" requires complete rewrite (2-4 week effort).

**Delivers:**
- Data models (Project, Timeline, Clip structures)
- Storage layer (file I/O, basic cache management)
- Basic GUI shell (PySide6 main window and layout)
- Async task queue architecture (Celery/TaskIQ setup)
- Error handling framework (user-friendly message translation)

**Addresses:**
- Foundational architecture patterns from ARCHITECTURE.md
- Establishes threading model to prevent GUI freeze pitfall
- Sets up error translation layer for non-technical users

**Avoids:**
- Pitfall #1 (GUI freeze)—threading model established
- Pitfall #3 (memory exhaustion)—streaming architecture chosen
- Pitfall #8 (cryptic errors)—error translation framework in place

### Phase 2: Core Video Processing & Proxy System
**Rationale:** Video processor and proxy system must be complete before adding features. Without proxy workflow, large 4K files will cause memory issues and poor preview performance. Hardware acceleration detection informs codec choices for all downstream work.

**Delivers:**
- Video processor core (PyAV integration, basic loading/playback)
- **Proxy system** (auto-generate 720p proxies on import)—CRITICAL dependency
- Hardware acceleration detection (Metal/VideoToolbox capabilities)
- Basic preview player (proxy-based playback)

**Uses:**
- PyAV 16.1.0+ for streaming video I/O
- FFmpeg 7.0+ with VideoToolbox for hardware encoding
- Task queue from Phase 1 for background proxy generation

**Implements:**
- Proxy/cache component from architecture
- Producer-consumer pattern with task queue
- Streaming frame processing (not array-based)

**Avoids:**
- Pitfall #3 (memory exhaustion)—proxy workflow prevents loading full 4K files
- Pitfall #7 (slow preview)—proxies enable smooth scrubbing
- Pitfall #4 (slow external drive I/O)—temp files on internal SSD

### Phase 3: Timeline, Effects & Single-Pass Processing
**Rationale:** Timeline and effects engine are core editing features but depend on video processor and proxy system being stable. Effects must be designed as composable pipeline (FFmpeg filter graph) to enable single-pass processing and prevent quality loss.

**Delivers:**
- Timeline UI (drag, trim, arrange clips with manual markers)
- Effects engine (color grading with 5+ LUT presets, transitions, filters)
- Preview player with effects applied
- Single-pass effects pipeline (all effects in one FFmpeg filter graph)

**Uses:**
- colour-science 0.4.7+ for LUT application
- FFmpeg filter chains for composable effects
- Proxy system from Phase 2 for preview performance

**Implements:**
- Pipeline-based processing pattern from architecture
- Effects as composable filter graph
- Preview with effects on proxies, export with effects on originals

**Avoids:**
- Pitfall #2 (quality loss)—single-pass effects processing prevents re-encoding
- Ensures effects applied to proxies during editing, originals only at export

### Phase 4: Music Sync & Beat Detection
**Rationale:** Music sync is the #1 competitive differentiator but builds on top of timeline and effects. Can be developed after core editing workflow works. Beat detection is CPU-intensive but independent; can run in background while user continues editing.

**Delivers:**
- Beat detection (librosa audio analysis, BPM/tempo tracking)
- Music sync engine (auto-align cuts to beats)
- Timeline markers for visual beat indicators
- Music import with basic volume control

**Uses:**
- librosa 0.11.0+ for beat detection with Ellis algorithm
- Task queue from Phase 1 for async beat detection
- Timeline model from Phase 1 for beat marker storage

**Implements:**
- Music sync component from architecture
- Async beat detection to avoid blocking import
- Beat-synced clip arrangement

**Avoids:**
- Pitfall #5 (audio sync drift)—implements audio resampling for timing changes
- Validates A/V duration matching before export

### Phase 5: Export, Presets & Polish
**Rationale:** Export requires all processing components to be complete. Platform-specific presets depend on effects and timeline being finalized. Export must switch from proxy to original source files, requiring proxy system to maintain path mappings.

**Delivers:**
- Export engine (9:16 vertical format, hardware-accelerated encoding)
- Platform-specific export presets (Instagram Reels, TikTok, YouTube Shorts)
- Batch export for multi-platform
- Progress reporting UI with time remaining
- Save/auto-save project functionality

**Uses:**
- FFmpeg VideoToolbox encoders for hardware acceleration
- Export preset system (JSON configs for each platform)
- Proxy manager from Phase 2 to switch proxy → original

**Implements:**
- Export renderer component from architecture
- Platform-specific optimization (15-20 Mbps for Instagram/TikTok)
- A/V sync validation before export

**Avoids:**
- Pitfall #6 (social media quality loss)—platform-specific presets with higher bitrate
- Pitfall #5 (audio sync drift)—validates duration matching before export

### Phase Ordering Rationale

- **Phase 1 before Phase 2:** Threading model, memory model, and error handling are foundational. Adding these later requires complete rewrite. Data models and task queue used by all subsequent phases.

- **Phase 2 before Phase 3:** Proxy system must be complete before effects processing. Effects applied to proxies during editing; without proxies, large files cause memory exhaustion and poor UX. Hardware acceleration detection informs codec choices for effects and export.

- **Phase 3 before Phase 4:** Music sync builds on top of timeline and effects. Beat sync auto-arranges clips on timeline and must work with effects pipeline. Single-pass effects processing established before adding music sync timing adjustments.

- **Phase 4 before Phase 5:** Export must integrate beat-synced timeline with effects applied. A/V sync validation critical for music-synced content; must be implemented before export finalization.

- **Why this avoids pitfalls:** Each phase addresses specific pitfalls at the point where they naturally arise. Threading model (Phase 1) prevents GUI freeze. Proxy workflow (Phase 2) prevents memory exhaustion and slow preview. Single-pass processing (Phase 3) prevents quality loss. Audio resampling (Phase 4) prevents sync drift. Platform presets (Phase 5) prevent social media quality degradation.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Hardware acceleration detection—need to research VideoToolbox API for capability querying on M1/M2/M3 Macs; fallback strategy if hardware encoding unavailable
- **Phase 4:** Beat detection accuracy—librosa Ellis algorithm is standard, but may need research into onset detection parameters for optimal sports highlight music (120-140 BPM EDM/hip-hop)
- **Phase 5:** Platform export specs—Instagram/TikTok change compression algorithms frequently; need to validate 15-20 Mbps recommendation with actual uploads in 2026

Phases with standard patterns (skip research-phase):
- **Phase 1:** Standard Python application architecture with PySide6 GUI and Celery task queue—well-documented, established patterns
- **Phase 3:** FFmpeg filter graphs for effects—extensive documentation, colour-science LUT library has clear API

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All core recommendations verified with official PyPI documentation and version compatibility confirmed. PyAV 16.1.0, PySide6 6.10.1, librosa 0.11.0, colour-science 0.4.7 all available and tested with Python 3.12+. FFmpeg VideoToolbox support confirmed for M1/M2/M3 Macs. |
| Features | HIGH | 40+ sources from 2026 confirm table stakes (drag-drop, preview, timeline, export) and competitive differentiators (beat sync, templates). Anti-features validated with UX research showing analysis paralysis from too many transitions/effects. |
| Architecture | MEDIUM | Standard patterns (proxy workflow, task queue, single-pass processing) are well-documented, but specific integration points (PyAV + librosa, PySide6 + async tasks) may have edge cases. Producer-consumer pattern with Celery is proven for video processing. |
| Pitfalls | HIGH | All 8 critical pitfalls verified with multiple sources documenting failures. Quality loss from re-encoding, memory exhaustion from MoviePy, GUI freeze from main thread processing are extensively documented problems with known solutions. |

**Overall confidence:** HIGH

Research is comprehensive across all areas. Stack recommendations are verified with official sources. Feature priorities validated with competitor analysis and user research. Architecture patterns are standard for this domain. Pitfalls are well-documented with clear prevention strategies.

### Gaps to Address

**Hardware acceleration edge cases:** Research confirms VideoToolbox support on M1/M2/M3 Macs, but specific fallback behavior if hardware encoding fails (thermal throttling, external GPU scenarios) needs validation during Phase 2 implementation. **How to handle:** Implement detection with graceful fallback to software encoding; test on entry-level M1 Mac to ensure acceptable performance even without GPU.

**Beat detection parameter tuning:** Librosa beat_track() uses Ellis algorithm, but optimal parameters (hop_length, aggregate window) for sports highlight music (fast-paced EDM, hip-hop) may differ from classical music defaults. **How to handle:** Test with 10-15 typical lacrosse highlight music tracks during Phase 4; tune parameters empirically; consider exposing "music type" preset (EDM, hip-hop, rock) to adjust detection.

**Social media platform spec changes:** Instagram/TikTok compression algorithms and recommended bitrates change periodically. Current recommendation (15-20 Mbps for 1080p vertical) is based on 2026 sources but may shift. **How to handle:** Validate with actual test uploads during Phase 5; design export preset system to be easily updatable (JSON configs, not hardcoded); monitor platform documentation for changes.

**PyAV edge cases with exotic codecs:** PyAV 16.1.0 supports all common codecs (H.264, HEVC, ProRes), but some phone cameras use exotic codecs or non-standard containers. **How to handle:** Implement codec detection and user-friendly error messages in Phase 1; guide users to convert unsupported files; test with footage from Canon, GoPro, iPhone 15 Pro (common for sports videography).

## Sources

### Primary (HIGH confidence)
- STACK.md — Comprehensive technology research with PyPI version verification
- FEATURES.md — Feature landscape research across 40+ sources including CapCut, Filmora, Descript, iMovie competitive analysis
- ARCHITECTURE.md — Standard architecture patterns for video processing applications
- PITFALLS.md — Critical pitfall analysis with 20+ documented failure modes and prevention strategies

### Secondary (MEDIUM confidence)
- [PyAV PyPI](https://pypi.org/project/av/) — Version 16.1.0, FFmpeg bindings, Cython performance
- [PySide6 PyPI](https://pypi.org/project/PySide6/) — Version 6.10.1, LGPL licensing, macOS universal2 support
- [librosa PyPI](https://pypi.org/project/librosa/) — Version 0.11.0, beat detection API
- [colour-science PyPI](https://pypi.org/project/colour-science/) — Version 0.4.7, LUT support
- [FFmpeg VideoToolbox on Mac](https://codetv.dev/blog/hardware-acceleration-ffmpeg-apple-silicon) — M1/M2/M3 performance data
- [Instagram Reels Dimensions & Aspect Ratio (2026)](https://zeely.ai/blog/instagram-reels-dimensions-aspect-ratio-in-2026/) — 1080×1920, 9:16 specs
- [Best AI Video Editors in 2026](https://wavespeed.ai/blog/posts/best-ai-video-editors-2026/) — CapCut, Filmora feature analysis
- [Proxy Workflow Best Practices](https://blog.frame.io/2024/07/29/updated-guide-premiere-pro-proxies-and-proxy-workflows/) — 720p proxy generation, performance benefits

### Tertiary (LOW confidence)
- VidGear capabilities for 4K — claimed "ultra-fast" but benchmarks not independently verified
- Exact M1 vs RTX 2070 performance parity for HEVC encoding — single forum post, needs validation
- RIFE 4.25 frame interpolation performance on M1/M2/M3 with MPS backend — official repo confirms MPS support but Mac benchmark data sparse

---
*Research completed: 2026-01-24*
*Ready for roadmap: YES*
