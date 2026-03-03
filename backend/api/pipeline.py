"""
Pipeline API — run steps, check status, reset.
"""

import json
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.models import (
    PipelineState,
    PipelineStatus,
    PipelineStepStatus,
    TranscriptionConfig,
    SubtitleStyle,
)
from backend.services import (
    transcriber,
    clip_extractor,
    cropper,
    subtitler,
)
from backend.ws import manager as ws_manager

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

# Resolve project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent   # backend/api → backend → project root
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
STATE_FILE = OUTPUT_DIR / "pipeline_state.json"
AI_DIR = OUTPUT_DIR / "ai_analysis"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
EXTRACTED_DIR = OUTPUT_DIR / "extracted"
CROPPED_DIR = OUTPUT_DIR / "cropped"
FINAL_DIR = OUTPUT_DIR / "final"

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}


def _find_video(name: str | None = None) -> Path | None:
    """Find a video in input/. If name given, look for that specific file."""
    if not INPUT_DIR.exists():
        return None
    if name:
        candidate = INPUT_DIR / name
        if candidate.is_file() and candidate.suffix.lower() in VIDEO_EXTENSIONS:
            return candidate
        return None
    for f in INPUT_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            return f
    return None


def _list_input_videos() -> list[dict]:
    """List all video files in input/."""
    if not INPUT_DIR.exists():
        return []
    from backend.services.utils import get_video_info
    videos = []
    for f in sorted(INPUT_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            info = get_video_info(f)
            videos.append({
                "name": f.name,
                "size": f.stat().st_size,
                **info,
            })
    return videos


def _find_transcript() -> Path | None:
    if not TRANSCRIPTS_DIR.exists():
        return None
    for f in TRANSCRIPTS_DIR.glob("*_transcript.json"):
        return f
    return None


def _count_files(d: Path, ext: str = ".mp4") -> int:
    if not d.exists():
        return 0
    return len([f for f in d.glob(f"*{ext}")])


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"completed_steps": [], "last_run": None}


def _save_state(state: dict):
    state["last_run"] = datetime.now().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ─── Input Videos ────────────────────────────────────────────────────

@router.get("/input-videos")
def list_input_videos():
    """List all video files in input/ folder."""
    return _list_input_videos()


@router.delete("/input-videos/{filename}")
def delete_input_video(filename: str):
    """Delete a video from input/ folder."""
    path = INPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, f"Video not found: {filename}")
    path.unlink()
    return {"deleted": filename}


# ─── Status ─────────────────────────────────────────────────────────

@router.get("/status", response_model=PipelineStatus)
def pipeline_status():
    state = _load_state()
    completed = set(state.get("completed_steps", []))

    steps_def = [
        (1, "Transcribe", "Transcribe video with speaker diarization"),
        (2, "AI Analysis", "Generate clips.json via LLM or manually"),
        (3, "Extract Clips", "Extract clips from source video"),
        (4, "Crop to Vertical", "Crop to 9:16 with speaker-aware framing"),
        (5, "Add Subtitles", "Burn karaoke subtitles into videos"),
    ]

    steps = []
    for num, name, desc in steps_def:
        status = "completed" if num in completed else "pending"
        steps.append(PipelineStepStatus(step=num, name=name, status=status, description=desc))

    video = _find_video()
    transcript = _find_transcript()
    clips_json = AI_DIR / "clips.json"

    from backend.services.utils import get_video_info
    duration = None
    if video:
        info = get_video_info(video)
        duration = info.get("duration")

    return PipelineStatus(
        steps=steps,
        input_video=video.name if video else None,
        input_video_duration=duration,
        has_transcript=transcript is not None,
        has_clips_json=clips_json.exists(),
        output_counts={
            "extracted": _count_files(EXTRACTED_DIR),
            "cropped": _count_files(CROPPED_DIR),
            "final": _count_files(FINAL_DIR),
        },
    )


# ─── Run Individual Steps ───────────────────────────────────────────

@router.post("/run/transcribe")
def run_transcribe(config: TranscriptionConfig | None = None, video_name: str | None = None):
    """Run Step 1: Transcription (blocking — heavy GPU work)."""
    video = _find_video(video_name)
    if not video:
        raise HTTPException(404, "No video file found in input/")

    cfg = config or TranscriptionConfig()

    def _task():
        try:
            result = transcriber.transcribe(
                video_path=video,
                output_dir=TRANSCRIPTS_DIR,
                language=cfg.language,
                model_name=cfg.model_name,
                batch_size=cfg.batch_size,
                compute_type=cfg.compute_type,
                device=cfg.device,
            )
            state = _load_state()
            if 1 not in state["completed_steps"]:
                state["completed_steps"].append(1)
            _save_state(state)
        except Exception as e:
            import asyncio, traceback
            traceback.print_exc()
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(ws_manager.send_error("transcribe", str(e)))
                loop.close()
            except Exception:
                pass

    thread = Thread(target=_task, daemon=True)
    thread.start()
    return {"message": "Transcription started", "video": video.name}


