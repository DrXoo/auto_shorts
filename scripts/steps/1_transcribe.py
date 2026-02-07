import torch
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fix for PyTorch 2.8 compatibility with pyannote models
# Monkey-patch torch.load before any other imports
_original_torch_load = torch.load

def _patched_torch_load(f, map_location=None, pickle_module=None, *, weights_only=None, mmap=None, **kwargs):
    """Load torch checkpoint with weights_only=False for trusted pyannote models"""
    # Force weights_only=False for compatibility
    return _original_torch_load(f, map_location=map_location, pickle_module=pickle_module, weights_only=False, mmap=mmap, **kwargs)

torch.load = _patched_torch_load

# Now import the rest
import whisperx
from whisperx.diarize import DiarizationPipeline
import json

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # Go up two levels: steps -> scripts -> project root
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"

# Find the first video file in the input directory
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v']
video_files = [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS]

if not video_files:
    raise FileNotFoundError(f"No video files found in {INPUT_DIR}. Supported formats: {', '.join(VIDEO_EXTENSIONS)}")

VIDEO_FILE = video_files[0]  # Use the first video file found
VIDEO_BASE_NAME = VIDEO_FILE.stem  # Get filename without extension

# Create output directories if they don't exist
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

# Device and model settings
device = "cuda"  # RTX 5080 with CUDA 12.8
batch_size = 32  # Optimized for RTX 5080 (16GB VRAM)
compute_type = "float16"  # Best for modern NVIDIA GPUs
model_name = "large-v3"  # Using the largest and most accurate Whisper model

print(f"Loading video: {VIDEO_FILE}")
print(f"Using model: {model_name} on {device}")
print(f"Batch size: {batch_size}, Compute type: {compute_type}")

# 1. Transcribe with Whisper
print("\n=== Step 1: Transcribing audio ===")
model = whisperx.load_model(model_name, device, compute_type=compute_type, language="es")
audio = whisperx.load_audio(str(VIDEO_FILE))
result = model.transcribe(audio, batch_size=batch_size, language="es")

print("Language: Spanish")

# 2. Align whisper output
print("\n=== Step 2: Aligning timestamps ===")
model_a, metadata = whisperx.load_align_model(language_code="es", device=device)
result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

# 3. Assign speaker labels (diarization)
print("\n=== Step 3: Performing speaker diarization ===")
hf_token = os.getenv('HF_TOKEN')
if not hf_token:
    raise ValueError("HF_TOKEN environment variable not set. Please set it with your Hugging Face token.")
diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
diarize_segments = diarize_model(audio)
result = whisperx.assign_word_speakers(diarize_segments, result)

# Save results
print("\n=== Saving results ===")

# Save full JSON output
output_json = TRANSCRIPTS_DIR / f"{VIDEO_BASE_NAME}_transcript.json"
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print(f"Saved JSON: {output_json}")

# Save human-readable transcript with speakers
output_txt = TRANSCRIPTS_DIR / f"{VIDEO_BASE_NAME}_transcript.txt"
with open(output_txt, "w", encoding="utf-8") as f:
    current_speaker = None
    for segment in result["segments"]:
        speaker = segment.get("speaker", "Unknown")
        text = segment["text"]
        
        if speaker != current_speaker:
            f.write(f"\n{speaker}:\n")
            current_speaker = speaker
        
        f.write(f"{text}\n")
print(f"Saved text: {output_txt}")

# Save detailed transcript with timestamps
output_detailed = TRANSCRIPTS_DIR / f"{VIDEO_BASE_NAME}_transcript_detailed.txt"
with open(output_detailed, "w", encoding="utf-8") as f:
    for segment in result["segments"]:
        speaker = segment.get("speaker", "Unknown")
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        
        f.write(f"[{start:.2f}s - {end:.2f}s] {speaker}: {text}\n")
print(f"Saved detailed: {output_detailed}")

print("\n=== Transcription complete! ===")
print("\nSummary:")
speakers = set(seg.get("speaker", "Unknown") for seg in result["segments"])
print(f"- Detected speakers: {', '.join(sorted(speakers))}")
print(f"- Total segments: {len(result['segments'])}")
