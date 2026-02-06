import json
import subprocess
from pathlib import Path
import re

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
CLIPS_DIR = OUTPUT_DIR / "extracted"
READ_AI_DIR = OUTPUT_DIR / "ai_analysis"

VIDEO_FILE = INPUT_DIR / "notisias.mp4"
CLIPS_JSON = READ_AI_DIR / "clips.json"

# Create output directory
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

print("=== Extracting Video Clips with FFmpeg ===\n")

def parse_timestamp(timestamp_str):
    """Convert MM:SS or HH:MM:SS to seconds"""
    parts = timestamp_str.split(':')
    
    if len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    elif len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

def sanitize_filename(title):
    """Clean title to make it a valid filename"""
    # Remove special characters, keep only alphanumeric, spaces, and hyphens
    clean = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    clean = re.sub(r'\s+', '_', clean)
    # Limit length
    return clean[:60]

# Load clips JSON
print("1. Loading clips data...")
try:
    with open(CLIPS_JSON, 'r', encoding='utf-8') as f:
        clips = json.load(f)
    print(f"   ✓ Found {len(clips)} clips to extract\n")
except Exception as e:
    print(f"   ✗ Error: {e}")
    exit(1)

# Check if video file exists
if not VIDEO_FILE.exists():
    print(f"   ✗ Video file not found: {VIDEO_FILE}")
    exit(1)

print(f"2. Video file: {VIDEO_FILE}\n")
print("3. Extracting clips...\n")

successful = 0
failed = 0

for clip in clips:
    clip_num = clip.get('clip_number', 0)
    title = clip.get('title', f'Clip {clip_num}')
    start_time = clip.get('start_time', '0:00')
    end_time = clip.get('end_time', '0:00')
    
    try:
        # Parse timestamps
        start_seconds = parse_timestamp(start_time)
        end_seconds = parse_timestamp(end_time)
        duration = end_seconds - start_seconds
        
        # Create filename
        safe_title = sanitize_filename(title)
        output_file = CLIPS_DIR / f"clip_{clip_num:02d}_{safe_title}.mp4"
        
        print(f"   Clip {clip_num}: {title[:50]}...")
        print(f"   Time: {start_time} → {end_time} ({duration}s)")
        
        # FFmpeg command
        # -ss: start time, -t: duration, -c copy: fast copy without re-encoding
        # For more precision, we'll re-encode with -c:v libx264 -c:a aac
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-ss', str(start_seconds),  # Start time
            '-i', str(VIDEO_FILE),  # Input file
            '-t', str(duration),  # Duration
            '-c:v', 'libx264',  # Video codec
            '-c:a', 'aac',  # Audio codec
            '-b:a', '192k',  # Audio bitrate
            '-preset', 'fast',  # Encoding speed
            '-avoid_negative_ts', 'make_zero',  # Fix timestamp issues
            str(output_file)
        ]
        
        # Run FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            print(f"   ✓ Saved to: {output_file.name}\n")
            successful += 1
        else:
            print("   ✗ FFmpeg error:")
            print(f"   {result.stderr[:200]}\n")
            failed += 1
            
    except Exception as e:
        print(f"   ✗ Error: {e}\n")
        failed += 1

print("=" * 50)
print("\n=== Summary ===")
print(f"Total clips: {len(clips)}")
print(f"✓ Successful: {successful}")
print(f"✗ Failed: {failed}")
print(f"\nClips saved to: {CLIPS_DIR}")

if successful > 0:
    print("\n🎬 Ready to upload to TikTok/Instagram/YouTube Shorts!")
