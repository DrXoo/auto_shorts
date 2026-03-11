"""
Tools API — utility operations (cut, music, clean, etc.)
"""

import json
import tempfile
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import Response

from backend.models import CutVideoRequest, AddMusicRequest, EditorRenderRequest
from backend.services.utils import cut_video, add_background_music, clean_output, get_video_info
from backend.services.editor_renderer import render_composition, extract_frame_jpeg

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
    # Try relative to output root
    candidate = OUTPUT_DIR / video_path
    if candidate.exists():
        return candidate
    # Try in each output stage subdirectory
    for subdir in ("extracted", "cropped", "final"):
        candidate = OUTPUT_DIR / subdir / video_path
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


# ─── Editor ─────────────────────────────────────────────────────────

EDITOR_DIR = OUTPUT_DIR / "editor"


@router.get("/editor/video-info")
def editor_video_info(video_path: str = Query(...)):
    """Return width/height/duration/codec for a video in any stage directory."""
    video = _resolve_video(video_path)
    info = get_video_info(video)
    if not info:
        raise HTTPException(500, "Could not read video info")
    return {**info, "name": video.name, "path": video_path}


@router.get("/editor/frame")
def editor_frame(
    video_path: str = Query(...),
    time_sec: float = Query(0.0),
):
    """Return a JPEG frame from the video at the given timestamp."""
    video = _resolve_video(video_path)
    jpeg = extract_frame_jpeg(video, time_sec)
    if not jpeg:
        raise HTTPException(500, "Could not extract frame")
    return Response(content=jpeg, media_type="image/jpeg")


@router.post("/editor/render")
def editor_render(body: EditorRenderRequest):
    """
    Start a background render job for a custom composition.
    Progress is streamed over WebSocket (step='editor').
    """
    video = _resolve_video(body.video_path)
    output_dir = OUTPUT_DIR / "cropped"
    temp_dir = OUTPUT_DIR / "editor_temp"

    def _run():
        render_composition(body, video, output_dir, temp_dir)

    Thread(target=_run, daemon=True).start()
    return {"status": "started", "video": body.video_path}


@router.post("/editor/save")
def editor_save(body: dict):
    """Persist a composition JSON for later editing."""
    EDITOR_DIR.mkdir(parents=True, exist_ok=True)
    video_path = body.get("video_path", "")
    if not video_path:
        raise HTTPException(400, "video_path is required")
    name = Path(video_path).stem + "_composition.json"
    dest = EDITOR_DIR / name
    dest.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return {"status": "ok", "file": name}


@router.get("/editor/load")
def editor_load(video_path: str = Query(...)):
    """Load a previously saved composition for the given video."""
    name = Path(video_path).stem + "_composition.json"
    dest = EDITOR_DIR / name
    if not dest.exists():
        return {"exists": False, "composition": None}
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
        return {"exists": True, "composition": data}
    except Exception as e:
        raise HTTPException(500, f"Could not read composition: {e}")
