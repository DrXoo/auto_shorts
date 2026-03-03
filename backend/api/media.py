"""
Media API — file upload, video serving, thumbnails.
"""

import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from backend.services.utils import get_video_info, generate_thumbnail

router = APIRouter(prefix="/api/media", tags=["media"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
THUMBS_DIR = OUTPUT_DIR / "thumbnails"

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}
STAGE_DIRS = {
    "input": INPUT_DIR,
    "extracted": OUTPUT_DIR / "extracted",
    "cropped": OUTPUT_DIR / "cropped",
    "final": OUTPUT_DIR / "final",
}


# ─── Upload ─────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file to input/."""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(400, "No filename")

    dest = INPUT_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    info = get_video_info(dest)
    return {"filename": file.filename, "size": dest.stat().st_size, **info}


# ─── List files ─────────────────────────────────────────────────────

@router.get("/list/{stage}")
def list_files(stage: str):
    """List video files in a stage directory."""
    d = STAGE_DIRS.get(stage)
    if not d:
        raise HTTPException(400, f"Unknown stage: {stage}. Use: {list(STAGE_DIRS.keys())}")
    if not d.exists():
        return []

    files = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            info = get_video_info(f)
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                **info,
            })
    return files


# ─── Serve video ────────────────────────────────────────────────────

@router.get("/file/{stage}/{filename}")
def serve_file(stage: str, filename: str):
    """Serve a video file for preview."""
    d = STAGE_DIRS.get(stage)
    if not d:
        raise HTTPException(400, f"Unknown stage: {stage}")
    path = d / filename
    if not path.exists():
        raise HTTPException(404, f"File not found: {filename}")
    return FileResponse(path, media_type="video/mp4")


# ─── Input video info ──────────────────────────────────────────────

@router.get("/input-info")
def input_video_info():
    """Get info about the current input video."""
    if not INPUT_DIR.exists():
        return {"exists": False}
    for f in INPUT_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            info = get_video_info(f)
            return {"exists": True, "name": f.name, "size": f.stat().st_size, **info}
    return {"exists": False}


# ─── Thumbnails ─────────────────────────────────────────────────────

@router.get("/thumbnail/{stage}/{filename}")
def serve_thumbnail(stage: str, filename: str):
    """Generate and serve a JPEG thumbnail."""
    d = STAGE_DIRS.get(stage)
    if not d:
        raise HTTPException(400, f"Unknown stage: {stage}")
    video = d / filename
    if not video.exists():
        raise HTTPException(404, f"Video not found: {filename}")

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    thumb = THUMBS_DIR / f"{stage}_{video.stem}.jpg"

    if not thumb.exists():
        ok = generate_thumbnail(video, thumb)
        if not ok:
            raise HTTPException(500, "Failed to generate thumbnail")

    return FileResponse(thumb, media_type="image/jpeg")
