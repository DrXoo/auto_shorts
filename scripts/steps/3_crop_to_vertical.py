import subprocess
from pathlib import Path
import numpy as np
import json
from collections import defaultdict
import re

# ============= CROP CONFIGURATION =============
# Adjust these values to match your podcast camera setup

# ============= EPISODE CONFIGURATION =============
# Set this at the start of each episode processing
EPISODE_CONFIG = {
    'num_speakers': None,  # Set to 3, 4, or 5 (will be prompted if None)
}
# ==================================================

# ============= CROP POSITIONS BY SCENE TYPE =============
# Each speaker count (3, 4, 5) has TWO scene types:
#   - 'speakers': Main discussion scene (triangle/grid pattern)
#   - 'content': Content sharing scene (speakers + screen)

# 3 SPEAKERS - Two scenes
CROP_POSITIONS_3 = {
    'speakers': [
        # Triangle pattern - 3 speakers
        {'x': 30, 'y': 30, 'width': 1180, 'height': 685},     # Top-left
        {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},   # Top-right
        {'x': 684, 'y': 715, 'width': 1180, 'height': 685}    # Bottom-center
    ],
    'content': {
        # Single crop - speakers on right side
        'x': 1728,
        'y': 0,
        'width': 810,
        'height': 1440
    }
}

# 4 SPEAKERS - Two scenes
# TODO: Adjust these coordinates based on your actual camera setup
CROP_POSITIONS_4 = {
    'speakers': [
        # Main discussion scene - 4 speaker positions (adjust these!)
        {'x': 30, 'y': 30, 'width': 1180, 'height': 685},     # Position 0: Top-left
        {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},   # Position 1: Top-right
        {'x': 30, 'y': 715, 'width': 1180, 'height': 685},    # Position 2: Bottom-left
        {'x': 1342, 'y': 715, 'width': 1180, 'height': 685}   # Position 3: Bottom-right
    ],
    'content': [
        # Content sharing scene - 4 speaker positions (smaller/different layout)
        # Shows 3 most active speakers in different positions to fit with content
        # TODO: Adjust these to match your content-sharing camera layout!
        {'x': 1600, 'y': 0, 'width': 900, 'height': 480},     # Position 0: Adjusted for content
        {'x': 1600, 'y': 480, 'width': 900, 'height': 480},   # Position 1: Adjusted for content
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480},   # Position 2: Adjusted for content
        {'x': 1600, 'y': 960, 'width': 900, 'height': 480}    # Position 3: Adjusted for content
    ]
}

# 5 SPEAKERS - Two scenes
CROP_POSITIONS_5 = {
    'speakers': [
        {'x': 58, 'y': 169, 'width': 778, 'height': 437},
        {'x': 895, 'y': 160, 'width': 778, 'height': 437},
        {'x': 1726, 'y': 160, 'width': 778, 'height': 437},
        {'x': 436, 'y': 825, 'width': 778, 'height': 437},
        {'x': 1271, 'y': 818, 'width': 778, 'height': 437}
    ],
    'content': [
        {'x': 72, 'y': 58, 'width': 708, 'height': 398},
        {'x': 917, 'y': 58, 'width': 708, 'height': 398},
        {'x': 1777, 'y': 58, 'width': 708, 'height': 398},
        {'x': 1777, 'y': 518, 'width': 708, 'height': 398},
        {'x': 1777, 'y': 993, 'width': 708, 'height': 398}
    ]
}

# Map number of speakers to their crop configurations
CROP_CONFIGS = {
    3: CROP_POSITIONS_3,
    4: CROP_POSITIONS_4,
    5: CROP_POSITIONS_5
}
# =========================================================

