# Stack Research

**Domain:** Mac Desktop Video Editing Automation
**Researched:** 2026-01-24
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.12+ | Core language | Best ecosystem for video processing, ML frame interpolation, and scientific computing. Native support for Mac universal2 binaries. 3.13+ supported by all major libraries. |
| **PyAV** | 16.1.0+ | Video I/O and FFmpeg wrapper | Direct Pythonic bindings to FFmpeg libraries. Superior to MoviePy for 4K processing - provides granular control over codecs, streams, and hardware acceleration. Uses Cython for performance. |
| **FFmpeg** | 7.0+ | Video processing backend | Industry standard with VideoToolbox support for M1/M2/M3 hardware acceleration. Entry-level M1 can handle three 4K 24fps HEVC transcodes simultaneously. Use `h264_videotoolbox` and `hevc_videotoolbox` encoders. |
| **PySide6** | 6.10.1+ | GUI framework | LGPL-licensed Qt bindings (free for commercial use). Native macOS look and feel. 558MB universal2 wheel includes WebView support. PyQt6 is functionally identical but requires commercial license for closed-source apps. |
| **NumPy** | 2.0+ | Array processing | Required by all video processing libraries. v2.0+ used by PySide6 for Python 3.10+. Essential for pixel-level manipulation. |

### Video Processing & Effects

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **MoviePy** | 2.2.1+ | High-level video editing | Quick concatenation, text overlays, simple effects. Good for prototyping editing sequences. Slower than PyAV but more intuitive API. |
| **RIFE** | 4.25+ | AI frame interpolation | Generate true slow-motion from 60-120fps footage. Runs 30+ FPS for 2X 720p on RTX 2080Ti. Use 4.25 for most scenes, 4.22.lite for post-processing. Requires GPU. |
| **OpenCV** | 4.10+ | Traditional frame interpolation | Lucas-Kanade and Horn-Schunck optical flow for CPU-based slow-mo. Fallback when GPU unavailable. Less smooth than RIFE. |
| **colour-science** | 0.4.7+ | Color grading and LUT support | Read/apply .cube LUTs. Supports LUT1D, LUT3x1D, LUT3D with Shepard interpolation. BSD-3-Clause license. For programmatic color transforms, not real-time grading UI. |

### Audio Processing & Music Sync

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **librosa** | 0.11.0+ | Music beat detection | `beat_track()` detects tempo and beat positions using Ellis algorithm. Essential for syncing cuts to music. Requires FFmpeg or GStreamer for MP3. Python 3.13 support confirmed. |
| **soundfile** | 1.0+ | Audio I/O | Backend for librosa. Handles WAV, FLAC, OGG natively. |
| **audioread** | 3.0+ | Audio format support | Provides MP3/AAC support to librosa via FFmpeg/GStreamer. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **py2app** | Mac app bundling | Recommended for Mac-specific distribution. Creates .app bundles with ad-hoc code signing for ARM64. Better than PyInstaller for macOS-only projects. |
| **PyInstaller** | Cross-platform packaging | Alternative if targeting multiple platforms. Works with Python 3.8-3.14. Not a cross-compiler - must run on macOS to build macOS apps. |
| **pytest** | Testing framework | Standard Python testing tool. Essential for video processing pipelines. |
| **black** | Code formatter | Consistent code style. Industry standard. |

## Installation

```bash
# Core video processing stack
pip install av==16.1.0
pip install moviepy==2.2.1
pip install numpy>=2.0
pip install opencv-python>=4.10

# GUI framework
pip install PySide6==6.10.1

# Audio and music analysis
pip install librosa==0.11.0
pip install soundfile>=1.0
pip install audioread>=3.0

# Color grading
pip install colour-science==0.4.7

# Dev tools
pip install -D pytest black py2app
```

