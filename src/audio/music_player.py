"""Music player wrapper for timeline synchronization.

Provides a QMediaPlayer wrapper with millisecond-accurate position control
and signal-based patterns for timeline integration.
"""

from pathlib import Path
from typing import Union, Optional

from PySide6.QtCore import QObject, Signal, QUrl, Slot
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class MusicPlayer(QObject):
    """Wrapper for QMediaPlayer with millisecond-accurate position control.

    Handles asynchronous duration loading and provides signals for
    timeline synchronization. Follows the same pattern as VideoPreviewWidget
    for consistency across the application.

    Signals:
        position_changed: int (milliseconds)
        duration_changed: int (milliseconds)
        playback_state_changed: QMediaPlayer.PlaybackState
        error_occurred: str (error message)

    Example:
        >>> from PySide6.QtWidgets import QApplication
        >>> app = QApplication([])
        >>> player = MusicPlayer()
        >>> player.duration_changed.connect(lambda ms: print(f"Duration: {ms}ms"))
        >>> player.load("/path/to/music.mp3")
        >>> player.play()
    """

    position_changed = Signal(int)  # Milliseconds
    duration_changed = Signal(int)  # Milliseconds
    playback_state_changed = Signal(object)  # QMediaPlayer.PlaybackState
    error_occurred = Signal(str)  # Error message

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize music player.

        Args:
            parent: Parent QObject (must be on main thread)
        """
        super().__init__(parent)

        # Create media player and audio output
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)

        # Connect audio output to player
        self.player.setAudioOutput(self.audio_output)

        # Connect internal signals to slot methods for forwarding
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_error)

    @Slot(int)
    def _on_position_changed(self, position: int) -> None:
        """Forward position changes.

        Args:
            position: Position in milliseconds
        """
        self.position_changed.emit(position)

    @Slot(int)
    def _on_duration_changed(self, duration: int) -> None:
        """Forward duration changes.

        Args:
            duration: Duration in milliseconds
        """
        self.duration_changed.emit(duration)

    @Slot(object)
    def _on_playback_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        """Forward playback state changes.

        Args:
            state: Playback state enum value
        """
        self.playback_state_changed.emit(state)

    def load(self, file_path: Union[str, Path]) -> None:
        """Load music file.

        Duration will be available asynchronously via duration_changed signal.
        Use QUrl.fromLocalFile for proper file path handling.

        Args:
            file_path: Path to audio file (MP3, WAV, etc.)

        Note:
            Duration is 0 until durationChanged signal fires.
        """
        path = Path(file_path)
        if not path.exists():
            self.error_occurred.emit(f"File not found: {file_path}")
            return

        url = QUrl.fromLocalFile(str(path.resolve()))
        self.player.setSource(url)

    def play(self) -> None:
        """Start playback."""
        self.player.play()

    def pause(self) -> None:
        """Pause playback."""
        self.player.pause()

    def stop(self) -> None:
        """Stop playback and reset position to beginning."""
        self.player.stop()

    def seek_ms(self, position_ms: int) -> None:
        """Seek to position in milliseconds.

        Args:
            position_ms: Target position in milliseconds

        Note:
            Seeking is asynchronous. Position will update via position_changed signal.
        """
        if self.player.isSeekable():
            self.player.setPosition(position_ms)
        else:
            self.error_occurred.emit("Media is not seekable")

    def set_volume(self, volume_0_to_1: float) -> None:
        """Set playback volume.

        Args:
            volume_0_to_1: Volume level from 0.0 (muted) to 1.0 (full volume)
        """
        # Clamp to valid range
        volume = max(0.0, min(1.0, volume_0_to_1))
        self.audio_output.setVolume(volume)

    def get_position_ms(self) -> int:
        """Get current playback position.

        Returns:
            Current position in milliseconds
        """
        return self.player.position()

    def get_duration_ms(self) -> int:
        """Get total duration.

        Returns:
            Total duration in milliseconds (may be 0 until media loads)

        Note:
            Duration becomes available asynchronously via duration_changed signal.
        """
        return self.player.duration()

    def is_playing(self) -> bool:
        """Check if currently playing.

        Returns:
            True if playing, False otherwise
        """
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def is_seekable(self) -> bool:
        """Check if media supports seeking.

        Returns:
            True if seeking is supported, False otherwise
        """
        return self.player.isSeekable()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        """Handle player errors.

        Args:
            error: QMediaPlayer.Error enum value
            error_string: Human-readable error message
        """
        self.error_occurred.emit(f"Player error: {error_string}")


__all__ = ['MusicPlayer']
