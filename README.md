# Flippa Edits - Lacrosse Reel Auto-Editor

Mac desktop application that automatically edits lacrosse highlight videos into social media reels synced to music.

## Features

- Drag-and-drop 4K video import
- Automatic 720p proxy generation
- Music upload with automatic beat detection
- Mark Goal, Celebration, and Beat Drop sync points
- Auto-sync video cuts to music beats
- LUT color grading presets
- Export for Instagram/TikTok (vertical 9:16)

## Requirements

- macOS
- Python 3.10+
- FFmpeg (for audio codec support)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/greg492/flippaedits.git lacrosse-reel-editor
cd lacrosse-reel-editor
git checkout claude/lacrosse-editor-app-snCwd

# Create virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Run the app
PYTHONPATH=. python3 -m src.gui.main_window
```

## Important: After Restarting Terminal

If you restart your terminal, you need to reactivate the virtual environment:

```bash
cd ~/Desktop/lacrosse-reel-editor
source venv/bin/activate
PYTHONPATH=. python3 -m src.gui.main_window
```

The `source venv/bin/activate` command loads all the installed packages. Without it, Python won't find PySide6, librosa, etc.

## Install FFmpeg (for MP3 support)

```bash
brew install ffmpeg
```

## Workflow

1. **Upload** - Drop video and select music file
2. **Mark** - Scrub timeline and mark:
   - **Goal** (green) - The goal moment
   - **Celebration** (orange) - When celebration starts
   - **Drop** (purple) - Beat drop sync point
3. **Color** - Select a LUT preset
4. **Export** - Generate the reel

## Tech Stack

- Python 3.10+
- PyAV 16.1.0 (video processing)
- PySide6 6.10.1 (GUI)
- librosa (beat detection)
- FFmpeg (audio/video codecs)
