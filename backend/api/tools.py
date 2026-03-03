"""
Tools API — utility operations (cut, music, clean, etc.)
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File

from backend.models import CutVideoRequest, AddMusicRequest
from backend.services.utils import cut_video, add_background_music, clean_output

router = APIRouter(prefix="/api/tools", tags=["tools"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}


def _resolve_video(video_path: str) -> Path:
    """Resolve a video path — accepts relative (from output/) or absolute."""
    p = Path(video_path)
    if p.is_absolute() and p.exists():
        return p
    # Try relative to output
    candidate = OUTPUT_DIR / video_path
    if candidate.exists():
        return candidate
    # Try relative to input
    candidate = INPUT_DIR / video_path
    if candidate.exists():
        return candidate
    raise HTTPException(404, f"Video not found: {video_path}")


# ─── Cut Video ──────────────────────────────────────────────────────

@router.post("/cut-video")
def api_cut_video(body: CutVideoRequest):
    video = _resolve_video(body.video_path)
    out_name = body.output_name or f"{video.stem}_cut.mp4"
    out_dir = INPUT_DIR if body.output_to_input else OUTPUT_DIR / "final"
    output = out_dir / out_name
    result = cut_video(video, body.start_time, body.end_time, output)
    if result["status"] != "ok":
        raise HTTPException(500, result.get("error", "Cut failed"))
    return result


# ─── Add Background Music ──────────────────────────────────────────

def _resolve_music(music_path: str) -> Path:
    """Resolve a music file path — accepts relative (from input/) or absolute."""
    p = Path(music_path)
    if p.is_absolute() and p.exists():
        return p
    candidate = INPUT_DIR / music_path
    if candidate.exists():
        return candidate
    raise HTTPException(404, f"Music file not found: {music_path}")


@router.post("/add-music")
def api_add_music(body: AddMusicRequest):
    video = _resolve_video(body.video_path)
    music = _resolve_music(body.music_path)

    out_name = body.output_name or f"{video.stem}_bg.mp4"
    out_dir = INPUT_DIR if body.output_to_input else OUTPUT_DIR / "final"
    output = out_dir / out_name

    result = add_background_music(
        video, music, output,
        music_db=body.music_db,
        fade_in=body.fade_in,
        start_delay_seconds=body.start_delay_seconds,
        audio_bitrate=body.audio_bitrate,
    )
    if result["status"] != "ok":
        raise HTTPException(500, result.get("error", "Music mixing failed"))
    return result


# ─── Clean Output ──────────────────────────────────────────────────

@router.post("/clean-output")
def api_clean_output():
    result = clean_output(OUTPUT_DIR)
    return result


# ─── Music file upload ──────────────────────────────────────────────

@router.post("/upload-music")
async def upload_music(file: UploadFile = File(...)):
    """Upload a music file to input/."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not file.filename:
        raise HTTPException(400, "No filename")
    import shutil
    dest = INPUT_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"filename": file.filename, "path": str(dest), "size": dest.stat().st_size}
