# Pitfalls Research

**Domain:** Video Processing/Editing Automation for 4K Sports Footage
**Researched:** 2026-01-24
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: GUI Freeze from Main Thread Video Processing

**What goes wrong:**
The application becomes completely unresponsive during video processing operations, forcing users to force-quit or wait indefinitely. Preview playback stutters or freezes when scrubbing through 4K 60-120fps footage. This is the #1 complaint in video editing applications.

**Why it happens:**
Video decoding, encoding, and effects processing are CPU/GPU intensive operations that block the main UI thread when not properly isolated. Developers often start with synchronous FFmpeg calls or direct AVFoundation processing on the main thread, which works fine for small test videos but fails catastrophically with 4K+ footage. A 1-minute 4K 60fps clip at 200Mbps can take 5-10 minutes to process, during which the GUI appears frozen.

**How to avoid:**
- **Architecture requirement:** Separate GUI thread from processing threads from Day 1 (not "we'll add threading later")
- Use background threads/processes for ALL video operations (import, processing, export)
- Implement progress callbacks that update UI asynchronously
- For Python: Use multiprocessing or subprocess for FFmpeg calls, never threading (GIL limitations)
- For macOS: Use DispatchQueue.global() for VideoToolbox/AVFoundation operations
- Test with realistic file sizes (150MB+ 4K clips) during development, not 5MB test files

**Warning signs:**
- Preview window lags when dragging playhead
- App shows "Not Responding" in Activity Monitor during processing
- UI updates (buttons, sliders) don't respond during operations
- Progress indicators freeze instead of updating smoothly
- Users report "app crashed" when it was actually just frozen

**Phase to address:**
Phase 1: Core Architecture - Threading model must be established before any video processing features are built. Adding threading later requires complete rewrite.

---

### Pitfall 2: Quality Loss Through Multiple Re-encoding Passes

**What goes wrong:**
Final exported videos show visible quality degradation, banding in gradients, blocky artifacts in fast motion (critical for sports footage), or color shifts. Each processing step (import → effects → color → export) introduces additional "generation loss" that compounds. For lacrosse footage with fast player movement, re-encoding artifacts destroy the exact action moments users want to highlight.

**Why it happens:**
Developers process video as: decode → apply effect → re-encode → decode → next effect → re-encode. Each encode/decode cycle loses quality, especially with H.264/H.265 (lossy codecs). The quality loss is exponential: 1st re-encode = 5% loss, 2nd = 15% total loss, 3rd = 30% total loss. Common mistake: importing user's H.264 file, decoding to frames, processing, then re-encoding back to H.264 for each operation.

**How to avoid:**
- **Architecture requirement:** Process entire effects pipeline in memory before final encode
- Use FFmpeg filter chains to apply all effects in a single pass: `-vf "scale,colorlevels,overlay"` not three separate encodes
- Keep video in decoded/raw format (numpy arrays, raw frames) throughout processing pipeline
- Only encode ONCE at the very end of the workflow
- Use `-c copy` (stream copy) in FFmpeg when possible (no re-encoding)
- For multi-step workflows: Decode source → process all effects on raw frames → encode final output
- If intermediate files are required, use lossless codecs (ProRes, FFV1) or very high CRF values (CRF 15-18)
- Never re-encode compressed video; always work from highest quality source

**Warning signs:**
- Test videos show more artifacts than source material
- Colors appear washed out or shifted after processing
- Motion blur or blockiness in fast-moving sequences
- File size is larger but quality is worse (sign of poor encoding parameters)
- Users complain "it looks worse than the original camera footage"

**Phase to address:**
Phase 1: Core Architecture - Effects pipeline design determines whether quality preservation is possible. Cannot retrofit single-pass processing into multi-pass architecture.

---

### Pitfall 3: Memory Exhaustion from Loading Entire Videos into RAM

