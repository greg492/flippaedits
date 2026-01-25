# Debug: 10% Failure Issue - SOLVED

## Summary

**Issue:** Application gets to 10% progress then fails when importing video.

**Root Cause:** Disk is 100% full (460GB used, only 93MB available), causing file operations to timeout or fail.

**Solution:** Added disk space checks with clear error messages + detailed logging for debugging.

---

## What Was Happening

The import workflow follows these steps:

1. **0-5%**: Initial validation
2. **5-10%**: Get video metadata ✓ (this worked)
3. **10-15%**: Copy video from external drive (if needed) ← **FAILED HERE**
4. **15-100%**: Generate 720p proxy

At 10%, the code attempts to copy the video from the external drive to temporary storage. When disk is full:

- `shutil.copy2()` fails with `OSError: [Errno 28] No space left on device`
- Error was caught but message wasn't clear to user
- No logging made it hard to debug

---

## Changes Made

### 1. Disk Space Validation (`temp_manager.py`)

**Before:** Attempted to copy, failed with generic error.

**After:** Checks available space BEFORE copying:
- Requires 2x video file size (1x for copy, 1x for proxy)
- Shows clear message: "Not enough disk space. Need 8.5GB, only 0.1GB available."

### 2. Proxy Generation Validation (`proxy.py`)

**Before:** Started encoding, failed midway if disk full.

**After:** Checks available space BEFORE encoding:
- Estimates proxy size (~15% of source for 720p from 4K)
- Prevents wasting time on doomed operation
- Shows clear message about disk space needed

### 3. Error Messages

**Before:**
```
Error: Failed to copy video to temp storage: [Errno 28] No space left on device
```

**After:**
```
Error: Disk full! Cannot copy video. Please free up disk space and try again.
```

### 4. Detailed Logging (`main_window.py`)

Added logging at each step to help debug issues:
```
INFO - Starting import workflow for: /Volumes/BACKUP/video.mp4
INFO - Getting video metadata...
INFO - Video info: 3840x2160 @ 60.0fps
INFO - File is on external drive, copying to temp storage...
ERROR - Copy failed: Not enough disk space...
```

View logs in Terminal when running the app.

---

## How to Fix Your System

### Check Disk Space

Run this command:
```bash
python3 check_disk_space.py
```

You should see:
```
Total:     460.0 GB
Used:      437.0 GB (95.0%)
Available: 93.0 MB

⚠️  WARNING: Disk is nearly full (>95% used)!
   This will cause video import to fail.
```

### Free Up Disk Space

**Quick wins:**
1. Empty Trash
2. Delete downloads folder old files
3. Remove unused applications
4. Clear system caches: `~/Library/Caches/`
5. Delete old iOS backups: `~/Library/Application Support/MobileSync/Backup/`

**Target:** At least 5-10GB free for comfortable video processing.

### Verify Fix

After freeing space:
```bash
python3 check_disk_space.py
```

Should show:
```
Available: 10.5 GB
✓ Disk space is OK
```

---

## Testing the Fix

### Option 1: Run with Logging

```bash
cd /Users/gcproductions/Desktop/lacrosse-reel-editor
python3 -m src.gui.main_window
```

You'll see detailed logs in Terminal showing exactly where it fails:
- What step is running
- Video info extracted
- Whether copy is needed
- Exact error if it fails

### Option 2: Create Test Video

If you want to test with a smaller file:

```bash
# Create a small test video (requires ffmpeg)
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 \
  -pix_fmt yuv420p test_video.mp4
```

Then drag-drop this into the app.

---

## What the App Will Show Now

### If Disk is Full (Before Copy)

```
Error: Not enough disk space. Need 8.5GB, only 0.1GB available.
Please free up disk space and try again.
```

### If Disk is Full (During Proxy Generation)

```
Error: Not enough disk space to generate proxy. Need ~1.2GB,
only 0.1GB available. Please free up disk space and try again.
```

### If Disk is Full (During Encoding)

```
Error: Disk full! Cannot generate proxy. Please free up disk
space and try again.
```

---

## Prevention

The app now checks disk space at TWO points:

1. **Before copying** from external drive
2. **Before generating** proxy

This prevents starting long operations that are doomed to fail.

---

## Still Having Issues?

### Enable Debug Logging

Edit `src/gui/main_window.py` line 18:
```python
# Change from INFO to DEBUG
logging.basicConfig(level=logging.DEBUG, ...)
```

### Check Logs

All errors are now logged with context:
```
ERROR - Copy failed: [detailed error]
ERROR - Proxy generation failed: [detailed error]
```

### Common Issues

**"Operation timed out" during import:**
- External drive is disconnected or slow
- Try copying video to Desktop first, then import

**"Permission denied":**
- Video file is locked or in use
- Close other video apps (QuickTime, VLC, etc.)

**App crashes at 10%:**
- If it's not disk space, check logs for actual error
- Might be corrupted video file
- Try different video file

---

## Technical Details

### Disk Space Requirements

For a typical 4K 60fps video (150MB, 30 seconds):
- **Source:** 150MB
- **Temp copy:** 150MB (if on external drive)
- **720p proxy:** ~20MB (15% of source)
- **Total needed:** ~320MB (with safety margin)

For a longer 4K video (2GB, 5 minutes):
- **Source:** 2GB
- **Temp copy:** 2GB
- **720p proxy:** ~300MB
- **Total needed:** ~4.3GB

### Error Codes

- **Errno 28 (ENOSPC):** No space left on device
- **Errno 60:** Operation timed out (external drive issue)
- **Errno 13 (EACCES):** Permission denied

All are now caught and translated to user-friendly messages.

---

## Summary

**The fix is deployed.** The app will now:

1. ✓ Check disk space before operations
2. ✓ Show clear error messages
3. ✓ Log detailed progress for debugging
4. ✓ Prevent starting doomed operations

**Your action:** Free up disk space (currently 100% full) and the app should work correctly.
