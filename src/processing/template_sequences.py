"""Template sequences for one-click export patterns.

Provides predefined timing patterns for common lacrosse reel structures.
Templates convert user-marked timestamps into concrete segment lists ready
for video assembly.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from .edit_session import EditSession


@dataclass
class VideoSegment:
    """Definition of a video segment to extract.

    Represents a time range in the source video with optional effects.

    Attributes:
        start_ms: Start time in milliseconds
        end_ms: End time in milliseconds
        effects: Optional effects dict with keys like 'slow_motion', 'lut'
    """
    start_ms: int
    end_ms: int
    effects: Optional[dict] = None


@dataclass
class TemplateSequence:
    """Definition of a one-click template sequence.

    Contains metadata and segment timing patterns for a reel template.

    Attributes:
        name: Display name of template
        description: User-facing description
        segments: List of segment definitions with timing patterns
    """
    name: str
    description: str
    segments: List[dict]  # Each dict: {type, duration_ms, before_timestamp/at_timestamp, effects}


# Standard templates for lacrosse highlight reels
TEMPLATES = {
    'goal_celebration': TemplateSequence(
        name="Goal + Celebration",
        description="Lead-up to goal → slow-mo goal moment → celebration",
        segments=[
            {
                'type': 'leadup',
                'duration_ms': 3000,  # 3 seconds before goal
                'before_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'goal',
                'duration_ms': 2000,  # 2 seconds of goal moment
                'at_timestamp': 'goal_moment',
                'effects': {'slow_motion': 0.5}  # 2x slow-mo
            },
            {
                'type': 'celebration',
                'duration_ms': 4000,  # 4 seconds of celebration
                'at_timestamp': 'celebration_start',
                'effects': None
            }
        ]
    ),

    'full_play': TemplateSequence(
        name="Full Play Sequence",
        description="Approach → goal → slow-mo replay → celebration",
        segments=[
            {
                'type': 'approach',
                'duration_ms': 5000,  # 5 seconds before goal
                'before_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'goal',
                'duration_ms': 1500,  # 1.5 seconds of goal
                'at_timestamp': 'goal_moment',
                'effects': None
            },
            {
                'type': 'replay',
                'duration_ms': 3000,  # 3 seconds replay
                'at_timestamp': 'goal_moment',
                'effects': {'slow_motion': 0.25}  # 4x slow-mo replay
            },
            {
                'type': 'celebration',
                'duration_ms': 3000,  # 3 seconds celebration
                'at_timestamp': 'celebration_start',
                'effects': None
            }
        ]
    )
}


def apply_template(session: EditSession, template_name: str) -> List[VideoSegment]:
    """Apply template sequence to edit session timestamps.

    Converts template definitions into concrete VideoSegment objects
    based on session timestamps (goal_moment_ms, celebration_start_ms).

    Args:
        session: EditSession with marked timestamps
        template_name: Name of template from TEMPLATES dict

    Returns:
        List of VideoSegment objects ready for assembly

    Raises:
        ValueError: If required timestamps not marked or template not found

    Example:
        >>> session = EditSession()
        >>> session.source_path = Path('/tmp/test.mp4')
        >>> session.goal_moment_ms = 10000  # 10s
        >>> session.celebration_start_ms = 15000  # 15s
        >>> segments = apply_template(session, 'goal_celebration')
        >>> len(segments)
        3
        >>> segments[0].end_ms
        10000
        >>> segments[1].start_ms
        10000
    """
    # Validate session has required timestamps
    if not session.is_ready_for_export():
        raise ValueError(
            "Session must have goal_moment and celebration_start marked for export. "
            f"Current state: goal_moment_ms={session.goal_moment_ms}, "
            f"celebration_start_ms={session.celebration_start_ms}"
        )

    # Get template
    template = TEMPLATES.get(template_name)
    if not template:
        available = ', '.join(TEMPLATES.keys())
        raise ValueError(
            f"Template '{template_name}' not found. "
            f"Available templates: {available}"
        )

    segments = []

    for seg_def in template.segments:
        # Calculate start/end times based on template timing
        if 'before_timestamp' in seg_def:
            # Segment ends at timestamp
            timestamp_name = seg_def['before_timestamp']
            end_ms = getattr(session, timestamp_name + '_ms')
            start_ms = end_ms - seg_def['duration_ms']

        elif 'at_timestamp' in seg_def:
            # Segment starts at timestamp
            timestamp_name = seg_def['at_timestamp']
            start_ms = getattr(session, timestamp_name + '_ms')
            end_ms = start_ms + seg_def['duration_ms']

        else:
            raise ValueError(
                f"Segment definition must specify 'before_timestamp' or 'at_timestamp'. "
                f"Got: {seg_def}"
            )

        # Create VideoSegment with clamped start (don't go negative)
        segments.append(VideoSegment(
            start_ms=max(0, start_ms),  # Clamp to video start
            end_ms=end_ms,
            effects=seg_def.get('effects')
        ))

    return segments


# Module exports
__all__ = [
    'VideoSegment',
    'TemplateSequence',
    'TEMPLATES',
    'apply_template',
]
