"""
Clips API — CRUD for clips.json + AI generation + external LLM support.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from backend.models import AIAnalysisRequest, ClipData, ClipsUpdateRequest

router = APIRouter(prefix="/api/clips", tags=["clips"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
AI_DIR = PROJECT_ROOT / "output" / "ai_analysis"
TRANSCRIPTS_DIR = PROJECT_ROOT / "output" / "transcripts"
CLIPS_JSON = AI_DIR / "clips.json"


def _find_transcript() -> Path | None:
    if not TRANSCRIPTS_DIR.exists():
        return None
    for f in TRANSCRIPTS_DIR.glob("*_transcript.json"):
        if "_fixed" not in f.stem:
            return f
    return None


# ─── CRUD ───────────────────────────────────────────────────────────

@router.get("")
def get_clips():
    """Return current clips.json content."""
    if not CLIPS_JSON.exists():
        return {"clips": [], "exists": False}
    with open(CLIPS_JSON, 'r', encoding='utf-8') as f:
        clips = json.load(f)
    return {"clips": clips, "exists": True}


@router.put("")
def update_clips(body: ClipsUpdateRequest):
    """Save the full clips array."""
    AI_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLIPS_JSON, 'w', encoding='utf-8') as f:
        json.dump([c.model_dump() for c in body.clips], f, indent=2, ensure_ascii=False)
    return {"message": f"Saved {len(body.clips)} clips"}


@router.delete("/{index}")
def delete_clip(index: int):
    """Remove a clip by its position in the array."""
    if not CLIPS_JSON.exists():
        raise HTTPException(404, "clips.json not found")
    with open(CLIPS_JSON, 'r', encoding='utf-8') as f:
        clips = json.load(f)
    if index < 0 or index >= len(clips):
        raise HTTPException(400, f"Index {index} out of range")
    removed = clips.pop(index)
    with open(CLIPS_JSON, 'w', encoding='utf-8') as f:
        json.dump(clips, f, indent=2, ensure_ascii=False)
    return {"message": f"Removed clip: {removed.get('title', index)}"}


# ─── AI Generation ─────────────────────────────────────────────────

@router.post("/generate")
def generate_clips(body: AIAnalysisRequest):
    """
    Call LLM to auto-generate clips from the transcript.
    Returns the proposals (not yet saved).
    """
    from backend.services.ai_analyzer import analyze_transcript

    # Get transcript text
    transcript_text = body.transcript_text
    if not transcript_text:
        tp = _find_transcript()
        if not tp:
            raise HTTPException(404, "No transcript found")
        # Use the plain-text version for the LLM
        txt_path = tp.with_name(tp.stem.replace("_transcript", "") + "_transcript.txt")
        if txt_path.exists():
            transcript_text = txt_path.read_text(encoding='utf-8')
        else:
            # Fallback: build text from JSON
            with open(tp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            lines = []
            for seg in data.get("segments", []):
                speaker = seg.get("speaker", "")
                lines.append(f"{speaker}: {seg.get('text', '')}")
            transcript_text = "\n".join(lines)

    try:
        result = analyze_transcript(transcript_text, body.config, PROJECT_ROOT)
    except Exception as e:
        raise HTTPException(500, f"AI analysis failed: {e}")

    return result


# ─── External LLM Support ──────────────────────────────────────────

@router.get("/prompt/{prompt_type}")
def get_prompt(prompt_type: str):
    """
    Return the prompt template so the user can copy it and paste
    into an external LLM (ChatGPT, Claude, etc.).
    """
    filename = f"{prompt_type}_extraction_prompt.txt"
    prompt_path = PROJECT_ROOT / filename
    if not prompt_path.exists():
        raise HTTPException(404, f"Prompt file not found: {filename}")
    return PlainTextResponse(prompt_path.read_text(encoding="utf-8"))


@router.get("/transcript-download")
def download_detailed_transcript():
    """
    Return the detailed transcript file for downloading / pasting
    into an external LLM alongside the prompt.
    """
    if not TRANSCRIPTS_DIR.exists():
        raise HTTPException(404, "No transcripts directory")

    # Prefer the detailed transcript (has timestamps + speakers per word)
    for f in TRANSCRIPTS_DIR.glob("*_transcript_detailed.txt"):
        return FileResponse(
            f,
            media_type="text/plain",
            filename=f.name,
        )
    # Fallback: plain transcript
    for f in TRANSCRIPTS_DIR.glob("*_transcript.txt"):
        return FileResponse(
            f,
            media_type="text/plain",
            filename=f.name,
        )
    raise HTTPException(404, "No transcript file found")


class ParseResponseRequest(BaseModel):
    llm_response: str


@router.post("/parse-response")
def parse_llm_response(body: ParseResponseRequest):
    """
    Parse raw LLM output (JSON, markdown code block, etc.) into
    structured clips. Used when the user runs the LLM externally
    and pastes the response back.
    """
    from backend.services.ai_analyzer import _extract_json

    try:
        parsed = _extract_json(body.llm_response)
    except ValueError as e:
        raise HTTPException(400, f"Could not parse JSON from response: {e}")

    # Normalize: could be a list or a dict with a "clips" key
    if isinstance(parsed, dict):
        clips_list = parsed.get("clips", parsed.get("hooks", []))
    elif isinstance(parsed, list):
        clips_list = parsed
    else:
        raise HTTPException(400, "Unexpected response format")

    # Ensure clip_number is set
    for i, clip in enumerate(clips_list):
        if "clip_number" not in clip:
            clip["clip_number"] = i + 1
        # Ensure required fields
        clip.setdefault("title", f"Clip {clip['clip_number']}")
        clip.setdefault("start_time", 0)
        clip.setdefault("end_time", 60)
        if "duration_seconds" not in clip:
            clip["duration_seconds"] = clip["end_time"] - clip["start_time"]

    return {"clips": clips_list}