# ============= SPEAKER-TO-POSITION MAPPING =============
# Maps speaker IDs from transcript to position indices in the 'speakers' scene
# Adjust based on where each person sits in your camera setup
SPEAKER_MAPPING = {
    3: {  # For 3-person episodes
        'SPEAKER_00': 0,  # Top-left
        'SPEAKER_01': 1,  # Top-right
        'SPEAKER_02': 2,  # Bottom-center
    },
    4: {  # For 4-person episodes (adjust based on seating!)
        'SPEAKER_00': 0,  # Top-left
        'SPEAKER_01': 1,  # Top-right
        'SPEAKER_02': 2,  # Bottom-left
        'SPEAKER_03': 3,  # Bottom-right
    },
    5: {  # For 5-person episodes (adjust based on seating!)
        'SPEAKER_00': 0,
        'SPEAKER_01': 1,
        'SPEAKER_02': 2,
        'SPEAKER_03': 3,
        'SPEAKER_04': 4,
    }
}

# Dynamic cropping configuration
DYNAMIC_CONFIG = {
    'enabled': True,  # Enable speaker-aware dynamic cropping for 4+ speakers
    'speakers_shown': 3,  # How many speakers to show at once (recommended: 3)
    'transition_duration': 0.5,  # Crossfade duration in seconds (future feature)
    'min_segment_duration': 2.0,  # Minimum seconds before switching speakers
}
# ========================================================

# ============= AUTO-DETECTION CONFIGURATION =============
# Define a reference pixel that differs between 'speakers' and 'content' scenes
# Use find_crop_positions.py to find good reference pixels for your setup

AUTO_DETECT = {
    'enabled': True,  # Set to False to manually choose scene for each video
    'default': {
        'pixel_position': (82, 1156),  # (x, y) coordinate to check
        # Define color ranges for each scene type (BGR format)
        # 'speakers' = main discussion scene (triangle/grid pattern)
        # 'content' = content sharing scene (speakers + screen)
        'speakers_color': (0, 0, 0),        # Pixel color in speakers scene
        'content_color': (0, 216, 217),     # Pixel color in content scene
        # Maximum color distance to consider a match (increase if detection fails)
        'tolerance': 100
    },
    # Override per speaker count (set these to match each layout)
    'by_num_speakers': {
        # 3: { 'pixel_position': (x, y), 'speakers_color': (...), 'content_color': (...), 'tolerance': 100 },
        # 4: { 'pixel_position': (x, y), 'speakers_color': (...), 'content_color': (...), 'tolerance': 100 },
        5: { 'pixel_position': (178, 1352), 'speakers_color': (0, 0, 7), 'content_color': (23, 197, 200), 'tolerance': 100 },
    }
}
# ==========================================================

def extract_frame(video_path, time_sec=5):
    """Extract a frame from the video at specified time"""
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-ss', str(time_sec),
        '-vframes', '1',
        '-f', 'image2pipe',
        '-pix_fmt', 'bgr24',
        '-vcodec', 'rawvideo',
        '-'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Get video dimensions
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=p=0',
            str(video_path)
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        width, height = map(int, probe_result.stdout.strip().split(','))
        
        # Decode the raw video frame
        frame = np.frombuffer(result.stdout, dtype=np.uint8)
        frame = frame.reshape((height, width, 3))
        
        return frame
    except Exception as e:
        print(f"Error extracting frame: {e}")
        return None

def get_auto_detect_config(num_speakers):
    override = AUTO_DETECT.get('by_num_speakers', {}).get(num_speakers, {})
    base = AUTO_DETECT.get('default', {})
    merged = base.copy()
    merged.update(override)
    return merged

