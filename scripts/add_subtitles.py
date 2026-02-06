import json
import subprocess
from pathlib import Path
import re

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
CANDIDATES_DIR = OUTPUT_DIR / "extracted"
READY_DIR = OUTPUT_DIR / "cropped"
RELEASE_DIR = OUTPUT_DIR / "final"
READ_AI_DIR = OUTPUT_DIR / "ai_analysis"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"

CLIPS_JSON = READ_AI_DIR / "clips.json"
TRANSCRIPT_JSON = TRANSCRIPTS_DIR / "notisias_transcript.json"

def parse_timestamp(timestamp_str):
    """Convert MM:SS or HH:MM:SS to seconds"""
    parts = timestamp_str.split(':')
    
    if len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp_str}")

def seconds_to_ass_time(seconds):
    """Convert seconds to ASS subtitle format: H:MM:SS.CC"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def create_ass_subtitle(words, clip_start_time, output_path):
    """Create an ASS subtitle file with karaoke effect
    
    Customization options:
    - Font: Change 'Montserrat' to any installed font
    - Fontsize: Change '80' for larger/smaller text
    - PrimaryColour: &H00FFFFFF = White text (BGR format: &H00BBGGRR)
    - SecondaryColour: &H0000FFFF = Yellow karaoke effect (change this for karaoke color!)
    - OutlineColour: &H00000000 = Black outline
    - Outline: 5 = outline thickness
    - Shadow: 2 = shadow depth
    - MarginV: 461 = 32% from bottom (461px on 1440px height)
    
    Common colors (in &H00BBGGRR format):
    - White: &H00FFFFFF
    - Yellow: &H0000FFFF
    - Cyan: &H00FFFF00
    - Magenta: &H00FF00FF
    - Red: &H000000FF
    - Green: &H0000FF00
    - Blue: &H00FF0000
    """
    
    # ASS file header with styling
    ass_content = """[Script Info]
Title: Podcast Subtitle
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 810
PlayResY: 1440
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,80,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,10,10,461,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Group words into subtitle chunks (every 3-5 words or by pauses)
    subtitle_chunks = []
    current_chunk = []
    
    for i, word_data in enumerate(words):
        current_chunk.append(word_data)
        
        # Create a new chunk every 4 words or if there's a pause
        if len(current_chunk) >= 4:
            subtitle_chunks.append(current_chunk)
            current_chunk = []
        elif i < len(words) - 1:
            # Check for pause (gap > 0.3 seconds)
            next_word = words[i + 1]
            if next_word['start'] - word_data['end'] > 0.3:
                subtitle_chunks.append(current_chunk)
                current_chunk = []
    
    # Add remaining words
    if current_chunk:
        subtitle_chunks.append(current_chunk)
    
    # Generate ASS dialogue lines with karaoke effect
    for chunk in subtitle_chunks:
        if not chunk:
            continue
        
        # Adjust times relative to clip start
        start_time = chunk[0]['start'] - clip_start_time
        end_time = chunk[-1]['end'] - clip_start_time
        
        # Skip if outside clip range
        if start_time < 0 or end_time < 0:
            continue
        
        # Build karaoke text
        karaoke_text = ""
        for word_data in chunk:
            word = word_data['word']
            word_start = word_data['start'] - clip_start_time - start_time
            word_duration = word_data['end'] - word_data['start']
            
            # Karaoke effect: \k<duration in centiseconds>
            duration_cs = int(word_duration * 100)
            karaoke_text += f"{{\\k{duration_cs}}}{word} "
        
        # Format: Dialogue: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
        dialogue = f"Dialogue: 0,{seconds_to_ass_time(start_time)},{seconds_to_ass_time(end_time)},Default,,0,0,0,,{karaoke_text.strip()}\n"
        ass_content += dialogue
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)
    
    return output_path

