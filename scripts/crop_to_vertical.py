import subprocess
from pathlib import Path
import numpy as np

# ============= CROP CONFIGURATION =============
# Adjust these values to match your podcast camera setup

# Mode 1: Single crop (content sharing scene - speakers on right)
SINGLE_CROP = {
    'x': 1728,      # Horizontal position (0 = left edge)
    'y': 0,      # Vertical position (0 = top edge)
    'width': 810,
    'height': 1440
}

# Mode 2: Triple crop (triangle speaker layout)
# Each speaker gets a 810x480 region that will be stacked vertically
TRIPLE_CROP = [
    # Speaker 1 (top in final video)
    {'x': 30, 'y': 30, 'width': 1180, 'height': 685},
    # Speaker 2 (middle in final video)
    {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},
    # Speaker 3 (bottom in final video)
    {'x': 684, 'y': 715, 'width': 1180, 'height': 685}
]

# ============= AUTO-DETECTION CONFIGURATION =============
# Define a reference pixel that differs between the two scene types
# Use find_crop_positions.py (right-click) to find good reference pixels

AUTO_DETECT = {
    'enabled': True,  # Set to False to manually choose mode for each video
    'pixel_position': (82, 1156),  # (x, y) coordinate to check
    
    # Define color ranges for each mode (BGR format)
    # If pixel color is closer to single_color, use single mode
    # If pixel color is closer to triple_color, use triple mode
    'single_color': (0, 216, 217),     # Example: dark area in content sharing scene
    'triple_color': (0, 0, 0),  # Example: bright area in triangle scene
    
    # Maximum color distance to consider a match (increase if detection fails)
    'tolerance': 100
}
# ===============================================

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

def detect_crop_mode(video_file):
    """Automatically detect which crop mode to use based on pixel color"""
    if not AUTO_DETECT['enabled']:
        return None  # Manual mode
    
    # Extract a frame
    frame = extract_frame(video_file, time_sec=5)
    if frame is None:
        print("  ⚠ Could not extract frame for auto-detection")
        return None
    
    # Get pixel color at reference position
    x, y = AUTO_DETECT['pixel_position']
    if y >= frame.shape[0] or x >= frame.shape[1]:
        print(f"  ⚠ Reference pixel position ({x}, {y}) is out of bounds")
        return None
    
    pixel_color = frame[y, x]
    
    # Calculate color distance to each mode's reference color
    single_color = np.array(AUTO_DETECT['single_color'])
    triple_color = np.array(AUTO_DETECT['triple_color'])
    
    dist_single = np.linalg.norm(pixel_color - single_color)
    dist_triple = np.linalg.norm(pixel_color - triple_color)
    
    # Determine which mode is closer
    if dist_single < dist_triple and dist_single < AUTO_DETECT['tolerance']:
        detected_mode = 'single'
    elif dist_triple < dist_single and dist_triple < AUTO_DETECT['tolerance']:
        detected_mode = 'triple'
    else:
        print(f"  ⚠ Pixel color {tuple(pixel_color)} doesn't match either mode")
        print(f"     Distance to single: {dist_single:.1f}, Distance to triple: {dist_triple:.1f}")
        return None
    
    print(f"  🎯 Auto-detected: {detected_mode.upper()} mode")
    print(f"     Pixel at ({x}, {y}) = {tuple(pixel_color)}")
    
    return detected_mode

def crop_to_vertical():
    """
    Crop videos from candidates folder to 9:16 aspect ratio for TikTok/Instagram/YouTube Shorts.
    Original resolution: 2560x1440
    Target resolution: 810x1440 (9:16 aspect ratio)
    """
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    candidates_dir = base_dir / "output" / "candidates"
    output_dir = base_dir / "output" / "ready_for_subs"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all video files from candidates folder
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv']
    video_files = [f for f in candidates_dir.iterdir() 
                   if f.is_file() and f.suffix.lower() in video_extensions]
    
    if not video_files:
        print(f"No video files found in {candidates_dir}")
        return
    
    print(f"Found {len(video_files)} video(s) to process\n")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for idx, video_file in enumerate(video_files, 1):
        print(f"\n[{idx}/{len(video_files)}] {video_file.name}")
        
        # Try auto-detection first
        crop_mode = detect_crop_mode(video_file)
        
        if crop_mode is None:
            # Manual mode selection
            print("\nCrop mode:")
            print("  1 = Single crop (content sharing scene)")
            print("  2 = Triple crop (triangle speaker layout)")
            print("  Q = Skip this video")
            
            mode_choice = input("\nYour choice (1/2/Q): ").strip().lower()
            
            if mode_choice == 'q':
                print("⊗ Skipped\n")
                continue
            elif mode_choice == '2':
                crop_mode = 'triple'
            else:
                crop_mode = 'single'
        
        output_file = output_dir / f"{video_file.stem}_vertical{video_file.suffix}"
        
        print(f"\nProcessing with {crop_mode} mode...")
        
        if crop_mode == 'single':
            # Single crop using predefined coordinates
            x = SINGLE_CROP['x']
            y = SINGLE_CROP['y']
            w = SINGLE_CROP['width']
            h = SINGLE_CROP['height']
            
            print(f"Crop: {w}x{h} at position ({x}, {y})")
            
            cmd = [
                'ffmpeg',
                '-i', str(video_file),
                '-vf', f'crop={w}:{h}:{x}:{y}',
                '-c:a', 'copy',
                '-y',
                str(output_file)
            ]
        else:
            # Triple crop mode - stack vertically using predefined coordinates
            regions = TRIPLE_CROP
            
            print("Crop regions:")
            print(f"  Region 1: {regions[0]['width']}x{regions[0]['height']} at ({regions[0]['x']}, {regions[0]['y']})")
            print(f"  Region 2: {regions[1]['width']}x{regions[1]['height']} at ({regions[1]['x']}, {regions[1]['y']})")
            print(f"  Region 3: {regions[2]['width']}x{regions[2]['height']} at ({regions[2]['x']}, {regions[2]['y']})")
            
            # Build complex filter: crop each region then stack vertically
            x1, y1, w1, h1 = regions[0]['x'], regions[0]['y'], regions[0]['width'], regions[0]['height']
            x2, y2, w2, h2 = regions[1]['x'], regions[1]['y'], regions[1]['width'], regions[1]['height']
            x3, y3, w3, h3 = regions[2]['x'], regions[2]['y'], regions[2]['width'], regions[2]['height']
            
            filter_complex = (
                f"[0:v]crop={w1}:{h1}:{x1}:{y1}[v1];"
                f"[0:v]crop={w2}:{h2}:{x2}:{y2}[v2];"
                f"[0:v]crop={w3}:{h3}:{x3}:{y3}[v3];"
                f"[v1][v2][v3]vstack=inputs=3[out]"
            )
            
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
                print(f"{result.stderr[:300]}")
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