def detect_crop_mode(video_file, num_speakers):
    """Automatically detect which scene type: 'speakers' or 'content'"""
    if not AUTO_DETECT['enabled']:
        return None  # Manual mode

    detect_cfg = get_auto_detect_config(num_speakers)
    
    # Extract a frame
    frame = extract_frame(video_file, time_sec=5)
    if frame is None:
        print("  ⚠ Could not extract frame for auto-detection")
        return None
    
    # Get pixel color at reference position
    x, y = detect_cfg['pixel_position']
    if y >= frame.shape[0] or x >= frame.shape[1]:
        print(f"  ⚠ Reference pixel position ({x}, {y}) is out of bounds")
        return None
    
    pixel_color = frame[y, x]
    
    # Calculate color distance to each scene's reference color
    speakers_color = np.array(detect_cfg['speakers_color'])
    content_color = np.array(detect_cfg['content_color'])
    
    dist_speakers = np.linalg.norm(pixel_color - speakers_color)
    dist_content = np.linalg.norm(pixel_color - content_color)
    
    # Determine which scene is closer
    if dist_speakers < dist_content and dist_speakers < detect_cfg['tolerance']:
        detected_scene = 'speakers'
    elif dist_content < dist_speakers and dist_content < detect_cfg['tolerance']:
        detected_scene = 'content'
    else:
        print(f"  ⚠ Pixel color {tuple(pixel_color)} doesn't match either scene")
        print(f"     Distance to speakers: {dist_speakers:.1f}, Distance to content: {dist_content:.1f}")
        return None
    
    print(f"  🎯 Auto-detected: {detected_scene.upper()} scene")
    print(f"     Pixel at ({x}, {y}) = {tuple(pixel_color)}")
    
    return detected_scene

def find_transcript_for_clip(clip_file, base_dir):
    """Find the matching transcript JSON for a given clip file"""
    transcripts_dir = base_dir / "output" / "transcripts"
    
    # Extract the base name (without clip number and suffix)
    # e.g., "video_clip_001.mp4" -> "video"
    clip_base = clip_file.stem.rsplit('_clip_', 1)[0] if '_clip_' in clip_file.stem else clip_file.stem
    
    # Look for matching transcript
    possible_transcripts = [
        transcripts_dir / f"{clip_base}_transcript.json",
        transcripts_dir / f"{clip_base.lower()}_transcript.json",
    ]
    
    # Also check for any transcript files
    for transcript_file in transcripts_dir.glob("*_transcript.json"):
        if transcript_file not in possible_transcripts:
            possible_transcripts.append(transcript_file)
    
    for transcript_path in possible_transcripts:
        if transcript_path.exists():
            return transcript_path
    
    return None

def get_clip_timestamps(clip_file, base_dir):
    """
    Get the original timestamps for a clip from clips.json
    Returns (start_seconds, end_seconds) or None if not found
    """
    clips_json_path = base_dir / "output" / "ai_analysis" / "clips.json"
    
    if not clips_json_path.exists():
        print(f"  ⚠️ clips.json not found at {clips_json_path}")
        return None
    
    # Extract clip number from filename (e.g., "clip_01_title.mp4" -> 1)
    match = re.search(r'clip_(\d+)', clip_file.stem)
    if not match:
        print(f"  ⚠️ Could not extract clip number from {clip_file.name}")
        return None
    
    clip_number = int(match.group(1))
    
    try:
        with open(clips_json_path, 'r', encoding='utf-8') as f:
            clips_data = json.load(f)
        
        # Find the matching clip
        for clip in clips_data:
            if clip.get('clip_number') == clip_number:
                start_time_str = clip.get('start_time', '')
                end_time_str = clip.get('end_time', '')
                
                # Parse time strings (format: "MM:SS" or "HH:MM:SS")
                def parse_time(time_str):
                    parts = time_str.split(':')
                    if len(parts) == 2:  # MM:SS
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:  # HH:MM:SS
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    return 0
                
                start_seconds = parse_time(start_time_str)
                end_seconds = parse_time(end_time_str)
                
                return (start_seconds, end_seconds)
        
        print(f"  ⚠️ Clip {clip_number} not found in clips.json")
        return None
        
    except Exception as e:
        print(f"  ⚠️ Error reading clips.json: {e}")
        return None

