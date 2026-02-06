import cv2
import numpy as np
import subprocess
from pathlib import Path

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

class CropPositionFinder:
    def __init__(self, image):
        self.image = image.copy()
        self.original = image.copy()
        self.mouse_x = 0
        self.mouse_y = 0
        self.crop_x = 0
        self.crop_y = 0
        self.mode = 'single'  # 'single' or 'triple'
        self.window_name = "Crop Position Finder"
        
        # Current crop settings
        self.single_crop = {'x': 0, 'y': 0, 'width': 810, 'height': 1440}
        self.triple_crop = [
            {'x': 100, 'y': 50, 'width': 810, 'height': 480},
            {'x': 1500, 'y': 50, 'width': 810, 'height': 480},
            {'x': 800, 'y': 700, 'width': 810, 'height': 480}
        ]
        self.selected_region = 0  # For triple mode (0, 1, or 2)
        
    def mouse_callback(self, event, x, y, flags, param):
        """Track mouse position and clicks"""
        self.mouse_x = x
        self.mouse_y = y
        
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.mode == 'single':
                self.single_crop['x'] = x
                self.single_crop['y'] = y
                print(f"\n✓ Single crop position updated: x={x}, y={y}")
            else:
                self.triple_crop[self.selected_region]['x'] = x
                self.triple_crop[self.selected_region]['y'] = y
                print(f"\n✓ Region {self.selected_region + 1} position updated: x={x}, y={y}")
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Right click shows pixel color for auto-detection
            if 0 <= y < self.original.shape[0] and 0 <= x < self.original.shape[1]:
                bgr = self.original[y, x]
                print(f"\n📍 Reference Pixel at ({x}, {y}):")
                print(f"   BGR: ({bgr[0]}, {bgr[1]}, {bgr[2]})")
                print("   Use this for auto-detection in crop_to_vertical.py!")
    
    def draw_overlay(self):
        """Draw crop areas on the image"""
        display = self.original.copy()
        
        if self.mode == 'single':
            # Draw single crop area
            x, y = self.single_crop['x'], self.single_crop['y']
            w, h = self.single_crop['width'], self.single_crop['height']
            
            # Draw semi-transparent overlay
            overlay = display.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
            
            # Draw border
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 3)
            
            # Add label
            cv2.putText(display, f"Single Crop: {w}x{h}", 
                       (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display, f"Position: ({x}, {y})", 
                       (x, y - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            # Draw triple crop areas
            for i, region in enumerate(self.triple_crop):
                x, y = region['x'], region['y']
                w, h = region['width'], region['height']
                
                # Use different color for selected region
                if i == self.selected_region:
                    color = (0, 255, 0)  # Green for selected
                    thickness = 3
                else:
                    color = (255, 150, 0)  # Blue for others
                    thickness = 2
                
                # Draw semi-transparent overlay
                overlay = display.copy()
                cv2.rectangle(overlay, (x, y), (x + w, y + h), color, -1)
                cv2.addWeighted(overlay, 0.15, display, 0.85, 0, display)
                
                # Draw border
                cv2.rectangle(display, (x, y), (x + w, y + h), color, thickness)
                
                # Add label
                label = f"Region {i+1}: {w}x{h}"
                if i == self.selected_region:
                    label += " [ACTIVE]"
                cv2.putText(display, label, 
                           (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(display, f"({x}, {y})", 
                           (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Draw mouse crosshair
        cv2.line(display, (self.mouse_x, 0), (self.mouse_x, display.shape[0]), (0, 255, 255), 1)
        cv2.line(display, (0, self.mouse_y), (display.shape[1], self.mouse_y), (0, 255, 255), 1)
        
        # Draw mouse coordinates
        coord_text = f"Mouse: ({self.mouse_x}, {self.mouse_y})"
        cv2.putText(display, coord_text, 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Draw instructions
        instructions = [
            "CONTROLS:",
            "M = Toggle mode (Single/Triple)",
            "1,2,3 = Select region (Triple mode)",
            "Left Click = Set position",
            "Right Click = Show pixel color",
            "C = Copy config to clipboard",
            "Q = Quit"
        ]
        
        y_offset = 70
        for instruction in instructions:
            cv2.putText(display, instruction, 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset += 25
        
        mode_text = f"MODE: {self.mode.upper()}"
        if self.mode == 'triple':
            mode_text += f" - Region {self.selected_region + 1} selected"
        cv2.putText(display, mode_text, 
                   (10, display.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        return display
    
    def print_config(self):
        """Print the current configuration in Python format"""
        print("\n" + "=" * 60)
        print("COPY THIS TO YOUR crop_to_vertical.py FILE:")
        print("=" * 60)
        print("\n# Mode 1: Single crop")
        print("SINGLE_CROP = {")
        print(f"    'x': {self.single_crop['x']},")
        print(f"    'y': {self.single_crop['y']},")
        print(f"    'width': {self.single_crop['width']},")
        print(f"    'height': {self.single_crop['height']}")
        print("}")
        print("\n# Mode 2: Triple crop")
        print("TRIPLE_CROP = [")
        for i, region in enumerate(self.triple_crop):
            print(f"    # Speaker {i+1}")
            print(f"    {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region['height']}}},")
        print("]")
        print("=" * 60 + "\n")
    
    def run(self):
        """Run the interactive position finder"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("\n" + "=" * 60)
        print("CROP POSITION FINDER")
        print("=" * 60)
        print("\nControls:")
        print("  M = Toggle between Single/Triple mode")
        print("  1/2/3 = Select region 1/2/3 (in Triple mode)")
        print("  Left Click = Set position for current crop/region")
        print("  Right Click = Show pixel color (for auto-detection)")
        print("  C = Print config to copy")
        print("  Q = Quit")
        print("\nMove your mouse to see coordinates, click to set position!")
        print("=" * 60 + "\n")
        
        while True:
            display = self.draw_overlay()
            cv2.imshow(self.window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord('m'):  # Toggle mode
                self.mode = 'triple' if self.mode == 'single' else 'single'
                print(f"\n→ Switched to {self.mode.upper()} mode")
            elif key == ord('1') and self.mode == 'triple':
                self.selected_region = 0
                print("\n→ Selected Region 1")
            elif key == ord('2') and self.mode == 'triple':
                self.selected_region = 1
                print("\n→ Selected Region 2")
            elif key == ord('3') and self.mode == 'triple':
                self.selected_region = 2
                print("\n→ Selected Region 3")
            elif key == ord('c'):  # Print config
                self.print_config()
        
        cv2.destroyAllWindows()
        self.print_config()

def main():
    # Get video file
    base_dir = Path(__file__).parent.parent
    candidates_dir = base_dir / "output" / "candidates"
    
    video_files = list(candidates_dir.glob("*.mp4"))
    
    if not video_files:
        print("No video files found in candidates folder!")
        print(f"Looking in: {candidates_dir}")
        return
    
    print("\nAvailable videos:")
    for i, video in enumerate(video_files, 1):
        print(f"  {i}. {video.name}")
    
    choice = input(f"\nSelect video (1-{len(video_files)}): ").strip()
    
    try:
        video_idx = int(choice) - 1
        video_file = video_files[video_idx]
    except (ValueError, IndexError):
        print("Invalid choice!")
        return
    
    print(f"\nExtracting frame from: {video_file.name}")
    frame = extract_frame(video_file, time_sec=5)
    
    if frame is None:
        print("Failed to extract frame!")
        return
    
    print(f"Frame size: {frame.shape[1]}x{frame.shape[0]}")
    
    # Run the position finder
    finder = CropPositionFinder(frame)
    finder.run()

if __name__ == "__main__":
    main()
