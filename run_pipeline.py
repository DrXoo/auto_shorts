"""
AutoShorts Pipeline Orchestrator
=================================
Runs the complete pipeline from video to final shorts with subtitles.

Pipeline Steps:
1. Transcribe video with speaker diarization
2. Wait for AI analysis (clips.json)
3. Extract clips from video
4. Crop to vertical format (9:16)
5. Add karaoke subtitles
6. Final shorts ready for upload

Usage:
    python run_pipeline.py                    # Run full pipeline
    python run_pipeline.py --from-step 3      # Resume from step 3
    python run_pipeline.py --skip-transcribe  # Skip transcription
"""

import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json

# Paths
SCRIPT_DIR = Path(__file__).parent
SCRIPTS_DIR = SCRIPT_DIR / "scripts"
STEPS_DIR = SCRIPTS_DIR / "steps"
INPUT_DIR = SCRIPT_DIR / "input"
OUTPUT_DIR = SCRIPT_DIR / "output"
AI_ANALYSIS_DIR = OUTPUT_DIR / "ai_analysis"
EXTRACTED_DIR = OUTPUT_DIR / "extracted"
CROPPED_DIR = OUTPUT_DIR / "cropped"
FINAL_DIR = OUTPUT_DIR / "final"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"

# Required files
CLIPS_JSON = AI_ANALYSIS_DIR / "clips.json"

def get_video_file():
    """Find the first video file in the input directory"""
    VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']
    video_files = [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]
    return video_files[0] if video_files else None

def get_transcript_file():
    """Find the first transcript JSON file in the transcripts directory"""
    transcript_files = [f for f in TRANSCRIPTS_DIR.glob("*_transcript.json") if f.is_file()]
    return transcript_files[0] if transcript_files else None

# Pipeline state file
STATE_FILE = OUTPUT_DIR / "pipeline_state.json"

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_header(text):
    """Print a fancy header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")

def print_step(step_num, title):
    """Print step header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[Step {step_num}] {title}{Colors.END}")
    print(f"{Colors.BLUE}{'-'*70}{Colors.END}")

def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")

def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")

def print_warning(message):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")

def print_info(message):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {message}{Colors.END}")

def load_state():
    """Load pipeline state from file"""
    if STATE_FILE.exists():
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"completed_steps": [], "last_run": None}

def save_state(state):
    """Save pipeline state to file"""
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def run_script(script_name, description):
    """Run a Python script and return success status"""
    script_path = STEPS_DIR / script_name
    
    print_info(f"Running: {script_name}")
    print_info(f"Command: python {script_path}")
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=SCRIPT_DIR,
            check=False
        )
        
        if result.returncode == 0:
            print_success(f"{description} completed successfully")
            return True
        else:
            print_error(f"{description} failed with exit code {result.returncode}")
            return False
    except Exception as e:
        print_error(f"Exception running {script_name}: {e}")
        return False

def wait_for_clips_json(timeout_minutes=None):
    """Wait for clips.json to appear in ai_analysis folder"""
    print_info("Waiting for AI analysis to complete...")
    print_info(f"Looking for: {CLIPS_JSON}")
    print()
    
    if CLIPS_JSON.exists():
        print_success("clips.json already exists!")
        return True
    
    print_warning("clips.json not found")
    print()
    print(f"{Colors.YELLOW}Please run your external AI analysis and save clips.json to:{Colors.END}")
    print(f"  {Colors.BOLD}{AI_ANALYSIS_DIR}{Colors.END}")
    print()
    print(f"{Colors.CYAN}Options:{Colors.END}")
    print("  1. Press ENTER to check again")
    print("  2. Type 'skip' to skip to next available step")
    print("  3. Type 'quit' to exit")
    print()
    
    start_time = time.time()
    check_interval = 5  # seconds
    
    while True:
        # Check if file appeared
        if CLIPS_JSON.exists():
            print_success("clips.json detected!")
            return True
        
        # Check timeout
        if timeout_minutes:
            elapsed = (time.time() - start_time) / 60
            if elapsed > timeout_minutes:
                print_error(f"Timeout after {timeout_minutes} minutes")
                return False
        
        # Wait for user input
        try:
            user_input = input(f"{Colors.CYAN}> {Colors.END}").strip().lower()
            
            if user_input == 'quit':
                print_info("Exiting pipeline")
                return False
            elif user_input == 'skip':
                print_warning("Skipping clip extraction step")
                return False
            elif user_input == '' or user_input == '1':
                print_info("Checking for clips.json...")
                if CLIPS_JSON.exists():
                    print_success("clips.json found!")
                    return True
                else:
                    print_warning("Still not found. Press ENTER to check again.")
            else:
                print_warning("Invalid input. Press ENTER, 'skip', or 'quit'")
        except KeyboardInterrupt:
            print()
            print_info("Pipeline interrupted by user")
            return False

