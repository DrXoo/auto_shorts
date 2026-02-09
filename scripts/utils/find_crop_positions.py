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
        self.num_speakers = 3  # 3, 4, or 5
        self.scene_type = 'speakers'  # 'speakers' or 'content'
        self.window_name = "Crop Position Finder"
        
        # Crop positions for different configurations
        # Only x, y, and width are stored - height is auto-calculated for 16:9 aspect ratio
        # vertical=True means 9:16 (portrait), vertical=False means 16:9 (landscape)
        
        # For 3 speakers
        self.crop_3_speakers = [
            {'x': 30, 'y': 30, 'width': 1180, 'vertical': False},
            {'x': 1342, 'y': 32, 'width': 1180, 'vertical': False},
            {'x': 684, 'y': 715, 'width': 1180, 'vertical': False}
        ]
        self.crop_3_content = {'x': 1728, 'y': 0, 'width': 810, 'vertical': True}  # Portrait for content
        
        # For 4 speakers
        self.crop_4_speakers = [
            {'x': 30, 'y': 30, 'width': 1180, 'vertical': False},
            {'x': 1342, 'y': 32, 'width': 1180, 'vertical': False},
            {'x': 30, 'y': 715, 'width': 1180, 'vertical': False},
            {'x': 1342, 'y': 715, 'width': 1180, 'vertical': False}
        ]
        self.crop_4_content = [
            {'x': 1600, 'y': 0, 'width': 900, 'vertical': False},
            {'x': 1600, 'y': 480, 'width': 900, 'vertical': False},
            {'x': 1600, 'y': 960, 'width': 900, 'vertical': False},
            {'x': 1600, 'y': 960, 'width': 900, 'vertical': False}
        ]
        
        # For 5 speakers
        self.crop_5_speakers = [
            {'x': 58, 'y': 169, 'width': 778, 'vertical': False},
            {'x': 895, 'y': 160, 'width': 778, 'vertical': False},
            {'x': 1726, 'y': 160, 'width': 778, 'vertical': False},
            {'x': 436, 'y': 825, 'width': 778, 'vertical': False},
            {'x': 1271, 'y': 818, 'width': 778, 'vertical': False}
        ]
        self.crop_5_content = [
            {'x': 54, 'y': 40, 'width': 738, 'vertical': False},
            {'x': 902, 'y': 40, 'width': 738, 'vertical': False},
            {'x': 1760, 'y': 40, 'width': 738, 'vertical': False},
            {'x': 1760, 'y': 505, 'width': 738, 'vertical': False},
            {'x': 1760, 'y': 969, 'width': 738, 'vertical': False}
        ]
        
        self.selected_region = 0  # Current region being edited
    
    def calculate_height(self, width, vertical=False):
        """Calculate height based on 16:9 aspect ratio"""
        if vertical:
            # Portrait: 9:16 ratio (width:height)
            return int(width * 16 / 9)
        else:
            # Landscape: 16:9 ratio (width:height)
            return int(width * 9 / 16)
    
    def get_crop_with_dimensions(self, crop):
        """Get crop dict with calculated height"""
        return {
            'x': crop['x'],
            'y': crop['y'],
            'width': crop['width'],
            'height': self.calculate_height(crop['width'], crop.get('vertical', False))
        }
        
    def get_current_crops(self):
        """Get the current crop configuration based on speaker count and scene type"""
        if self.num_speakers == 3:
            if self.scene_type == 'speakers':
                return self.crop_3_speakers
            else:
                return [self.crop_3_content]  # Wrap in list for consistent handling
        elif self.num_speakers == 4:
            return self.crop_4_speakers if self.scene_type == 'speakers' else self.crop_4_content
        else:  # 5 speakers
            return self.crop_5_speakers if self.scene_type == 'speakers' else self.crop_5_content
    
    def set_crop_position(self, region_idx, x, y):
        """Set the position for a specific crop region"""
        if self.num_speakers == 3:
            if self.scene_type == 'speakers':
                self.crop_3_speakers[region_idx]['x'] = x
                self.crop_3_speakers[region_idx]['y'] = y
            else:
                self.crop_3_content['x'] = x
                self.crop_3_content['y'] = y
        elif self.num_speakers == 4:
            if self.scene_type == 'speakers':
                self.crop_4_speakers[region_idx]['x'] = x
                self.crop_4_speakers[region_idx]['y'] = y
            else:
                self.crop_4_content[region_idx]['x'] = x
                self.crop_4_content[region_idx]['y'] = y
        else:  # 5 speakers
            if self.scene_type == 'speakers':
                self.crop_5_speakers[region_idx]['x'] = x
                self.crop_5_speakers[region_idx]['y'] = y
            else:
                self.crop_5_content[region_idx]['x'] = x
                self.crop_5_content[region_idx]['y'] = y
    
    def mouse_callback(self, event, x, y, flags, param):
        """Track mouse position and clicks"""
        self.mouse_x = x
        self.mouse_y = y
        
        if event == cv2.EVENT_LBUTTONDOWN:
            crops = self.get_current_crops()
            if self.num_speakers == 3 and self.scene_type == 'content':
                # Single crop for 3-speaker content
                self.set_crop_position(0, x, y)
                print(f"\n✓ 3-Speaker Content crop position updated: x={x}, y={y}")
            else:
                # Multi-region crop
                self.set_crop_position(self.selected_region, x, y)
                print(f"\n✓ {self.num_speakers}-Speaker {self.scene_type} - Region {self.selected_region + 1} position updated: x={x}, y={y}")
        
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
        
        crops = self.get_current_crops()
        
        # Special case: 3 speakers content scene (single crop)
        if self.num_speakers == 3 and self.scene_type == 'content':
            crop = self.get_crop_with_dimensions(crops[0])
            x, y = crop['x'], crop['y']
            w, h = crop['width'], crop['height']
            is_vertical = crops[0].get('vertical', False)
            
            # Draw semi-transparent overlay
            overlay = display.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), -1)
            cv2.addWeighted(overlay, 0.2, display, 0.8, 0, display)
            
            # Draw border
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 3)
            
            # Add label
            ratio_text = "9:16" if is_vertical else "16:9"
            cv2.putText(display, f"Content: {w}x{h} ({ratio_text})", 
                       (x, y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(display, f"Position: ({x}, {y})", 
                       (x, y - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        else:
            # Draw multiple crop areas
            for i, region in enumerate(crops):
                region_with_dims = self.get_crop_with_dimensions(region)
                x, y = region_with_dims['x'], region_with_dims['y']
                w, h = region_with_dims['width'], region_with_dims['height']
                is_vertical = region.get('vertical', False)
                
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
                ratio_text = "9:16" if is_vertical else "16:9"
                label = f"Pos {i+1}: {w}x{h} ({ratio_text})"
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
            "N = Change # of speakers",
            "S/C = Scene (Speakers/Content)",
            "1-5 = Select position",
            "V = Toggle vertical/horizontal",
            "+/- = Adjust width",
            "Left Click = Set position",
            "Right Click = Pixel color",
            "P = Print config",
            "Q = Quit"
        ]
        
        y_offset = 70
        for instruction in instructions:
            cv2.putText(display, instruction, 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            y_offset += 25
        
        mode_text = f"{self.num_speakers} SPEAKERS - {self.scene_type.upper()} SCENE"
        crops = self.get_current_crops()
        if not (self.num_speakers == 3 and self.scene_type == 'content'):
            mode_text += f" - Position {self.selected_region + 1}/{len(crops)}"
        cv2.putText(display, mode_text, 
                   (10, display.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        return display
    
    def print_config(self):
        """Print the current configuration in Python format"""
        print("\n" + "="*70)
        print("COPY THIS TO YOUR 3_crop_to_vertical.py FILE:")
        print("="*70)
        
        if self.num_speakers == 3:
            print("\n# 3 SPEAKERS (height auto-calculated for 16:9)")
            print("CROP_POSITIONS_3 = {")
            print("    'speakers': [")
            for i, region in enumerate(self.crop_3_speakers):
                region_with_dims = self.get_crop_with_dimensions(region)
                ratio = "9:16" if region.get('vertical', False) else "16:9"
                print(f"        {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region_with_dims['height']}}},  # {ratio}")
            print("    ],")
            print("    'content': {")
            content_with_dims = self.get_crop_with_dimensions(self.crop_3_content)
            ratio = "9:16" if self.crop_3_content.get('vertical', False) else "16:9"
            print(f"        'x': {self.crop_3_content['x']},")
            print(f"        'y': {self.crop_3_content['y']},")
            print(f"        'width': {self.crop_3_content['width']},")
            print(f"        'height': {content_with_dims['height']}  # {ratio}")
            print("    }")
            print("}")
        
        elif self.num_speakers == 4:
            print("\n# 4 SPEAKERS (height auto-calculated for 16:9)")
            print("CROP_POSITIONS_4 = {")
            print("    'speakers': [")
            for region in self.crop_4_speakers:
                region_with_dims = self.get_crop_with_dimensions(region)
                ratio = "9:16" if region.get('vertical', False) else "16:9"
                print(f"        {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region_with_dims['height']}}},  # {ratio}")
            print("    ],")
            print("    'content': [")
            for region in self.crop_4_content:
                region_with_dims = self.get_crop_with_dimensions(region)
                ratio = "9:16" if region.get('vertical', False) else "16:9"
                print(f"        {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region_with_dims['height']}}},  # {ratio}")
            print("    ]")
            print("}")
        
        else:  # 5 speakers
            print("\n# 5 SPEAKERS (height auto-calculated for 16:9)")
            print("CROP_POSITIONS_5 = {")
            print("    'speakers': [")
            for region in self.crop_5_speakers:
                region_with_dims = self.get_crop_with_dimensions(region)
                ratio = "9:16" if region.get('vertical', False) else "16:9"
                print(f"        {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region_with_dims['height']}}},  # {ratio}")
            print("    ],")
            print("    'content': [")
            for region in self.crop_5_content:
                region_with_dims = self.get_crop_with_dimensions(region)
                ratio = "9:16" if region.get('vertical', False) else "16:9"
                print(f"        {{'x': {region['x']}, 'y': {region['y']}, 'width': {region['width']}, 'height': {region_with_dims['height']}}},  # {ratio}")
            print("    ]")
            print("}")
        
        print("="*70 + "\n")
    
    def run(self):
        """Run the interactive position finder"""
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)
        
        print("\n" + "="*70)
        print("CROP POSITION FINDER")
        print("="*70)
        print(f"\nCurrent: {self.num_speakers} speakers, {self.scene_type} scene")
        print("\nControls:")
        print("  N = Change number of speakers (3/4/5)")
        print("  S = Switch to Speakers scene")
        print("  C = Switch to Content scene")
        print("  1-5 = Select position to edit")
        print("  V = Toggle vertical/horizontal aspect ratio")
        print("  + = Increase width by 10")
        print("  - = Decrease width by 10")
        print("  Left Click = Set position for selected crop")
        print("  Right Click = Show pixel color (for auto-detection)")
        print("  P = Print configuration to copy")
        print("  Q = Quit")
        print("\nMove your mouse to see coordinates, click to set position!")
        print("Height is auto-calculated to maintain 16:9 aspect ratio!")
        print("="*70 + "\n")
        
        while True:
            display = self.draw_overlay()
            cv2.imshow(self.window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                break
            elif key == ord('n'):  # Change number of speakers
                print("\nSelect number of speakers:")
                print("  3 = 3 speakers")
                print("  4 = 4 speakers")  
                print("  5 = 5 speakers")
                num_key = cv2.waitKey(0) & 0xFF
                if num_key == ord('3'):
                    self.num_speakers = 3
                    self.selected_region = 0
                    print(f"\n→ Switched to 3 speakers")
                elif num_key == ord('4'):
                    self.num_speakers = 4
                    self.selected_region = 0
                    print(f"\n→ Switched to 4 speakers")
                elif num_key == ord('5'):
                    self.num_speakers = 5
                    self.selected_region = 0
                    print(f"\n→ Switched to 5 speakers")
            elif key == ord('s'):  # Speakers scene
                self.scene_type = 'speakers'
                self.selected_region = 0
                print(f"\n→ Switched to SPEAKERS scene")
            elif key == ord('c'):  # Content scene
                self.scene_type = 'content'
                self.selected_region = 0
                print(f"\n→ Switched to CONTENT scene")
            elif key == ord('1'):
                self.selected_region = 0
                print(f"\n→ Selected Position 1")
            elif key == ord('2'):
                crops = self.get_current_crops()
                if len(crops) > 1:
                    self.selected_region = 1
                    print(f"\n→ Selected Position 2")
            elif key == ord('3'):
                crops = self.get_current_crops()
                if len(crops) > 2:
                    self.selected_region = 2
                    print(f"\n→ Selected Position 3")
            elif key == ord('4'):
                crops = self.get_current_crops()
                if len(crops) > 3:
                    self.selected_region = 3
                    print(f"\n→ Selected Position 4")
            elif key == ord('5'):
                crops = self.get_current_crops()
                if len(crops) > 4:
                    self.selected_region = 4
                    print(f"\n→ Selected Position 5")
            elif key == ord('v'):  # Toggle vertical/horizontal
                crops = self.get_current_crops()
                if self.num_speakers == 3 and self.scene_type == 'content':
                    self.crop_3_content['vertical'] = not self.crop_3_content.get('vertical', False)
                    ratio = "9:16" if self.crop_3_content['vertical'] else "16:9"
                    print(f"\n→ Toggled to {ratio} aspect ratio")
                else:
                    current_crop = crops[self.selected_region]
                    current_crop['vertical'] = not current_crop.get('vertical', False)
                    ratio = "9:16" if current_crop['vertical'] else "16:9"
                    print(f"\n→ Position {self.selected_region + 1} toggled to {ratio}")
            elif key == ord('+') or key == ord('='):  # Increase width
                crops = self.get_current_crops()
                if self.num_speakers == 3 and self.scene_type == 'content':
                    self.crop_3_content['width'] += 10
                    new_height = self.calculate_height(self.crop_3_content['width'], self.crop_3_content.get('vertical', False))
                    print(f"\n→ Width increased to {self.crop_3_content['width']} (height: {new_height})")
                else:
                    current_crop = crops[self.selected_region]
                    current_crop['width'] += 10
                    new_height = self.calculate_height(current_crop['width'], current_crop.get('vertical', False))
                    print(f"\n→ Position {self.selected_region + 1} width: {current_crop['width']} (height: {new_height})")
            elif key == ord('-') or key == ord('_'):  # Decrease width
                crops = self.get_current_crops()
                if self.num_speakers == 3 and self.scene_type == 'content':
                    self.crop_3_content['width'] = max(10, self.crop_3_content['width'] - 10)
                    new_height = self.calculate_height(self.crop_3_content['width'], self.crop_3_content.get('vertical', False))
                    print(f"\n→ Width decreased to {self.crop_3_content['width']} (height: {new_height})")
                else:
                    current_crop = crops[self.selected_region]
                    current_crop['width'] = max(10, current_crop['width'] - 10)
                    new_height = self.calculate_height(current_crop['width'], current_crop.get('vertical', False))
                    print(f"\n→ Position {self.selected_region + 1} width: {current_crop['width']} (height: {new_height})")
            elif key == ord('p'):  # Print config
                self.print_config()
        
        cv2.destroyAllWindows()
        self.print_config()

def main():
    # Get video file
    base_dir = Path(__file__).parent.parent.parent
    extracted_dir = base_dir / "output" / "extracted"
    
    # Also check input folder as fallback
    input_dir = base_dir / "input"
    
    video_files = list(extracted_dir.glob("*.mp4"))
    if not video_files:
        video_files = list(input_dir.glob("*.mp4"))
        if not video_files:
            print("No video files found!")
            print(f"Checked: {extracted_dir}")
            print(f"Checked: {input_dir}")
            return
        else:
            print(f"Using videos from: {input_dir}")
    else:
        print(f"Using videos from: {extracted_dir}")
    
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
