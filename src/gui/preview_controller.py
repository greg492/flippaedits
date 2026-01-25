"""Preview controller for generating effects preview.

Manages preview generation workflow: applies LUT and slow-motion
effects to proxy file, then loads result into media player.
"""

import logging
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal, Slot

from ..processing.edit_session import EditSession
from ..processing.effects import apply_effects_chain
from ..storage.temp_manager import get_temp_manager

logger = logging.getLogger(__name__)


class PreviewController(QObject):
    """Controls preview generation with effects applied.

    Generates preview video by processing proxy through effects chain
    (LUT color grading, slow-motion), then signals when ready to play.

    Signals:
        preview_ready: Emitted with path to preview file
        preview_error: Emitted with error message
        progress: Emitted with progress percentage (0-100)
    """

    preview_ready = Signal(str)  # path to preview file
    preview_error = Signal(str)  # error message
    progress = Signal(int)  # 0-100

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._preview_path: Optional[Path] = None

    def generate_preview(
        self,
        session: EditSession,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> str:
        """Generate preview video with all effects applied.

        Uses proxy file for speed. Applies effects in order:
        1. LUT color grading (if selected)
        2. Slow-motion (if speed != 1.0)

        Args:
            session: EditSession with source, proxy, and effect settings
            progress_callback: Optional progress callback

        Returns:
            Path to generated preview file

        Raises:
            ValueError: If session not ready for preview
            Exception: If effects processing fails
        """
        # Validate session
        if not session.is_ready_for_preview():
            raise ValueError("Session not ready for preview - need proxy and goal timestamp")

        if session.proxy_path is None or not session.proxy_path.exists():
            raise ValueError(f"Proxy file not found: {session.proxy_path}")

        logger.info("Generating preview with effects...")

        # Get temp directory for preview output
        temp_manager = get_temp_manager()
        preview_path = temp_manager.temp_dir / "preview_effects.mp4"

        # Get effect settings
        lut_path = None
        if session.color_grading.is_enabled():
            lut_path = str(session.color_grading.lut_path)
            logger.info(f"Applying LUT: {session.color_grading.lut_name}")

        speed = session.slow_motion.speed
        if speed != 1.0:
            logger.info(f"Applying slow-motion: {speed}x")

        # Apply effects chain
        def wrapped_progress(p: int) -> None:
            self.progress.emit(p)
            if progress_callback:
                progress_callback(p)

        try:
            result = apply_effects_chain(
                str(session.proxy_path),
                str(preview_path),
                lut_path=lut_path,
                slow_motion_speed=speed,
                progress_callback=wrapped_progress
            )

            self._preview_path = Path(result)
            logger.info(f"Preview generated: {self._preview_path}")
            return result

        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            raise

    def get_preview_path(self) -> Optional[Path]:
        """Get path to last generated preview."""
        return self._preview_path


__all__ = ['PreviewController']
