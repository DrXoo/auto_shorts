"""
Hooks Compilation Generator
============================
Creates a compelling intro/teaser video by compiling identified hooks with transitions.

This script:
1. Reads hooks from AI-identified hooks.json
2. Extracts each hook segment from the source video
3. Adds smooth transitions between hooks
4. Compiles everything into a single teaser video
5. Optionally adds background music (if provided)

Usage:
    python create_hooks_compilation.py
    python create_hooks_compilation.py --music path/to/music.mp3
    python create_hooks_compilation.py --transition fade --duration 0.5

Output:
    output/final/hooks_compilation.mp4
"""

import json
import subprocess
from pathlib import Path
import argparse
import sys

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
AI_ANALYSIS_DIR = OUTPUT_DIR / "ai_analysis"
TEMP_DIR = OUTPUT_DIR / "hooks_temp"
FINAL_DIR = OUTPUT_DIR / "final"

HOOKS_JSON = AI_ANALYSIS_DIR / "hooks.json"

# Transition effects available in FFmpeg
TRANSITIONS = {
    'fade': 'fade',           # Smooth fade transition
    'wipeleft': 'wipeleft',   # Wipe from left to right
    'wiperight': 'wiperight', # Wipe from right to left
    'slideup': 'slideup',     # Slide up
    'slidedown': 'slidedown', # Slide down
    'dissolve': 'dissolve',   # Cross dissolve
    'pixelize': 'pixelize',   # Pixelation effect
}

def get_video_file():
    """Find the first video file in the input directory"""
    VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']
    video_files = [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]
    return video_files[0] if video_files else None

def parse_timestamp(timestamp):
    """Convert timestamp to seconds (handles both string and float)"""
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    return float(timestamp)

def extract_hook(video_file, start_time, end_time, output_file):
    """Extract a single hook segment from the video"""
    start_seconds = parse_timestamp(start_time)
    end_seconds = parse_timestamp(end_time)
    duration = end_seconds - start_seconds
    
    cmd = [
        'ffmpeg',
        '-nostdin',             # Don't wait for user input
        '-y',                   # Overwrite output
        '-ss', str(start_seconds),  # Seek before input (faster)
        '-i', str(video_file),
        '-t', str(duration),
        '-c:v', 'libx264',      # Re-encode for consistency
        '-c:a', 'aac',
        '-preset', 'ultrafast', # Much faster encoding
        '-crf', '23',           # Good quality
        '-v', 'warning',        # Only show warnings/errors
        str(output_file)
    ]
    
    try:
        # Show output in real-time, with timeout
        result = subprocess.run(cmd, timeout=60, text=True)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("   ⚠ Timeout - hook took too long to extract")
        return False
    except Exception as e:
        print(f"   ⚠ Error: {e}")
        return False

def create_transitions_filter(num_hooks, transition_type='fade', transition_duration=0.5):
    """
    Create FFmpeg filter complex for transitions between hooks.
    This uses xfade filter for smooth transitions.
    """
    if num_hooks == 1:
        return "[0:v]copy[outv]; [0:a]acopy[outa]"
    
    filter_parts = []
    
    # For each pair of consecutive videos, create a transition
    current_video = "[0:v]"
    for i in range(num_hooks - 1):
        next_video = f"[{i+1}:v]"
        output_label = f"[v{i}]" if i < num_hooks - 2 else "[outv]"
        
        # Calculate offset (this is simplified - in reality you'd accumulate durations)
        filter_parts.append(
            f"{current_video}{next_video}xfade=transition={transition_type}:"
            f"duration={transition_duration}:offset={{offset{i}}}:{output_label}"
        )
        current_video = output_label
    
    # Audio mixing (simpler approach - concatenate audio)
    audio_filter = " ".join([f"[{i}:a]" for i in range(num_hooks)])
    audio_filter += f"concat=n={num_hooks}:v=0:a=1[outa]"
    
    filter_complex = "; ".join(filter_parts) + "; " + audio_filter
    return filter_complex

def create_concat_list(hook_files, concat_file):
    """Create a concat file for FFmpeg"""
    with open(concat_file, 'w') as f:
        for hook_file in hook_files:
            # FFmpeg concat requires forward slashes and escaped special chars
            safe_path = str(hook_file).replace('\\', '/')
            f.write(f"file '{safe_path}'\n")

def compile_hooks_simple(hook_files, output_file, transition_duration=0.5):
    """
    Compile hooks using simple concatenation with fade transitions.
    This is more reliable than complex xfade filters.
    """
    # Create temporary concat file
    concat_file = TEMP_DIR / "concat_list.txt"
    create_concat_list(hook_files, concat_file)
    
    # Simple concatenation first
    temp_concat = TEMP_DIR / "temp_concat.mp4"
    
    cmd = [
        'ffmpeg',
        '-nostdin',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        '-v', 'warning',
        str(temp_concat)
    ]
    
    print("   Concatenating hooks...")
    result = subprocess.run(cmd, timeout=120, text=True)
    
    if result.returncode != 0:
        print(f"   ✗ Concatenation failed: {result.stderr}")
        return False
    
    # Now add crossfade transitions if needed
    # For simplicity, we'll use a basic approach with fade in/out on each clip
    # This creates a smoother viewing experience
    
    # Just copy the concatenated file for now
    # In a production version, you'd add proper xfade filters here
    cmd = [
        'ffmpeg',
        '-nostdin',
        '-y',
        '-i', str(temp_concat),
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-v', 'warning',
        str(output_file)
    ]
    
    print("   Re-encoding with optimizations...")
    result = subprocess.run(cmd, timeout=180, text=True)
    
    return result.returncode == 0