**What goes wrong:**
Application crashes with "Out of Memory" errors, system becomes unresponsive, or macOS kernel panic when processing large 4K files. A 150MB compressed 4K clip expands to 15-30GB when fully decoded into memory (each frame = ~25MB uncompressed). Processing 2-3 clips simultaneously exhausts 32GB RAM.

**Why it happens:**
Developers use libraries like MoviePy that load entire videos into numpy arrays in memory for easy frame manipulation. This works for 10-second test clips but fails for real-world footage. A 60-second 4K 60fps clip = 3,600 frames × 25MB per frame = 90GB RAM required. MoviePy's convenience (array[frame_number]) hides this memory bomb until production.

**How to avoid:**
- **Stream processing:** Process videos frame-by-frame, never load entire video into memory
- Use PyAV instead of MoviePy for production (PyAV streams, MoviePy loads arrays)
- Implement frame buffering: keep only N frames in memory (e.g., 30 frames = 1 second buffer)
- For preview: Generate proxy files (720p) for scrubbing, use original only for export
- Monitor memory usage during development; set alerts for >4GB usage
- Use FFmpeg's pipe I/O for frame streaming: `ffmpeg -i input.mp4 -f rawvideo pipe:1 | python process.py`
- For effects that need multiple frames (motion analysis), use rolling window not full video

**Warning signs:**
- Memory usage grows linearly with video duration
- Activity Monitor shows Python process using >10GB RAM
- Swap usage increases during video processing
- System becomes sluggish when app is running
- Crashes only occur with "real" footage, not test clips
- Error messages about "MemoryError" or "malloc failed"

**Phase to address:**
Phase 1: Core Architecture - Memory model (streaming vs. array-based) is foundational. MoviePy → PyAV migration later is a complete rewrite.

---

### Pitfall 4: Slow External Drive I/O Killing Performance

**What goes wrong:**
Processing takes 10x longer than expected. Previews stutter. Export hangs at "Processing..." for minutes. A 2-minute operation on internal SSD takes 20+ minutes on external HDD. User sees "spinning beach ball" constantly.

**Why it happens:**
Users store 150MB+ 4K clips on external drives (rational for space), but video processing requires rapid sequential reads. External HDDs max out at 80-120 MB/s; 4K 60fps = 200 Mbps ≈ 25 MB/s read requirement. With decode/encode overhead, HDDs can't keep up. USB 2.0/3.0 bus contention, multiple apps reading from same drive, or filesystem fragmentation (FAT32) compound the issue. 2026 global SSD shortage means more users are on HDDs.

**How to avoid:**
- **Design assumption:** Users WILL store source files on slow external drives - optimize for this
- Copy source files to temp directory on internal SSD for processing, process there, then save back
- Detect drive type (HDD vs SSD) and warn user: "Processing will be faster if you move files to internal drive"
- Use aggressive read-ahead buffering: pre-load next 5 seconds of video while processing current second
- For preview: Create proxy files on fast internal storage, keep originals on external
- Avoid multiple read/write operations to external drive; batch them
- Test on external USB HDD during development, not just internal SSD
- Recommend Thunderbolt SSDs in docs (400+ MB/s) over USB HDDs for best performance

**Warning signs:**
- Activity Monitor shows "diskutil" or drive processes using high CPU
- Read/write speeds in Activity Monitor <100 MB/s during processing
- Progress bar moves in bursts (fast → pause → fast) instead of smoothly
- Users report "works fine on Desktop, slow on external drive"
- Processing time varies wildly for same video (drive speed variance)

**Phase to address:**
Phase 2: File Management - Can implement temp directory strategy after core processing works. However, knowing this constraint should inform Phase 1 architecture (streaming, buffering).

---

### Pitfall 5: Audio Sync Drift After Frame Rate or Speed Changes

**What goes wrong:**
Audio and video gradually go out of sync over the course of the clip. By the end of a 2-minute video, audio is 1-2 seconds ahead or behind video. Particularly disastrous for music synchronization (key feature requirement: music sync accuracy). User highlights are ruined because the goal/action doesn't match the beat drop.

