"""Video export utilities for social media platforms.

Provides vertical 9:16 export optimized for Instagram Reels and TikTok
with center crop, scale, and high-bitrate H.264 encoding.
"""

from typing import Optional, Callable
import av


def create_vertical_crop_graph(input_stream, target_width: int = 1080, target_height: int = 1920):
    """Create filter graph to crop 16:9 to 9:16 vertical format.

    Center crops horizontal video to vertical aspect ratio, then scales to target resolution.
    For 3840x2160 (4K 16:9) source: crops to 1215x2160, scales to 1080x1920.

    Args:
        input_stream: PyAV video stream (16:9 or similar horizontal aspect)
        target_width: Output width (1080 for Instagram/TikTok standard)
        target_height: Output height (1920 for Instagram/TikTok standard)

    Returns:
        Configured filter graph ready for push/pull operations
    """
    graph = av.filter.Graph()

    # Add buffer with template from input stream
    buffer_src = graph.add_buffer(template=input_stream)

    # Center crop to 9:16 aspect ratio
    # Formula: crop width = input_height * 9/16, centered horizontally
    # crop=w=ih*9/16:h=ih:x=(iw-ow)/2:y=0
    crop_filter = graph.add("crop", "w=ih*9/16:h=ih:x=(iw-ow)/2:y=0")

    # Scale to target resolution
    scale_filter = graph.add("scale", f"{target_width}:{target_height}")

    # Add sink
    buffer_sink = graph.add("buffersink")

    # Link: buffer -> crop -> scale -> sink
    buffer_src.link_to(crop_filter)
    crop_filter.link_to(scale_filter)
    scale_filter.link_to(buffer_sink)

    graph.configure()
    return graph


__all__ = ['create_vertical_crop_graph']
