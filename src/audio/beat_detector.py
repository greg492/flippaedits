"""Beat detection using librosa with Qt threading support.

This module provides BeatDetectorWorker for background beat detection,
offloading CPU-intensive librosa processing to avoid blocking the GUI.
"""

import subprocess
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import librosa
from PySide6.QtCore import QObject, Signal, QThread


class BeatDetectorWorker(QObject):
    """Worker for background beat detection - librosa is CPU intensive.

    Uses QObject + moveToThread pattern for proper Qt threading.
    Processing takes 5-10 seconds for typical 30-second music clips.

    Signals:
        progress: Status updates during processing
        finished: Beat detection complete - emits (beat_times, onset_envelope, tempo, sr, hop_length)
        error: Error message if detection fails
    """

    progress = Signal(str)  # Status updates
    finished = Signal(object, object, object, int, int)  # (beat_times, onset_envelope, tempo, sr, hop_length)
    error = Signal(str)

    def __init__(self, audio_path: str) -> None:
        """Initialize worker with audio file path.

        Args:
            audio_path: Path to audio file (MP3 or WAV)
        """
        super().__init__()
        self.audio_path = audio_path

    def run(self) -> None:
        """Execute beat detection in background thread.

        Loads audio, computes onset strength, detects beats, and emits results.
        Falls back to 130 BPM grid if detection fails.
        """
        try:
            # Check for MP3 support via FFmpeg
            if self.audio_path.lower().endswith('.mp3'):
                if not self._check_ffmpeg():
                    self.error.emit(
                        "MP3 support requires FFmpeg. Install via: brew install ffmpeg"
                    )
                    return

            self.progress.emit("Loading audio...")

            # Load audio - preserve native sample rate
            # mono=True simplifies beat detection
            y, sr = librosa.load(self.audio_path, sr=None, mono=True)

            self.progress.emit("Analyzing audio...")

            # Compute onset strength with median aggregation (robust for hip-hop/trap)
            # hop_length determines frame spacing - default 512 is standard
            hop_length = 512
            onset_env = librosa.onset.onset_strength(
                y=y,
                sr=sr,
                aggregate=np.median,
                hop_length=hop_length
            )

            self.progress.emit("Detecting beats...")

            # Detect beats with tempo prior for hip-hop/trap (120-150 BPM typical)
            tempo, beat_times = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                start_bpm=130,  # Initial guess for EDM/hip-hop
                units='time',   # Return seconds (not frame indices)
                trim=True,      # Remove spurious trailing beats
                hop_length=hop_length
            )

            # Handle empty beat detection with fallback grid
            if tempo == 0 or len(beat_times) == 0:
                self.progress.emit("Generating fallback beat grid...")
                duration = len(y) / sr
                beat_interval = 60.0 / 130  # 130 BPM default
                beat_times = np.arange(0, duration, beat_interval)
                tempo = 130.0

            # Emit results including sr and hop_length for downstream intensity calculations
            self.finished.emit(beat_times, onset_env, tempo, sr, hop_length)

        except Exception as e:
            error_msg = str(e)
            if "NoBackendError" in error_msg or "audioread" in error_msg:
                self.error.emit(
                    "MP3 support requires FFmpeg. Install via: brew install ffmpeg"
                )
            else:
                self.error.emit(f"Beat detection failed: {error_msg}")

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available for MP3 support.

        Returns:
            True if FFmpeg is installed, False otherwise
        """
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


def detect_beats(
    audio_path: str,
    start_bpm: int = 130
) -> Tuple[np.ndarray, np.ndarray, float, int, int]:
    """Synchronous beat detection for testing.

    This is a convenience function that runs beat detection synchronously.
    For GUI usage, use BeatDetectorWorker with QThread instead.

    Args:
        audio_path: Path to audio file (MP3 or WAV)
        start_bpm: Initial tempo guess (default 130 for hip-hop/EDM)

    Returns:
        Tuple of (beat_times, onset_envelope, tempo, sample_rate, hop_length)

    Raises:
        Exception: If audio loading or beat detection fails

    Note:
        Beat detection latency: Beats may be 20-60ms late due to onset peak
        detection. Consider backtracking for tighter sync (deferred to Phase 4).
    """
    # Load audio
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # Compute onset strength
    hop_length = 512
    onset_env = librosa.onset.onset_strength(
        y=y,
        sr=sr,
        aggregate=np.median,
        hop_length=hop_length
    )

    # Detect beats
    tempo, beat_times = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        start_bpm=start_bpm,
        units='time',
        trim=True,
        hop_length=hop_length
    )

    # Fallback if detection fails
    if tempo == 0 or len(beat_times) == 0:
        duration = len(y) / sr
        beat_interval = 60.0 / start_bpm
        beat_times = np.arange(0, duration, beat_interval)
        tempo = float(start_bpm)

    return beat_times, onset_env, tempo, sr, hop_length