**Why it happens:**
Video frame rate changes (60fps → 30fps, slow motion effects) alter video duration without corresponding audio adjustments. Audio has no "frame rate" - it's continuous. When converting 60fps → 30fps, if you drop every other frame naively, video is now half as long, but audio plays at original speed. FFmpeg's `-r` flag changes framerate but doesn't automatically adjust audio. Async audio resampling errors compound: 0.01s drift per second × 120 seconds = 1.2s total drift.

**How to avoid:**
- **Golden rule:** Never change frame rate without explicit audio resampling strategy
- Use FFmpeg's `atempo` filter to match audio duration to video duration: `-filter:a "atempo=0.5"` for 2x slow motion
- For speed ramps: Calculate exact speed ratio and apply matching audio stretch with phase vocoding
- Validate A/V sync programmatically: Check that video_duration == audio_duration before export
- Test with music-synced content during development (not just voice-over)
- For frame interpolation (60→120fps smoothing): Keep audio untouched, only synthesize video frames
- Use `-async 1` flag in FFmpeg to fix sync drift: `-async 1` enables audio timestamp correction
- Implement "snap to beat" feature that adjusts video timing to music, not the reverse

**Warning signs:**
- A/V sync is perfect at start, drifts by end of video
- Audio duration ≠ video duration in metadata
- Users report "music doesn't line up with action"
- Slow-motion clips have normal-speed audio
- MediaInfo shows mismatched durations (video: 120s, audio: 60s)

**Phase to address:**
Phase 3: Music Sync Features - Must be handled when implementing speed/timing adjustments. Core architecture (Phase 1) should preserve audio alongside video in processing pipeline.

---

### Pitfall 6: Social Media Export Creates Lower Quality Than Source

**What goes wrong:**
Exported videos look great locally but appear pixelated, washed out, or artifacted when uploaded to Instagram, TikTok, or YouTube. Users complain "it looked perfect before I uploaded it." Platform compression turns good-quality exports into low-quality mush.

**Why it happens:**
Social platforms re-encode ALL uploads with aggressive compression. Instagram/TikTok target ~4-8 Mbps for 1080p, even if you upload at 20 Mbps. If you export at 8 Mbps to "match platform," platform re-encodes it again → double compression = quality loss. Counter-intuitively, exporting at HIGHER quality (15-20 Mbps) gives better post-platform results because platform's compression has better source material. Additionally, exporting 4K vertical (2160×3840) to Instagram causes heavy downscaling + compression; 1080p direct export often looks better.

**How to avoid:**
- **Platform-specific export presets:** Don't use one-size-fits-all export settings
- **Instagram/TikTok/YouTube Shorts:** Export 1080×1920 (9:16), H.264, 15-20 Mbps, 30fps
- **YouTube regular:** Export 1920×1080 (16:9), H.264, 20 Mbps, frame rate matching source
- **General rule:** Export at higher bitrate than platform targets to survive re-compression
- Use H.264 (not H.265) for maximum compatibility; platforms prefer H.264 for encoding
- Test exports by actually uploading to platforms during development
- Provide "Export for [Platform]" presets in UI, don't expect users to know settings
- Include sharp/clarity filters before export to compensate for platform blur
- Set colorspace metadata correctly: `-colorspace bt709 -color_primaries bt709` for web

**Warning signs:**
- "Looks great in QuickTime, terrible on Instagram"
- Colors shift after upload (often red→orange, blue→purple)
- Horizontal banding or blockiness in platform player
- Users export 4K but platform video looks worse than 1080p uploads
- Exported file is small (5-8 MB for 1-min video) - too low bitrate

**Phase to address:**
Phase 4: Export Optimization - Implement platform-specific presets. Should test during Phase 1 to inform base quality settings.

---

### Pitfall 7: Cryptic Error Messages for Non-Technical Users

**What goes wrong:**
Processing fails and shows: "Error: codec not found" or "FFmpeg returned exit code 1" or "AVFoundation error -12412." Non-technical user has no idea what this means, no idea if it's their fault or the app's fault, and no idea how to recover. User abandons app or floods support with "it doesn't work" tickets.

