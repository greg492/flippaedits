"""LUT preset loading and path resolution.

Provides utilities for loading bundled LUT presets and resolving
their file paths for use with FFmpeg's lut3d filter.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class LUTPreset:
    """A color grading LUT preset.

    Attributes:
        name: Display name of the preset (e.g., "Teal & Orange")
        filename: Name of the .cube file
        description: Short description of the look
        path: Resolved absolute path to the .cube file
    """
    name: str
    filename: str
    description: str
    path: Path


def get_luts_directory() -> Path:
    """Get the path to bundled LUTs directory.

    Returns:
        Path to src/assets/luts/ directory
    """
    # Navigate from this file to assets/luts
    return Path(__file__).parent.parent / "assets" / "luts"


def load_lut_registry() -> List[LUTPreset]:
    """Load all available LUT presets from registry.

    Returns:
        List of LUTPreset objects with resolved paths

    Raises:
        FileNotFoundError: If registry file missing
        json.JSONDecodeError: If registry malformed
    """
    luts_dir = get_luts_directory()
    registry_path = luts_dir / "lut_registry.json"

    with open(registry_path, 'r') as f:
        data = json.load(f)

    presets = []
    for entry in data.get("presets", []):
        preset = LUTPreset(
            name=entry["name"],
            filename=entry["file"],
            description=entry.get("description", ""),
            path=luts_dir / entry["file"]
        )
        presets.append(preset)

    return presets


def get_lut_by_name(name: str) -> Optional[LUTPreset]:
    """Get a specific LUT preset by name.

    Args:
        name: Preset display name (e.g., "Teal & Orange")

    Returns:
        LUTPreset if found, None otherwise
    """
    presets = load_lut_registry()
    for preset in presets:
        if preset.name == name:
            return preset
    return None


def validate_lut_file(path: Path) -> bool:
    """Check if a .cube file exists and is readable.

    Args:
        path: Path to .cube file

    Returns:
        True if file exists and has .cube extension
    """
    return path.exists() and path.suffix.lower() == '.cube'