def check_prerequisites(step_num):
    """Check if prerequisites for a step are met"""
    if step_num >= 1:
        # Need video file
        VIDEO_FILE = get_video_file()
        if not VIDEO_FILE:
            print_error(f"No video file found in {INPUT_DIR}")
            print_info(f"Please add a video file to the input directory")
            return False
        print_info(f"Using video: {VIDEO_FILE.name}")
    
    if step_num >= 3:
        # Need clips.json
        if not CLIPS_JSON.exists():
            print_error(f"clips.json not found: {CLIPS_JSON}")
            print_info("Run steps 1-2 first, or provide clips.json manually")
            return False
        
        # Need transcript
        TRANSCRIPT_JSON = get_transcript_file()
        if not TRANSCRIPT_JSON:
            print_error(f"No transcript found in {TRANSCRIPTS_DIR}")
            print_info("Run step 1 first")
            return False
        print_info(f"Using transcript: {TRANSCRIPT_JSON.name}")
    
    if step_num >= 4:
        # Need extracted clips
        extracted_files = list(EXTRACTED_DIR.glob("*.mp4"))
        if not extracted_files:
            print_error(f"No extracted clips found in {EXTRACTED_DIR}")
            print_info("Run step 3 first")
            return False
    
    if step_num >= 5:
        # Need cropped clips
        cropped_files = list(CROPPED_DIR.glob("*.mp4"))
        if not cropped_files:
            print_error(f"No cropped clips found in {CROPPED_DIR}")
            print_info("Run step 4 first")
            return False
    
    return True

def run_pipeline(start_step=1, skip_transcribe=False):
    """Run the complete pipeline"""
    
    print_header("🎬 AutoShorts Pipeline 🎬")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Create output directories
    for dir_path in [AI_ANALYSIS_DIR, EXTRACTED_DIR, CROPPED_DIR, FINAL_DIR, TRANSCRIPTS_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Load state
    state = load_state()
    
    # Define pipeline steps
    steps = [
        {
            "num": 1,
            "title": "Transcribe Video with Speaker Diarization",
            "script": "1_transcribe.py",
            "description": "Transcription"
        },
        {
            "num": 2,
            "title": "AI Analysis (External - Wait for clips.json)",
            "script": None,  # External step
            "description": "AI Analysis"
        },
        {
            "num": 3,
            "title": "Extract Clips from Video",
            "script": "2_extract_clips.py",
            "description": "Clip extraction"
        },
        {
            "num": 4,
            "title": "Crop to Vertical Format (9:16)",
            "script": "3_crop_to_vertical.py",
            "description": "Cropping"
        },
        {
            "num": 5,
            "title": "Add Karaoke Subtitles",
            "script": "4_add_subtitles.py",
            "description": "Subtitle generation"
        }
    ]
    
    # Filter steps based on start_step
    steps_to_run = [s for s in steps if s["num"] >= start_step]
    
    # Skip transcription if requested
    if skip_transcribe and start_step == 1:
        steps_to_run = [s for s in steps_to_run if s["num"] != 1]
    
    # Run pipeline
    for step in steps_to_run:
        step_num = step["num"]
        
        # Skip if already completed
        if step_num in state["completed_steps"]:
            print_step(step_num, step["title"])
            print_warning("Already completed - skipping")
            continue
        
        print_step(step_num, step["title"])
        
        # Check prerequisites
        if not check_prerequisites(step_num):
            print_error("Prerequisites not met. Pipeline stopped.")
            return False
        
        # Run step
        if step["script"]:
            # Python script step
            success = run_script(step["script"], step["description"])
            
            if not success:
                print_error(f"Step {step_num} failed. Pipeline stopped.")
                print_info(f"To resume, run: python run_pipeline.py --from-step {step_num}")
                save_state(state)
                return False
            
            # Mark as completed
            state["completed_steps"].append(step_num)
            save_state(state)
        else:
            # External step (AI analysis)
            success = wait_for_clips_json()
            
            if not success:
                print_error("AI analysis step failed or skipped. Pipeline stopped.")
                print_info(f"To resume, run: python run_pipeline.py --from-step {step_num + 1}")
                save_state(state)
                return False
            
            # Mark as completed
            state["completed_steps"].append(step_num)
            save_state(state)
    
    # Pipeline complete!
    print_header("🎉 Pipeline Complete! 🎉")
    
    # Show summary
    final_files = list(FINAL_DIR.glob("*.mp4"))
    if final_files:
        print_success(f"Generated {len(final_files)} final video(s)")
        print(f"\n{Colors.BOLD}Final videos location:{Colors.END}")
        print(f"  {Colors.GREEN}{FINAL_DIR}{Colors.END}")
        print()
        print(f"{Colors.BOLD}Files:{Colors.END}")
        for f in final_files:
            print(f"  • {f.name}")
        print()
        print(f"{Colors.GREEN}✓ Ready to upload to Instagram/TikTok/YouTube Shorts!{Colors.END}")
    
    # Reset state for next run
    state["completed_steps"] = []
    save_state(state)
    
    return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AutoShorts Pipeline Orchestrator")
    parser.add_argument("--from-step", type=int, default=1, 
                        help="Start from specific step (1-5)")
    parser.add_argument("--skip-transcribe", action="store_true",
                        help="Skip transcription step")
    parser.add_argument("--reset", action="store_true",
                        help="Reset pipeline state")
    
    args = parser.parse_args()
    
    # Reset state if requested
    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print_success("Pipeline state reset")
        return
    
    # Validate step number
    if args.from_step < 1 or args.from_step > 5:
        print_error("Step number must be between 1 and 5")
        return
    
    # Run pipeline
    try:
        success = run_pipeline(start_step=args.from_step, skip_transcribe=args.skip_transcribe)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print_warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