**Why it happens:**
Developers surface raw FFmpeg/library error messages directly to UI without translation. FFmpeg errors are designed for command-line developers, not end users. Example: "Invalid data found when processing input" (means: file is corrupted, or wrong codec, or DRM-protected). Error handling is often afterthought, added after core features work.

**How to avoid:**
- **Error translation layer:** Catch library errors and translate to user-friendly messages
- **Good error:** "This video file appears to be corrupted. Try re-exporting from your camera or using a different file."
- **Bad error:** "AVFormatContext initialization failed: -1094995529"
- Include recovery actions: "What you can do: [Copy file to Desktop] [Try different file] [Contact Support]"
- Detect common issues proactively:
  - Missing codec → "Your video uses a codec we don't support yet. Please convert to MP4 (H.264) first."
  - DRM/protected → "This file is protected and can't be processed. Try a non-DRM version."
  - Out of disk space → "Not enough disk space. You need 5 GB free. Current: 1.2 GB."
  - Permission denied → "Can't access this file. Try moving it to your Desktop."
- Log technical errors to file for debugging, show simple messages to user
- For critical errors, offer "Send Error Report" button that includes context
- Test with deliberately corrupted/incompatible files during development

**Warning signs:**
- Error messages contain: "errno", "exit code", "exception", library names
- Users ask "what does this mean?" in support
- Errors don't suggest next action
- No difference between user error (bad file) and app error (bug)
- Stack traces shown in UI

**Phase to address:**
Phase 1: Core Architecture - Error handling strategy must be established early. Retrofitting friendly errors later is cosmetic; need structured error system from start.

---

### Pitfall 8: Not Using Proxy Workflow for 4K Preview Performance

**What goes wrong:**
Preview playback is choppy, laggy, or stutters on 4K 60fps footage. Scrubbing through timeline feels sluggish (1-2 second delay). Effects preview updates slowly. App feels "unresponsive" even though processing eventually completes. Users on M1/M2 Macs expect smooth performance but don't get it.

**Why it happens:**
Developers decode and display full 4K resolution for preview/scrubbing. Decoding 4K 60fps in real-time requires significant CPU/GPU: ~8GB/s bandwidth for uncompressed frames. While export can be slow (users understand), preview MUST be real-time or app feels broken. Not implementing proxy workflow from start means preview code is coupled to full-res pipeline.

**How to avoid:**
- **Proxy workflow:** Generate low-res proxy files (720p or 480p) for preview/scrubbing
- On import: Automatically create proxy: `ffmpeg -i input.mp4 -vf scale=1280:720 -preset ultrafast proxy.mp4`
- Use proxy for ALL preview operations (playback, scrubbing, effects preview)
- Switch to full-res only for final export
- Store proxies in temp directory on internal SSD (fast access)
- Proxies should be frame-for-frame identical to original (same frame count, same duration)
- For 500GB project, proxies reduce to ~25GB → 20x faster preview
- Make proxy generation background task with progress: "Optimizing for preview... 30%"
- Offer "Preview Quality" toggle: Low (proxy), High (half-res), Full (original) for user control

**Warning signs:**
- Preview playback is <15 fps on 30fps source
- Scrubbing has 1+ second delay before frame updates
- Activity Monitor shows sustained high CPU during preview (>80%)
- Users report "laggy" or "slow" even on high-end hardware
- Preview performance degrades with longer videos or multiple clips