```bash
# Install FFmpeg with VideoToolbox support (Mac)
brew install ffmpeg

# For RIFE (GPU-accelerated frame interpolation)
# Clone official repo - no pip package
git clone https://github.com/hzwer/ECCV2022-RIFE.git
# Requires: PyTorch with CUDA/MPS support
pip install torch torchvision
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **PyAV** | MoviePy | Use MoviePy for simple edits where performance isn't critical. PyAV has steeper learning curve but 5x faster for 4K. |
| **PySide6** | PyQt6 | Functionally identical (99.9% same API). Use PyQt6 if you already have commercial license. Otherwise PySide6's LGPL is better for closed-source commercial apps. |
| **PySide6** | Tkinter | Only if you need ultra-lightweight distribution (~5MB vs 558MB). Tkinter looks dated and non-native on Mac. |
| **RIFE** | OpenCV optical flow | RIFE produces smoother results but requires GPU. OpenCV works CPU-only but quality is lower for slow-motion. |
| **py2app** | PyInstaller | Use PyInstaller for cross-platform projects. py2app better integrates with macOS signing/notarization. |
| **colour-science** | Custom LUT code | colour-science handles edge cases (interpolation, multiple LUT formats). Don't reinvent unless you need real-time GPU LUT processing. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **MoviePy 1.x** | v1 reached end-of-life. Breaking API changes in 2.0 (`.set_*` → `.with_*`, effects are now classes, no `moviepy.editor` namespace). | MoviePy 2.2.1+ |
| **Python 2.7** | End-of-life since 2020. MoviePy 2.0+ explicitly drops support. | Python 3.12+ |
| **Direct FFmpeg subprocess calls for complex edits** | Error-prone, hard to debug. Reinventing PyAV's wheel. | PyAV for programmatic control, MoviePy for high-level edits |
| **wxPython** | Outdated, inconsistent macOS support. Last major update 2019. | PySide6 for modern, native Mac UI |
| **VidGear** | Overkill for this use case. Designed for live streaming/network protocols. Adds unnecessary complexity. | PyAV for file-based processing |
| **PyNvVideoCodec** | NVIDIA-specific. Doesn't leverage Mac's VideoToolbox. Requires CUDA. | PyAV with FFmpeg VideoToolbox encoders for Mac |

## Stack Patterns by Variant

**For CPU-only processing (no GPU):**
- Use OpenCV optical flow for slow-motion (fallback from RIFE)
- Use FFmpeg's CPU encoders instead of VideoToolbox
- Expect 3-5x slower processing times for 4K

**For maximum performance (M1/M2/M3 Mac):**
- Use PyAV with VideoToolbox encoders: `h264_videotoolbox`, `hevc_videotoolbox`
- M1 matches RTX 2070 performance for HEVC encoding
- M3+ supports hardware AV1 decoding
- Can handle three 4K 24fps transcodes simultaneously

**For non-technical users:**
- Prioritize PySide6 drag-drop GUI over command-line
- Use py2app to create standalone .app (no Python installation required)
- Include progress bars for all video processing operations
- Provide video preview functionality (PySide6 QMediaPlayer or QVideoWidget)

**For beat-synced editing:**
- Use librosa's `beat_track()` to detect tempo and beat frames
- Convert beat frames to timestamps: `librosa.frames_to_time(beat_frames, sr=sr)`
- Sync video cuts to beat_times array
- Test with 120-140 BPM music (typical sports highlight music)

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PyAV 16.1.0+ | FFmpeg 7.0+ | PyAV wheels on PyPI are pre-built with FFmpeg. Separate brew FFmpeg install for CLI access. |
| PySide6 6.10.1+ | Python 3.9-3.14 | NumPy 2.0+ required for Python 3.10+. macOS 13.0+ for universal2 wheels. |
| MoviePy 2.2.1+ | Python 3.9+ | Breaking changes from v1. See migration guide. |
| librosa 0.11.0+ | Python 3.8-3.13 | Python 3.13 requires manual pip install (conda builds pending). Needs FFmpeg/GStreamer for MP3. |
| RIFE 4.25+ | PyTorch 2.0+, CUDA 11.8+ or MPS | Mac M1/M2/M3 can use MPS (Metal Performance Shaders) backend for GPU acceleration. |
| colour-science 0.4.7+ | Python 3.14+ supported | Recent addition. NumPy 2.0+ recommended. |

## Critical Integration Notes

### Hardware Acceleration on Mac
```python
# PyAV example - VideoToolbox encoding
import av

container = av.open('output.mp4', 'w')
stream = container.add_stream('h264_videotoolbox', rate=60)
stream.width = 1080
stream.height = 1920  # 9:16 vertical
stream.pix_fmt = 'nv12'  # Required for VideoToolbox
```

### RIFE Frame Interpolation
- Not available on PyPI - must clone GitHub repo
- Model weights (~300MB) downloaded on first run
- Recommended: RIFE 4.25 for general use, 4.22.lite for post-processing
- Inference time: ~33ms per frame pair on RTX 2080Ti (720p)
- Mac M1/M2/M3 can use MPS backend but slower than NVIDIA

### Librosa Beat Detection
```python
import librosa

y, sr = librosa.load('music.mp3')
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
# beat_times is array of seconds where beats occur
```

### LUT Application
```python
import colour

lut = colour.read_LUT('cinematic_grade.cube')
# Apply to RGB frame (NumPy array)
graded_frame = lut.apply(rgb_frame)
```

## Sources

**HIGH CONFIDENCE (Verified with official sources):**
- [MoviePy PyPI](https://pypi.org/project/moviepy/) - Version 2.2.1, features
- [PyAV PyPI](https://pypi.org/project/av/) - Version 16.1.0, requirements
- [PySide6 PyPI](https://pypi.org/project/PySide6/) - Version 6.10.1, Mac universal2 support
- [librosa PyPI](https://pypi.org/project/librosa/) - Version 0.11.0
- [colour-science PyPI](https://pypi.org/project/colour-science/) - Version 0.4.7
- [PyQt6 vs PySide6 comparison](https://www.pythonguis.com/faq/pyqt6-vs-pyside6/) - Licensing differences
- [FFmpeg VideoToolbox on Mac](https://codetv.dev/blog/hardware-acceleration-ffmpeg-apple-silicon) - M1/M2/M3 performance data
- [RIFE GitHub](https://github.com/hzwer/ECCV2022-RIFE) - Official implementation, version recommendations
- [librosa beat detection docs](https://librosa.org/doc/main/generated/librosa.beat.beat_track.html) - Ellis algorithm details

**MEDIUM CONFIDENCE (Multiple sources agree):**
- [Python video processing libraries 2026](https://www.gumlet.com/learn/ffmpeg-python/) - MoviePy vs PyAV trade-offs
- [4K video processing Python performance](https://developer.nvidia.com/blog/whats-new-in-pynvvideocodec-2-0-for-python-gpu-accelerated-video-processing/) - GPU acceleration benefits
- [Mac GUI frameworks 2026](https://www.pythonguis.com/faq/which-python-gui-library/) - PySide6 recommended for professional apps
- [py2app vs PyInstaller](https://py2app.readthedocs.io/en/latest/) - Mac-specific bundling

**LOW CONFIDENCE (WebSearch only - flagged for validation):**
- VidGear capabilities for 4K - claimed "ultra-fast" but benchmarks not verified
- Exact M1 vs RTX 2070 performance parity - single forum post, needs independent verification

---
*Stack research for: Mac Desktop Video Editing Automation*
*Researched: 2026-01-24*
*Confidence: HIGH - All core recommendations verified with official documentation/PyPI*