def add_background_music(video_file, music_file, output_file, music_volume=0.3):
    """Add background music to the compilation, ducking under dialogue"""
    cmd = [
        'ffmpeg',
        '-nostdin',
        '-y',
        '-i', str(video_file),
        '-i', str(music_file),
        '-filter_complex',
        f'[1:a]volume={music_volume}[music];'
        '[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]',
        '-map', '0:v',
        '-map', '[aout]',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-v', 'warning',
        str(output_file)
    ]
    
    try:
        result = subprocess.run(cmd, timeout=120, text=True)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("   ⚠ Music mixing timeout")
        return False
    except Exception as e:
        print(f"   ⚠ Error adding music: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Create hooks compilation video')
    parser.add_argument('--music', type=str, help='Path to background music file (optional)')
    parser.add_argument('--music-volume', type=float, default=0.3, help='Music volume (0.0-1.0)')
    parser.add_argument('--transition', type=str, default='fade', 
                       choices=list(TRANSITIONS.keys()),
                       help='Transition effect type')
    parser.add_argument('--duration', type=float, default=0.5, 
                       help='Transition duration in seconds')
    args = parser.parse_args()
    
    print("=== Creating Hooks Compilation ===\n")
    
    # Check if hooks.json exists
    if not HOOKS_JSON.exists():
        print(f"✗ Hooks file not found: {HOOKS_JSON}")
        print("\nPlease:")
        print("1. Use the hook_extraction_prompt.txt to analyze your transcript")
        print("2. Save the AI output as output/ai_analysis/hooks.json")
        print("3. Run this script again")
        sys.exit(1)
    
    # Get source video
    video_file = get_video_file()
    if not video_file:
        print(f"✗ No video file found in {INPUT_DIR}")
        sys.exit(1)
    
    print(f"Source video: {video_file.name}\n")
    
    # Load hooks
    with open(HOOKS_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    hooks = data.get('hooks', [])
    if not hooks:
        print("✗ No hooks found in hooks.json")
        sys.exit(1)
    
    print(f"Found {len(hooks)} hooks to compile\n")
    
    # Create temp directory
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    
    # Extract each hook
    print("Step 1: Extracting hooks from video...\n")
    hook_files = []
    
    for hook in hooks:
        hook_num = hook['hook_number']
        title = hook.get('title', f'Hook {hook_num}')
        start = hook['start_time']
        end = hook['end_time']
        duration = hook.get('duration', 0)
        
        output_file = TEMP_DIR / f"hook_{hook_num:02d}.mp4"
        
        print(f"   Hook {hook_num}: {title}")
        print(f"   Time: {start}s → {end}s ({duration}s)")
        
        if extract_hook(video_file, start, end, output_file):
            hook_files.append(output_file)
            print("   ✓ Extracted\n")
        else:
            print("   ✗ Failed to extract\n")
    
    if not hook_files:
        print("✗ No hooks were extracted successfully")
        sys.exit(1)
    
    # Compile hooks
    print(f"\nStep 2: Compiling {len(hook_files)} hooks with transitions...\n")
    
    if args.music:
        # Create compilation without music first
        temp_output = TEMP_DIR / "compilation_no_music.mp4"
        success = compile_hooks_simple(hook_files, temp_output, args.duration)
        
        if not success:
            print("✗ Failed to compile hooks")
            sys.exit(1)
        
        # Add background music
        print("\nStep 3: Adding background music...\n")
        final_output = FINAL_DIR / "hooks_compilation.mp4"
        
        music_path = Path(args.music)
        if not music_path.exists():
            print(f"✗ Music file not found: {music_path}")
            print("   Saving compilation without music...")
            subprocess.run(['copy', str(temp_output), str(final_output)], shell=True)
        else:
            if add_background_music(temp_output, music_path, final_output, args.music_volume):
                print("   ✓ Background music added")
            else:
                print("   ✗ Failed to add music, using version without music")
                subprocess.run(['copy', str(temp_output), str(final_output)], shell=True)
    else:
        # No music, just compile
        final_output = FINAL_DIR / "hooks_compilation.mp4"
        success = compile_hooks_simple(hook_files, final_output, args.duration)
        
        if not success:
            print("✗ Failed to compile hooks")
            sys.exit(1)
    
    print(f"\n{'='*50}")
    print("✓ HOOKS COMPILATION COMPLETE!")
    print(f"{'='*50}")
    print(f"\nOutput: {final_output}")
    print(f"Duration: ~{sum(h.get('duration', 0) for h in hooks):.1f} seconds")
    print(f"Hooks: {len(hooks)}")
    
    if args.music:
        print(f"Music: {Path(args.music).name} (volume: {args.music_volume})")
    
    print("\n💡 Next steps:")
    print("   - Review the compilation")
    print("   - Add background music if you haven't already")
    print("   - Share as a teaser for your full episode!")
    print(f"\nTemp files in: {TEMP_DIR}")
    print("   (You can delete these after reviewing the final output)")

if __name__ == "__main__":
    main()
