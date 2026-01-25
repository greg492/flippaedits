#!/usr/bin/env python3
"""Check disk space and show helpful diagnostics."""

import os
import sys
import tempfile
from pathlib import Path

def format_bytes(bytes_val):
    """Format bytes as human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"

def check_disk_space(path=None):
    """Check available disk space."""
    if path is None:
        # Use temp directory location
        temp_dir = tempfile.gettempdir()
        path = temp_dir

    print(f"Checking disk space for: {path}")
    print()

    stat = os.statvfs(path)

    total_bytes = stat.f_blocks * stat.f_frsize
    available_bytes = stat.f_bavail * stat.f_frsize
    used_bytes = total_bytes - available_bytes

    percent_used = (used_bytes / total_bytes) * 100 if total_bytes > 0 else 0

    print(f"Total:     {format_bytes(total_bytes)}")
    print(f"Used:      {format_bytes(used_bytes)} ({percent_used:.1f}%)")
    print(f"Available: {format_bytes(available_bytes)}")
    print()

    # Check for low disk space
    if percent_used > 95:
        print("⚠️  WARNING: Disk is nearly full (>95% used)!")
        print("   This will cause video import to fail.")
        print()
        print("   Recommended actions:")
        print("   1. Delete unused files to free up space")
        print("   2. Empty Trash")
        print("   3. Remove old downloads")
        print("   4. Move large files to external storage")
        print()
        print(f"   You need at least 5-10GB free for video processing.")
        print(f"   Current free space: {format_bytes(available_bytes)}")
        return False
    elif percent_used > 90:
        print("⚠️  CAUTION: Disk space is getting low (>90% used)")
        print("   Consider freeing up space before importing large videos.")
        print()
        return True
    else:
        print("✓ Disk space is OK")
        print()
        return True

if __name__ == "__main__":
    # Check system disk
    check_disk_space()

    # If an external drive path is provided, check that too
    if len(sys.argv) > 1:
        print("-" * 60)
        print()
        check_disk_space(sys.argv[1])