**Phase to address:**
Phase 2: Preview System - Must implement before exposing app to users. Core architecture (Phase 1) should anticipate dual-file (proxy + original) model.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using MoviePy instead of PyAV | Easier API, rapid prototyping, array-based frame access | Memory exhaustion, slow performance, can't scale to production | MVP/prototype only - must migrate to PyAV for production |
| Synchronous FFmpeg calls on main thread | Simple code, no threading complexity | GUI freezes, poor UX, user complaints | Never acceptable - even MVP should use async |
| Single export preset (one-size-fits-all) | Faster to build, less UI complexity | Poor quality on social platforms, user confusion | Acceptable for MVP if target platform is known; must add presets for v1.0 |
| Skip proxy generation (process full-res directly) | No extra disk space, simpler architecture | Unusable preview performance on 4K content | Never acceptable for 4K workflows - required from Day 1 |
| Re-encode after each effect | Simpler pipeline, easier to debug | Severe quality loss, slow processing | Never acceptable - compounds quality issues |
| Store temp files on external drive | Use user's selected location | 10x slower processing, poor UX | Never acceptable - always use internal storage for temp files |
| Generic error messages | Faster development, less error handling code | Users can't recover from errors, support burden | Never acceptable for non-technical users - must translate errors |
| Skip A/V sync validation | Assume libraries handle it | Silent sync drift bugs, music sync failures | Acceptable only if no speed/framerate changes; must validate if timing manipulation exists |

---

## Integration Gotchas