@router.post("/run/extract")
def run_extract(video_name: str | None = None):
    """Run Step 3: Extract clips."""
    video = _find_video(video_name)
    clips_json = AI_DIR / "clips.json"
    if not video:
        raise HTTPException(404, "No video file in input/")
    if not clips_json.exists():
        raise HTTPException(404, "clips.json not found in output/ai_analysis/")

    with open(clips_json, 'r', encoding='utf-8') as f:
        raw_clips = json.load(f)

    from backend.models import ClipData
    clips = [ClipData(**c) for c in raw_clips]

    def _task():
        try:
            clip_extractor.extract_clips(video, clips, EXTRACTED_DIR)
            state = _load_state()
            if 3 not in state["completed_steps"]:
                state["completed_steps"].append(3)
            _save_state(state)
        except Exception as e:
            import asyncio, traceback
            traceback.print_exc()

    thread = Thread(target=_task, daemon=True)
    thread.start()
    return {"message": "Clip extraction started", "clip_count": len(clips)}


@router.post("/run/crop")
def run_crop(
    num_speakers: int = 3,
    scene_type: str | None = None,
    dynamic_enabled: bool = True,
):
    """Run Step 4: Crop to vertical."""
    transcript = _find_transcript()
    clips_json = AI_DIR / "clips.json"

    def _task():
        try:
            cropper.crop_videos(
                input_dir=EXTRACTED_DIR,
                output_dir=CROPPED_DIR,
                num_speakers=num_speakers,
                scene_type=scene_type,
                transcript_path=transcript,
                clips_json_path=clips_json if clips_json.exists() else None,
                dynamic_enabled=dynamic_enabled,
            )
            state = _load_state()
            if 4 not in state["completed_steps"]:
                state["completed_steps"].append(4)
            _save_state(state)
        except Exception as e:
            import traceback
            traceback.print_exc()

    thread = Thread(target=_task, daemon=True)
    thread.start()
    return {"message": "Cropping started", "num_speakers": num_speakers}


@router.post("/run/subtitle")
def run_subtitle(style: SubtitleStyle | None = None):
    """Run Step 5: Add subtitles."""
    transcript = _find_transcript()
    clips_json = AI_DIR / "clips.json"
    if not transcript:
        raise HTTPException(404, "No transcript found")
    if not clips_json.exists():
        raise HTTPException(404, "clips.json not found")

    def _task():
        try:
            subtitler.add_subtitles(
                cropped_dir=CROPPED_DIR,
                output_dir=FINAL_DIR,
                clips_json_path=clips_json,
                transcript_json_path=transcript,
                style=style,
            )
            state = _load_state()
            if 5 not in state["completed_steps"]:
                state["completed_steps"].append(5)
            _save_state(state)
        except Exception as e:
            import traceback
            traceback.print_exc()

    thread = Thread(target=_task, daemon=True)
    thread.start()
    return {"message": "Subtitle generation started"}


@router.post("/run/subtitle/{filename}")
def run_subtitle_single(filename: str, style: SubtitleStyle | None = None):
    """Re-generate subtitles for a single final video (synchronous)."""
    transcript = _find_transcript()
    clips_json = AI_DIR / "clips.json"
    if not transcript:
        raise HTTPException(404, "No transcript found")
    if not clips_json.exists():
        raise HTTPException(404, "clips.json not found")

    final_path = FINAL_DIR / filename
    if not final_path.exists():
        raise HTTPException(404, f"Final video not found: {filename}")

    result = subtitler.subtitle_single_video(
        filename=filename,
        cropped_dir=CROPPED_DIR,
        output_dir=FINAL_DIR,
        clips_json_path=clips_json,
        transcript_json_path=transcript,
        style=style,
    )
    if result.get("status") == "error":
        raise HTTPException(500, result.get("error", "Unknown error"))
    return result


# ─── Reset ──────────────────────────────────────────────────────────

@router.post("/reset")
def reset_pipeline():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    return {"message": "Pipeline state reset"}