def analyze_speaker_timeline(transcript_path, clip_start, clip_end):
    """
    Analyze the transcript to determine which speaker is talking at each time
    Returns a list of (start_time, end_time, speaker_id) tuples
    """
    with open(transcript_path, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    # Build speaker timeline from word-level timestamps
    speaker_segments = []
    current_speaker = None
    segment_start = None
    
    for segment in transcript_data.get('segments', []):
        for word in segment.get('words', []):
            word_start = word.get('start', 0)
            word_end = word.get('end', 0)
            speaker = word.get('speaker', 'UNKNOWN')
            
            # Filter to clip time range
            if word_end < clip_start or word_start > clip_end:
                continue
            
            # Adjust times relative to clip
            adjusted_start = max(word_start - clip_start, 0)
            
            if speaker != current_speaker:
                # Save previous segment if exists
                if current_speaker is not None and segment_start is not None:
                    speaker_segments.append((segment_start, adjusted_start, current_speaker))
                
                # Start new segment
                current_speaker = speaker
                segment_start = adjusted_start
    
    # Add final segment
    if current_speaker is not None and segment_start is not None:
        speaker_segments.append((segment_start, clip_end - clip_start, current_speaker))
    
    return speaker_segments

def calculate_speaker_activity(speaker_timeline, num_speakers, speaker_mapping):
    """
    Calculate how much each speaker talks in the clip
    Returns list of speaker IDs sorted by talk time (descending)
    """
    talk_time = defaultdict(float)
    
    # Calculate total talk time for each speaker
    for start_time, end_time, speaker_id in speaker_timeline:
        duration = end_time - start_time if end_time != float('inf') else 0
        talk_time[speaker_id] += duration
    
    # Get all speakers from mapping
    all_speakers = sorted(speaker_mapping.keys())
    
    # Sort speakers by talk time (descending)
    sorted_speakers = sorted(all_speakers, key=lambda s: talk_time.get(s, 0), reverse=True)
    
    return sorted_speakers, talk_time

def select_speakers_to_show(speaker_timeline, num_speakers, speakers_shown=3):
    """
    Determine which speakers to show at each point in time
    Returns list of (start_time, end_time, [speaker_ids]) tuples
    """
    if num_speakers <= speakers_shown:
        # Show all speakers all the time
        all_speakers = set()
        for _, _, speaker in speaker_timeline:
            all_speakers.add(speaker)
        return [(0, float('inf'), sorted(list(all_speakers)))]
    
    display_segments = []
    current_speakers = []
    segment_start = 0
    recent_speakers = []  # Track recently active speakers
    
    for seg_start, seg_end, active_speaker in speaker_timeline:
        # Determine which speakers to show
        # Priority: active speaker + most recent other speakers
        if active_speaker not in recent_speakers:
            recent_speakers.insert(0, active_speaker)
        else:
            # Move to front if already in list
            recent_speakers.remove(active_speaker)
            recent_speakers.insert(0, active_speaker)
        
        # Select top N speakers
        selected = recent_speakers[:speakers_shown]
        
        # If selection changed, create new segment
        if selected != current_speakers:
            if current_speakers:
                display_segments.append((segment_start, seg_start, current_speakers.copy()))
            current_speakers = selected.copy()
            segment_start = seg_start
    
    # Add final segment
    if current_speakers:
        display_segments.append((segment_start, float('inf'), current_speakers))
    
    return display_segments

def get_speaker_positions(num_speakers):
    """Get the crop positions for speakers scene based on number of speakers"""
    return CROP_CONFIGS.get(num_speakers, {}).get('speakers', [])

def prompt_num_speakers():
    """Prompt user for number of speakers if not configured"""
    if EPISODE_CONFIG['num_speakers'] is not None:
        return EPISODE_CONFIG['num_speakers']
    
    print("\n" + "="*60)
    print("Episode Configuration".center(60))
    print("="*60)
    print("\nHow many people are in this episode?")
    print("  3 = Core podcast (3 people)")
    print("  4 = Core + 1 guest")
    print("  5 = Core + 2 guests")
    
    while True:
        choice = input("\nEnter number of speakers (3-5): ").strip()
        if choice in ['3', '4', '5']:
            num = int(choice)
            print(f"\n✓ Episode configured for {num} speakers")
            print("="*60 + "\n")
            return num
        else:
            print("  ⚠️ Please enter 3, 4, or 5")

def crop_to_vertical():
    """
    Crop videos from candidates folder to 9:16 aspect ratio for TikTok/Instagram/YouTube Shorts.
    Original resolution: 2560x1440
    Target resolution: 810x1440 (9:16 aspect ratio)
    """
    
    # Define paths
    base_dir = Path(__file__).parent.parent.parent  # Go up three levels: steps -> scripts -> project root
    candidates_dir = base_dir / "output" / "extracted"
    output_dir = base_dir / "output" / "cropped"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Prompt for number of speakers in this episode
    num_speakers = prompt_num_speakers()
    
    # Get configuration for this number of speakers
    if num_speakers not in CROP_CONFIGS:
        print(f"❌ No configuration found for {num_speakers} speakers")
        return
    
    crop_config = CROP_CONFIGS[num_speakers]
    
    # Get all video files from candidates folder
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    video_files = [f for f in candidates_dir.iterdir() 
                   if f.is_file() and f.suffix.lower() in video_extensions]
    
    if not video_files:
        print(f"No video files found in {candidates_dir}")
        return
    
    print(f"Found {len(video_files)} video(s) to process")
    print(f"Episode: {num_speakers} speakers")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for idx, video_file in enumerate(video_files, 1):
        print(f"\n[{idx}/{len(video_files)}] {video_file.name}")
        
        # Auto-detect scene type (speakers vs content)
        scene_type = detect_crop_mode(video_file, num_speakers)
        
        if scene_type is None:
            # Manual mode selection
            print("\nScene type:")
            print("  1 = Content sharing scene")
            print("  2 = Speakers scene (main discussion)")
            print("  Q = Skip this video")
            
            scene_choice = input("\nYour choice (1/2/Q): ").strip().lower()
            
            if scene_choice == 'q':
                print("⊗ Skipped\n")
                continue
            elif scene_choice == '2':
                scene_type = 'speakers'
            else:
                scene_type = 'content'
        
        output_file = output_dir / f"{video_file.stem}_vertical{video_file.suffix}"
        
        print(f"\nProcessing: {num_speakers} speakers, {scene_type.upper()} scene")
        
        if scene_type == 'content':
            # Content sharing scene
            content_config = crop_config.get('content', None)
            if not content_config:
                print("  ⚠️ No content scene configuration - skipping")
                continue
            
            # Check if content is a single crop (3 speakers) or multi-position (4-5 speakers)
            if isinstance(content_config, dict):
                # 3 speakers: Single crop (speakers on right side)
                x = content_config['x']
                y = content_config['y']
                w = content_config['width']
                h = content_config['height']
                
                print(f"  Crop: {w}x{h} at position ({x}, {y})")
                
                cmd = [
                    'ffmpeg',
                    '-i', str(video_file),
                    '-vf', f'crop={w}:{h}:{x}:{y}',
                    '-c:a', 'copy',
                    '-y',
                    str(output_file)
                ]
            else:
                # 4-5 speakers: Show 3 most active with different positions/sizes
                # Use same logic as speakers scene but with content scene positions
                print(f"  🎙️ Content scene with {num_speakers} speakers - showing 3 most active")
                
                if num_speakers <= 3 or not DYNAMIC_CONFIG['enabled']:
                    # Show first 3 positions
                    regions = content_config[:3]
                    
                    print(f"  Showing {len(regions)} speaker(s) in content layout:")
                    for i, region in enumerate(regions, 1):
                        print(f"    Speaker {i}: {region['width']}x{region['height']} at ({region['x']}, {region['y']})")
                    
                    crop_filters = []
                    for i, region in enumerate(regions):
                        x, y, w, h = region['x'], region['y'], region['width'], region['height']
                        crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                    
                    filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                else:
                    # Use transcript for speaker-aware selection
                    transcript_path = find_transcript_for_clip(video_file, base_dir)
                    
                    if transcript_path is None:
                        print("  ⚠️ No transcript - showing first 3 speakers in content layout")
                        regions = content_config[:3]
                        
                        crop_filters = []
                        for i, crop in enumerate(regions):
                            x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                            crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                        
                        filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                    else:
                        print(f"  📄 Using transcript: {transcript_path.name}")
                        
                        # Get original timestamps from clips.json
                        timestamps = get_clip_timestamps(video_file, base_dir)
                        
                        if timestamps is None:
                            # Fallback: use clip duration
                            print("  ⚠️ Using clip duration as fallback (timestamps not found)")
                            probe_cmd = [
                                'ffprobe',
                                '-v', 'error',
                                '-show_entries', 'format=duration',
                                '-of', 'csv=p=0',
                                str(video_file)
                            ]
                            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                            clip_start = 0
                            clip_end = float(probe_result.stdout.strip()) if probe_result.returncode == 0 else 60
                        else:
                            clip_start, clip_end = timestamps
                        
                        speaker_timeline = analyze_speaker_timeline(transcript_path, clip_start, clip_end)
                        
                        if not speaker_timeline:
                            print("  ⚠️ No speaker data - using first 3 in content layout")
                            regions = content_config[:3]
                            
                            crop_filters = []
                            for i, crop in enumerate(regions):
                                x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                                crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                            
                            filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                        else:
                            # Calculate speaker activity (talk time)
                            speaker_mapping = SPEAKER_MAPPING.get(num_speakers, {})
                            sorted_speakers, talk_time = calculate_speaker_activity(
                                speaker_timeline, 
                                num_speakers, 
                                speaker_mapping
                            )
                            
                            print("  📊 Speaker activity (by talk time):")
                            for i, spkr in enumerate(sorted_speakers, 1):
                                time = talk_time.get(spkr, 0)
                                print(f"     {i}. {spkr}: {time:.1f}s")
                            print("  📄 Using content scene crop positions")
                            
                            if num_speakers == 5:
                                # 5 speakers: 2×2 grid + 1 bottom
                                print("  📐 Using 2×2+1 grid layout (least active speaker at bottom)")
                                
                                # Map speakers to their crop positions
                                positions = [speaker_mapping.get(spkr, i) for i, spkr in enumerate(sorted_speakers)]
                                crops = [content_config[pos] for pos in positions[:5] if pos < len(content_config)]
                                
                                # Ensure we have all 5 crops
                                while len(crops) < 5 and len(content_config) > 0:
                                    crops.append(content_config[len(crops) % len(content_config)])
                                
                                # Build 2×2+1 grid filter
                                crop_filters = []
                                for i, crop in enumerate(crops[:5]):
                                    x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                                    crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[spk{i}]")
                                
                                # Target dimensions for 1080×1920 vertical video
                                row_height = 640  # 1920 ÷ 3 rows = 640 per row
                                half_width = 540  # 1080 ÷ 2 = 540 per speaker in top/middle rows
                                
                                # For all speakers: crop to 8:9 (narrower) from center to prevent stretching
                                # Top/middle: scale to 540×640, Bottom: scale to 1080×640
                                
                                filter_complex = (
                                    ';'.join(crop_filters) + ';' +
                                    # Top row: allow stretch to fill 540×640
                                    '[spk0]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top0];' +
                                    '[spk1]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top1];' +
                                    '[top0][top1]hstack[top];' +
                                    # Middle row: allow stretch to fill 540×640
                                    '[spk2]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid0];' +
                                    '[spk3]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid1];' +
                                    '[mid0][mid1]hstack[mid];' +
                                    # Bottom: preserve aspect, then pad to 1080×640 (no stretch)
                                    '[spk4]crop=iw*8/9:ih:(iw-iw*8/9)/2:0,scale=1080:640:force_original_aspect_ratio=decrease,pad=1080:640:(ow-iw)/2:(oh-ih)/2,setsar=1[bottom];' +
                                    '[top][mid][bottom]vstack=inputs=3[out]'
                                )
                            else:
                                # 3-4 speakers: vertical stack of top 3
                                print("  📐 Showing top 3 speakers (vertical stack)")
                                
                                # Map to content scene positions
                                positions = [speaker_mapping.get(spkr, i % len(content_config)) for i, spkr in enumerate(sorted_speakers[:3])]
                                crops = [content_config[pos] for pos in positions if pos < len(content_config)]
                                
                                # Ensure we have exactly 3 crops
                                while len(crops) < 3 and len(content_config) > 0:
                                    crops.append(content_config[len(crops) % len(content_config)])
                                
                                crop_filters = []
                                for i, crop in enumerate(crops[:3]):
                                    x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                                    crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                                
                                filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                
                cmd = [
                    'ffmpeg',
                    '-i', str(video_file),
                    '-filter_complex', filter_complex,
                    '-map', '[out]',
                    '-map', '0:a',
                    '-c:a', 'copy',
                    '-y',
                    str(output_file)
                ]
        else:  # speakers scene
            # Speakers scene - stack speakers vertically
            speaker_positions = crop_config.get('speakers', [])
            if not speaker_positions:
                print("  ⚠️ No speakers scene configuration - skipping")
                continue
            
            # For 3 speakers or when dynamic cropping is disabled: show all speakers
            if num_speakers <= 3 or not DYNAMIC_CONFIG['enabled']:
                # Show all speakers (or first 3 if more than 3)
                regions = speaker_positions[:min(num_speakers, 3)]
                
                print(f"  Showing {len(regions)} speaker(s):")
                for i, region in enumerate(regions, 1):
                    print(f"    Speaker {i}: {region['width']}x{region['height']} at ({region['x']}, {region['y']})")
                
                # Build filter: crop each region then stack vertically
                crop_filters = []
                for i, region in enumerate(regions):
                    x, y, w, h = region['x'], region['y'], region['width'], region['height']
                    crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                
                filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                
                cmd = [
                    'ffmpeg',
                    '-i', str(video_file),
                    '-filter_complex', filter_complex,
                    '-map', '[out]',
                    '-map', '0:a',
                    '-c:a', 'copy',
                    '-y',
                    str(output_file)
                ]
            else:
                # 4-5 speakers: Use speaker-aware dynamic cropping
                print(f"  🎙️ Speaker-aware mode: showing 3/{num_speakers} speakers based on conversation")
                
                # Find matching transcript
                transcript_path = find_transcript_for_clip(video_file, base_dir)
                
                if transcript_path is None:
                    print("  ⚠️ No transcript found - showing first 3 speakers")
                    # Fall back to showing first 3 speaker positions
                    regions = speaker_positions[:3]
                    
                    # Build static filter
                    crop_filters = []
                    for i, crop in enumerate(regions):
                        x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                        crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                    
                    filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                else:
                    print(f"  📄 Using transcript: {transcript_path.name}")
                    
                    # Get original timestamps from clips.json
                    timestamps = get_clip_timestamps(video_file, base_dir)
                    
                    if timestamps is None:
                        # Fallback: use clip duration
                        print("  ⚠️ Using clip duration as fallback (timestamps not found)")
                        probe_cmd = [
                            'ffprobe',
                            '-v', 'error',
                            '-show_entries', 'format=duration',
                            '-of', 'csv=p=0',
                            str(video_file)
                        ]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                        clip_start = 0
                        clip_end = float(probe_result.stdout.strip()) if probe_result.returncode == 0 else 60
                    else:
                        clip_start, clip_end = timestamps
                    
                    # Analyze speaker timeline
                    print(f"  🔍 Analyzing speakers from {clip_start:.1f}s to {clip_end:.1f}s (original video timestamps)...")
                    speaker_timeline = analyze_speaker_timeline(transcript_path, clip_start, clip_end)
                    
                    if not speaker_timeline:
                        print("  ⚠️ No speaker data found - showing first 3 speakers")
                        regions = speaker_positions[:3]
                        
                        crop_filters = []
                        for i, crop in enumerate(regions):
                            x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                            crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                        
                        filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                    else:
                        # Get speaker mapping for this configuration
                        speaker_mapping = SPEAKER_MAPPING.get(num_speakers, {})
                        
                        # Calculate speaker activity (talk time)
                        sorted_speakers, talk_time = calculate_speaker_activity(
                            speaker_timeline, 
                            num_speakers, 
                            speaker_mapping
                        )
                        
                        print("  📊 Speaker activity (by talk time):")
                        for i, spkr in enumerate(sorted_speakers, 1):
                            time = talk_time.get(spkr, 0)
                            print(f"     {i}. {spkr}: {time:.1f}s")
                        
                        if num_speakers == 5:
                            # 5 speakers: 2×2 grid + 1 bottom (least active gets covered by subtitles)
                            print("  📐 Using 2×2+1 grid layout (least active speaker at bottom)")
                            
                            # Map speakers to their crop positions
                            positions = [speaker_mapping.get(spkr, i) for i, spkr in enumerate(sorted_speakers)]
                            crops = [speaker_positions[pos] for pos in positions[:5] if pos < len(speaker_positions)]
                            
                            # Ensure we have all 5 crops
                            while len(crops) < 5 and len(speaker_positions) > 0:
                                crops.append(speaker_positions[len(crops) % len(speaker_positions)])
                            
                            # Build 2×2+1 grid filter
                            # Crop all 5 speakers
                            crop_filters = []
                            for i, crop in enumerate(crops[:5]):
                                x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                                crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[spk{i}]")
                            
                            # Target dimensions for 1080×1920 vertical video
                            row_height = 640  # 1920 ÷ 3 rows = 640 per row
                            half_width = 540  # 1080 ÷ 2 = 540 per speaker in top/middle rows
                            
                            # For all speakers: crop to 8:9 (narrower) from center to prevent stretching
                            # Top/middle: scale to 540×640, Bottom: scale to 1080×640
                            # 8:9 aspect ratio at height 640 → width = 640*(8/9) = 568.89
                            
                            filter_complex = (
                                ';'.join(crop_filters) + ';' +
                                # Top row: allow stretch to fill 540×640
                                '[spk0]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top0];' +
                                '[spk1]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top1];' +
                                '[top0][top1]hstack[top];' +
                                # Middle row: allow stretch to fill 540×640
                                '[spk2]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid0];' +
                                '[spk3]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid1];' +
                                '[mid0][mid1]hstack[mid];' +
                                # Bottom: preserve aspect, then pad to 1080×640 (no stretch)
                                '[spk4]crop=iw*8/9:ih:(iw-iw*8/9)/2:0,scale=1080:640:force_original_aspect_ratio=decrease,pad=1080:640:(ow-iw)/2:(oh-ih)/2,setsar=1[bottom];' +
                                '[top][mid][bottom]vstack=inputs=3[out]'
                            )
                        else:
                            # 3-4 speakers: vertical stack of top 3
                            print("  📐 Showing top 3 speakers (vertical stack)")
                            
                            # Map speakers to their positions
                            positions = [speaker_mapping.get(spkr, i) for i, spkr in enumerate(sorted_speakers[:3])]
                            crops = [speaker_positions[pos] for pos in positions if pos < len(speaker_positions)]
                            
                            # Ensure we have exactly 3 crops
                            while len(crops) < 3 and len(speaker_positions) > 0:
                                crops.append(speaker_positions[len(crops) % len(speaker_positions)])
                            
                            crop_filters = []
                            for i, crop in enumerate(crops[:3]):
                                x, y, w, h = crop['x'], crop['y'], crop['width'], crop['height']
                                crop_filters.append(f"[0:v]crop={w}:{h}:{x}:{y}[v{i}]")
                            
                            filter_complex = ';'.join(crop_filters) + ';' + ''.join(f"[v{i}]" for i in range(len(crop_filters))) + f"vstack=inputs={len(crop_filters)}[out]"
                
                cmd = [
                    'ffmpeg',
                    '-i', str(video_file),
                    '-filter_complex', filter_complex,
                    '-map', '[out]',
                    '-map', '0:a',
                    '-c:a', 'copy',
                    '-y',
                    str(output_file)
                ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Saved: {output_file.name}")
                successful += 1
            else:
                print("✗ FFmpeg error:")
                print(result.stderr)
                failed += 1
                
        except Exception as e:
            print(f"✗ Exception: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("\n=== Summary ===")
    print(f"Total: {len(video_files)} | ✓ Success: {successful} | ✗ Failed: {failed}")
    print(f"\nCropped videos saved to: {output_dir}")

if __name__ == "__main__":
    crop_to_vertical()