Common mistakes when connecting to external services and libraries.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FFmpeg | Using `os.system()` or `subprocess.call()` without capturing stderr | Use `subprocess.run(capture_output=True)` and parse stderr for progress/errors |
| FFmpeg | Assuming installed FFmpeg has all codecs | Check available codecs: `ffmpeg -codecs`, bundle known-good FFmpeg binary with app, or use static build |
| AVFoundation | Using `AVAssetReader` synchronously on main thread | Always use `DispatchQueue.global()` for asset reading/writing operations |
| VideoToolbox | Not checking hardware encoder availability | Query `VTCopySupportedPropertyDictionaryForEncoder` before assuming hardware encode works |
| PyAV | Treating PyAV streams like Python lists (indexing) | PyAV streams are iterators; can't do `stream[10]`, must iterate sequentially |
| Social Media APIs | Uploading 4K assuming platform preserves quality | Always export at platform-recommended specs; uploading higher doesn't improve final quality |
| File I/O | Using relative paths for temp files | Use `tempfile.mkdtemp()` for OS-managed temp directory, always absolute paths |
| macOS Sandbox | Accessing files outside app container without permission | Use `NSOpenPanel` for user file selection to get sandbox permission, or request proper entitlements |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading video frames into numpy array | Fast for test clips, easy array operations | Memory exhaustion, crashes | >30 seconds of 4K footage (~20GB RAM) |
| Sequential processing (decode → effect → encode → repeat) | Works fine for single effect | Extreme quality loss after 3+ effects | 2-3 effects applied sequentially |
| No read-ahead buffering from external drive | Simple I/O logic | Stuttering, slow processing | Any video on USB HDD (80-120 MB/s insufficient for 4K) |
| Using high-quality encoding preset for preview | Better preview quality | Slow preview generation | 4K 60fps takes 5x real-time to encode even preview |
| Synchronous FFmpeg progress polling | Simple implementation | UI freezes during processing | Any video >10 seconds |
| Storing all temp files in single directory | Easy to clean up | Filesystem slowdown, Mac Spotlight indexing | >100 temp files in directory |
| Full-resolution effects preview | Accurate preview of final result | Laggy, unresponsive scrubbing | 4K+ footage, especially 60fps+ |
| Global singleton for video processor | Simple access pattern | Crashes if processing two videos | User tries to process multiple videos concurrently |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Processing videos without size/duration limits | Users upload 10GB+ files, DoS your system | Set limits: max 500MB file size, max 10 min duration for web; check before processing |
| Passing user file paths directly to FFmpeg | Command injection via filename: `; rm -rf /` | Validate/sanitize filenames, use `shlex.quote()` in Python, or use FFmpeg library bindings |
| Storing temp files in predictable locations | Other users could access uploaded videos | Use random temp directories: `tempfile.mkdtemp()` with secure permissions |
| Not validating file type (trusting extension) | User uploads .exe renamed to .mp4 | Check file signature (magic bytes): verify MP4 box structure, not just extension |
| Leaving temp files after processing | Disk fills up, videos leak to disk | Always clean up temp files in `try/finally` block, even on error |
| Processing videos in shared temp directory | Filename collisions, data leaks | Create unique subdirectory per processing job with UUIDs |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indication during processing | User thinks app crashed, force-quits | Show percentage, time remaining, current step: "Applying effects... 45% (30s remaining)" |
| Processing blocks UI interaction | Can't cancel, can't browse other videos | Process in background, allow continued UI interaction, add Cancel button |
| No preview before export | User waits 5 minutes for export, realizes effect looks wrong | Always show real-time preview with effects applied before allowing export |
| Unclear what went wrong on error | User retries same action, same failure | Specific error messages with recovery steps: "File too large. Maximum: 500 MB. Yours: 750 MB. Try shorter clip." |
| No indication of quality settings | User exports low quality, doesn't know why result looks bad | Show quality settings with examples: "Good (smaller file)" vs "Best (larger file, recommended)" |
| Auto-playing videos at full volume | Startles user, especially sports footage with crowd noise | Always start muted or at 50% volume with visible volume control |
| No recovery from interrupted processing | Power loss or crash loses all progress | Save checkpoint every N seconds, offer "Resume previous processing?" on restart |
| Confusing file naming on export | Export creates "output.mp4", user can't find it or overwrites previous | Suggest descriptive names: "[original-name]-edited-[date].mp4" with file location shown |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Video Export:** Often missing audio track - verify `ffprobe` shows both audio and video streams, test playback with sound
- [ ] **Effects Pipeline:** Often missing colorspace preservation - verify color range/primaries metadata preserved from source to export
- [ ] **Music Sync:** Often missing tempo detection accuracy check - verify beat detection within ±50ms with ground truth test file
- [ ] **Multi-clip Processing:** Often missing memory cleanup between clips - verify memory returns to baseline after processing each clip
- [ ] **Error Handling:** Often missing file permission errors - test with read-only files, locked files, external drive disconnection
- [ ] **Progress Reporting:** Often missing subprocess error propagation - verify errors during FFmpeg processing surface to UI
- [ ] **Preview Generation:** Often missing audio in preview - verify proxy files include audio stream
- [ ] **4K Performance:** Often missing hardware acceleration check - verify VideoToolbox/GPU acceleration is actually being used (Activity Monitor → GPU utilization)
- [ ] **External Drive Support:** Often missing "drive disconnected" handling - verify graceful failure if drive unmounts during processing
- [ ] **Social Media Export:** Often missing aspect ratio validation - verify exported file matches platform requirements (9:16, 16:9) exactly

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| GUI freezes from main thread processing | HIGH (major refactor) | Extract all processing to separate thread/process; add progress callbacks; refactor UI to be reactive to processing events - 2-3 week effort |
| Quality loss from multi-pass encoding | MEDIUM (pipeline refactor) | Redesign effects pipeline to process raw frames; combine all FFmpeg filters into single `-vf` chain; may require rewriting effect application logic - 1-2 week effort |
| Memory exhaustion from full-video loading | HIGH (library change) | Migrate from MoviePy to PyAV; rewrite frame processing to use streaming iterators instead of arrays - 2-4 week effort |
| Slow external drive I/O | LOW (add temp copy) | Add "Copy to temp directory" step before processing; copy processed file back after; requires UI updates for progress - 2-3 day effort |
| Audio sync drift | MEDIUM (pipeline addition) | Add A/V duration validation before export; implement audio resampling for timing changes; may require rebuilding speed adjustment logic - 1 week effort |
| Social media quality issues | LOW (preset addition) | Create platform-specific export presets; add UI for preset selection; test on actual platforms - 3-5 day effort |
| Cryptic error messages | LOW (error handling layer) | Build error translation map; wrap library calls with try/except; requires testing various failure modes - 1 week effort |
| No proxy workflow | MEDIUM (dual-file architecture) | Add proxy generation on import; modify all preview code to use proxy; add proxy/original switching logic - 1-2 week effort |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| GUI freeze from main thread processing | Phase 1: Core Architecture | Run 150MB 4K file through pipeline; UI should remain responsive with <50ms button click latency |
| Quality loss from multi-pass encoding | Phase 1: Core Architecture | Apply 3 effects; compare output to source using VMAF score (should be >95) |
| Memory exhaustion from full-video loading | Phase 1: Core Architecture | Process 2-minute 4K clip; memory usage should stay <2GB throughout |
| Slow external drive I/O | Phase 2: File Management | Process video on USB HDD; should be max 2x slower than SSD (not 10x) |
| Audio sync drift | Phase 3: Music Sync Features | Apply speed change; verify audio duration == video duration exactly |
| Social media quality issues | Phase 4: Export Optimization | Export for Instagram; upload to test account; verify quality comparable to source |
| Cryptic error messages | Phase 1: Core Architecture | Test with corrupted file; error message should not mention "FFmpeg", "errno", or "exception" |
| No proxy workflow | Phase 2: Preview System | Scrub through 4K 60fps timeline; playhead should update <100ms after click |

