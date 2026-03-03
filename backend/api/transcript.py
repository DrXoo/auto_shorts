"""
Transcript API — view, edit speakers, merge, rename, fix consistency.
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.models import (
    SpeakerBulkRenameRequest,
    SpeakerInfo,
    SpeakerRenameRequest,
    SegmentSpeakerUpdate,
    Transcript,
)

router = APIRouter(prefix="/api/transcript", tags=["transcript"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
TRANSCRIPTS_DIR = PROJECT_ROOT / "output" / "transcripts"


def _find_transcript() -> Path | None:
    if not TRANSCRIPTS_DIR.exists():
        return None
    for f in TRANSCRIPTS_DIR.glob("*_transcript.json"):
        if "_fixed" not in f.stem:
            return f
    return None


def _load_transcript() -> tuple[Path, dict]:
    path = _find_transcript()
    if not path:
        raise HTTPException(404, "No transcript found. Run transcription first.")
    with open(path, 'r', encoding='utf-8') as f:
        return path, json.load(f)


def _save_transcript(path: Path, data: dict):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─── Read ───────────────────────────────────────────────────────────

@router.get("")
def get_transcript():
    """Return the full transcript JSON."""
    path, data = _load_transcript()
    return {"path": str(path), "data": data}


@router.get("/speakers")
def get_speakers():
    """List distinct speakers with stats."""
    _, data = _load_transcript()
    stats: dict[str, dict] = defaultdict(lambda: {"word_count": 0, "talk_time": 0.0, "segment_count": 0})

    for seg in data.get("segments", []):
        speaker = seg.get("speaker") or seg.get("words", [{}])[0].get("speaker", "UNKNOWN")
        stats[speaker]["segment_count"] += 1
        stats[speaker]["talk_time"] += seg.get("end", 0) - seg.get("start", 0)
        stats[speaker]["word_count"] += len(seg.get("words", []))

    result = []
    for sid, s in sorted(stats.items()):
        result.append(SpeakerInfo(
            speaker_id=sid,
            word_count=s["word_count"],
            total_talk_time=round(s["talk_time"], 2),
            segment_count=s["segment_count"],
        ))
    return result


# ─── Edit single segment speaker ────────────────────────────────────

@router.put("/segment/{index}")
def update_segment_speaker(index: int, body: SegmentSpeakerUpdate):
    """Change the speaker label of a specific segment (and its words)."""
    path, data = _load_transcript()
    segments = data.get("segments", [])

    if index < 0 or index >= len(segments):
        raise HTTPException(400, f"Segment index {index} out of range (0-{len(segments)-1})")

    segments[index]["speaker"] = body.speaker
    for word in segments[index].get("words", []):
        word["speaker"] = body.speaker

    _save_transcript(path, data)
    return {"message": f"Segment {index} updated to speaker {body.speaker}"}


# ─── Bulk rename / merge speakers ──────────────────────────────────

@router.put("/speakers/bulk-rename")
def bulk_rename_speaker(body: SpeakerBulkRenameRequest):
    """
    Merge source_speaker into target_speaker.
    All words and segments labeled as source become target.
    Fixes the misdetection issue (e.g. SPEAKER_03 → SPEAKER_00).
    """
    path, data = _load_transcript()
    changed = 0

    for seg in data.get("segments", []):
        if seg.get("speaker") == body.source_speaker:
            seg["speaker"] = body.target_speaker
            changed += 1
        for word in seg.get("words", []):
            if word.get("speaker") == body.source_speaker:
                word["speaker"] = body.target_speaker

    _save_transcript(path, data)
    return {"message": f"Renamed {body.source_speaker} → {body.target_speaker}", "segments_changed": changed}


@router.put("/speakers/rename")
def rename_speaker(body: SpeakerRenameRequest):
    """Rename a speaker label (e.g. SPEAKER_00 → 'Carlos')."""
    path, data = _load_transcript()
    changed = 0

    for seg in data.get("segments", []):
        if seg.get("speaker") == body.old_name:
            seg["speaker"] = body.new_name
            changed += 1
        for word in seg.get("words", []):
            if word.get("speaker") == body.old_name:
                word["speaker"] = body.new_name

    _save_transcript(path, data)
    return {"message": f"Renamed {body.old_name} → {body.new_name}", "segments_changed": changed}


# ─── Fix word-level consistency ─────────────────────────────────────

@router.post("/fix-consistency")
def fix_speaker_consistency():
    """
    Ensure all words within a segment match the segment's speaker.
    (Port of scripts/utils/fix_speaker_consistency.py)
    """
    path, data = _load_transcript()
    fixed = 0

    for seg in data.get("segments", []):
        seg_speaker = seg.get("speaker")
        if not seg_speaker:
            continue
        for word in seg.get("words", []):
            if word.get("speaker") != seg_speaker:
                word["speaker"] = seg_speaker
                fixed += 1

    _save_transcript(path, data)
    return {"message": f"Fixed {fixed} word-level speaker labels"}


# ─── Save (explicit — frontend can POST after batch edits) ─────────

@router.post("/save")
def save_transcript(body: dict):
    """Persist a full transcript dict back to disk."""
    path = _find_transcript()
    if not path:
        raise HTTPException(404, "No transcript found")
    _save_transcript(path, body)
    return {"message": "Transcript saved"}


# ─── Update full transcript (for text edits) ───────────────────────

@router.put("")
def update_full_transcript(body: dict):
    """Replace the entire transcript data."""
    path = _find_transcript()
    if not path:
        raise HTTPException(404, "No transcript found")
    _save_transcript(path, body)
    return {"message": "Transcript updated"}