def add_subtitles_to_videos():
    """Add ASS subtitles to videos in ready_for_subs folder"""
    
    print("=== Adding Karaoke Subtitles to Videos ===\n")
    
    # Load clips metadata
    print("1. Loading clips data...")
    try:
        with open(CLIPS_JSON, 'r', encoding='utf-8') as f:
            clips = json.load(f)
        print(f"   ✓ Found {len(clips)} clips\n")
    except Exception as e:
        print(f"   ✗ Error loading clips: {e}")
        return
    
    # Load transcript
    print("2. Loading transcript...")
    try:
        with open(TRANSCRIPT_JSON, 'r', encoding='utf-8') as f:
            transcript = json.load(f)
        print(f"   ✓ Loaded transcript with {len(transcript.get('segments', []))} segments\n")
    except Exception as e:
        print(f"   ✗ Error loading transcript: {e}")
        return
    
    # Extract all words with timestamps
    all_words = []
    for segment in transcript.get('segments', []):
        for word_data in segment.get('words', []):
            all_words.append(word_data)
    
    print(f"   ✓ Found {len(all_words)} words with timestamps\n")
    
    # Create release directory if it doesn't exist
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get videos from ready_for_subs folder
    video_files = list(READY_DIR.glob("*.mp4"))
    
    if not video_files:
        print(f"   ✗ No videos found in {READY_DIR}")
        return
    
    print(f"3. Processing {len(video_files)} video(s)...\n")
    
    successful = 0
    failed = 0
    
    for video_file in video_files:
        # Extract clip number from filename (clip_XX_...)
        match = re.search(r'clip_(\d+)_', video_file.name)
        if not match:
            print(f"   ⚠ Skipping {video_file.name} - couldn't parse clip number\n")
            continue
        
        clip_num = int(match.group(1))
        
        # Find matching clip metadata
        clip_data = next((c for c in clips if c.get('clip_number') == clip_num), None)
        if not clip_data:
            print(f"   ⚠ Skipping clip {clip_num} - no metadata found\n")
            continue
        
        print(f"   Clip {clip_num}: {clip_data.get('title', 'Unknown')[:50]}...")
        
        try:
            # Parse clip times
            start_time = parse_timestamp(clip_data['start_time'])
            end_time = parse_timestamp(clip_data['end_time'])
            
            # Get words within this clip's timeframe
            clip_words = [
                w for w in all_words
                if start_time <= w['start'] <= end_time
            ]
            
            if not clip_words:
                print("   ⚠ No words found for this clip time range\n")
                continue
            
            print(f"   Found {len(clip_words)} words in clip")
            
            # Generate ASS subtitle file (temporary, in READY_DIR)
            ass_file = READY_DIR / f"{video_file.stem}.ass"
            create_ass_subtitle(clip_words, start_time, ass_file)
            print(f"   ✓ Generated subtitles: {ass_file.name}")
            
            # Create output with subtitles burned in (save to RELEASE_DIR)
            output_file = RELEASE_DIR / f"{video_file.stem}_subtitled.mp4"
            
            cmd = [
                'ffmpeg',
                '-i', str(video_file),
                '-vf', f"ass={ass_file.name}",
                '-c:a', 'copy',
                '-y',
                str(output_file)
            ]
            
            # Run from READY_DIR to use relative path for ass file
            result = subprocess.run(
                cmd,
                cwd=READY_DIR,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"   ✓ Subtitled video saved: {output_file.name}")
                # Delete .ass file since subtitles are now burned into video
                ass_file.unlink()
                print("   ✓ Cleaned up temporary .ass file\n")
                successful += 1
            else:
                print("   ✗ FFmpeg error:")
                print(f"   {result.stderr[:300]}\n")
                failed += 1
                
        except Exception as e:
            print(f"   ✗ Error: {e}\n")
            failed += 1
    
    print("=" * 60)
    print("\n=== Summary ===")
    print(f"Total videos: {len(video_files)}")
    print(f"✓ Successful: {successful}")
    print(f"✗ Failed: {failed}")
    print(f"\nSubtitled videos saved to: {RELEASE_DIR}")

if __name__ == "__main__":
    add_subtitles_to_videos()