---

## Sources

### Video Processing Performance & 4K Challenges
- [12 Common 4K Video Play/Edit/Upload Errors & How to Fix Them](https://www.winxdvd.com/video-transcoder/4k-video-errors-and-solutions.htm)
- [Best Practices to Mitigate Common Pitfalls in 4K Video Delivery – Display Daily](https://displaydaily.com/best-practices-to-mitigate-common-pitfalls-in-4k-video-delivery/)
- [Best External SSDs for Video Editing in 2026](https://gagadget.com/en/66712-best-ssds-for-video-editing-internal-and-external-review-amp/)
- [Common Causes of Slow External Drive Performance](https://support-en.wd.com/app/answers/detailweb/a_id/17047/~/common-causes-of-slow-external-drive-performance-and-data-transfer-rates)
- [Global Memory Shortage 2026: What Filmmakers Need To Know](https://www.cined.com/global-memory-shortage-2026-what-filmmakers-need-to-know-about-rising-nand-dram-and-ssd-prices/)

### GUI Threading & Performance
- [PySide 6: GUI Freezing even when using QThreadPool class](https://forum.qt.io/topic/137276/pyside-6-gui-freezing-even-when-using-qthreadpool-class)
- [GUI freezes even with multithreading](https://forum.qt.io/topic/98407/gui-freezes-even-with-multithreading)
- [Threads Made Simple: Understanding Single vs. Multi-Threading for Beginners](https://medium.com/@sweetondonie/single-thread-vs-multi-thread-a-beginners-guide-becc77c66a0c)

### Quality Loss & FFmpeg Best Practices
- [How to compress video files while maintaining quality with ffmpeg](https://www.mux.com/articles/how-to-compress-video-files-while-maintaining-quality-with-ffmpeg)
- [What you NEED to know before touching a video file](https://gist.github.com/arch1t3cht/b5b9552633567fa7658deee5aec60453/)
- [Video Bitrates and Export Myths - Frame.io](https://blog.frame.io/2024/02/26/video-bitrates-and-export-myths/)

### Audio Sync & Frame Rate Issues
- [Syncing Audio From Different Video Sources With Different FPS](https://forum.videohelp.com/threads/390196-Syncing-Audio-From-Different-Video-Sources-With-Different-FPS)
- [DiVAS: Video and Audio Synchronization with Dynamic Frame Rates](https://openaccess.thecvf.com/content/CVPR2024/papers/Fernandez-Labrador_DiVAS_Video_and_Audio_Synchronization_with_Dynamic_Frame_Rates_CVPR_2024_paper.pdf)
- [Automated Video Time Warp: Smooth Speed Ramps with Audio Sync](https://reelmind.ai/blog/automated-video-time-warp-smooth-speed-ramps-with-audio-sync)

### Color Grading & Effects Pipeline
- [Color Correction Basics for Short Films](https://www.indieshortsmag.com/tutorials/post-production/2026/01/color-correction-basics-for-short-films/)
- [Colour Management for Video Editors](https://jonnyelwyn.co.uk/film-and-video-editing/colour-management-for-video-editors/)
- [Loss in quality when colour correcting/grading footage](https://creativecow.net/forums/thread/loss-in-quality-when-colour-correcting-grading-foo/)

### Social Media Export Optimization
- [Best CapCut Export Settings for TikTok, Instagram & YouTube Shorts](https://www.mygamingdiaries.com/2026/01/best-capcut-export-settings-for-tiktok.html)
- [Social Media Video Aspect Ratios and Sizes — The 2026 Guide](https://www.kapwing.com/resources/social-media-video-aspect-ratios-and-sizes-the-2025-guide/)
- [Best Video Format & Codec for Social Media](https://pixflow.net/blog/the-creators-cheat-sheet-best-video-formats-codecs-for-social-media/)
- [Social Media Video Sizes for 2026: Complete Platform Guide](https://recurpost.com/blog/the-up-to-date-video-sizes-guide-for-social-media/)

### Error Handling & UX
- [UX Error Recovery: Key Strategies for Better User Experience](https://helio.app/ux-research/ux-terms/ux-error-recovery/)
- [Mastering Error Handling: A Comprehensive Guide](https://dev.to/kfir-g/mastering-error-handling-a-comprehensive-guide-1hmg)
- [How to Fix 20+ Common Video Errors: A Complete Guide](https://repairit.wondershare.com/video-repair/repair-video-errors.html)

### Proxy Workflow
- [How a Proxy Workflow Makes Editing 4K Footage Smooth and Stress-Free](https://sanantoniovideoproductions.com/blog/how-a-proxy-workflow-makes-editing-4k-footage-smooth-and-stress-free)
- [Editing 4k Videos Smoothly Using Proxy in Premiere Pro](https://pixflow.net/blog/editing-4k-videos-using-proxy-premiere-pro/)
- [Proxy Editing Explained: Faster, Smoother Workflow](https://filmora.wondershare.com/video-editing-workflow/what-is-proxy-video.html)
- [Updated: Complete Guide to Premiere Proxies & Proxy Workflows](https://blog.frame.io/2024/07/29/updated-guide-premiere-pro-proxies-and-proxy-workflows/)

### Python Video Libraries
- [Python Video Processing: 6 Useful Libraries](https://cloudinary.com/guides/front-end-development/python-video-processing-6-useful-libraries-and-a-quick-tutorial)
- [pyav instead of moviepy? Discussion](https://github.com/soft-matter/pims/issues/38)
- [Native video processing in Python](https://brunovellutini.com/posts/native-video-processing-python/)

### Video Codecs
- [H.264 vs H.265 vs VP9: Which Codec Should You Use in 2026?](https://www.red5.net/blog/h264-vs-h265-vp9/)
- [AV1 vs H.264 vs H.265: Video Codec Comparison Guide](https://www.fastpix.io/blog/av1-vs-h-264-vs-h-265-best-codec-for-video-streaming)
- [Understanding Video Codecs: H.264, H.265 (HEVC), VP9 & AV1 Compared](https://pixflow.net/blog/understanding-video-codecs-h-264-hevc-h-265-vp9-and-av1-explained/)

### macOS Hardware Acceleration
- [Video Toolbox and Hardware Acceleration](https://www.objc.io/issues/23-video/videotoolbox/)
- [Apple Mac - Hardware Acceleration - Jellyfin](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/apple/)
- [Video Toolbox | Apple Developer Documentation](https://developer.apple.com/documentation/videotoolbox)
- [Using Hardware Acceleration on MacOS with FFmpeg](https://www.martin-riedl.de/2020/12/06/using-hardware-acceleration-on-macos-with-ffmpeg/)

---

*Pitfalls research for: Mac Video Editing Automation - 4K Sports Footage Processing*
*Researched: 2026-01-24*
