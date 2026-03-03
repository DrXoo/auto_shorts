"""
Clip extractor service — extracts video clips using ffmpeg.

Refactored from scripts/steps/2_extract_clips.py.
"""

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from backend.models import ClipData
from backend.ws import manager as ws_manager


def sanitize_filename(title: str, max_len: int = 60) -> str:
    clean = re.sub(r'[^\w\s-]', '', title)
    clean = re.sub(r'\s+', '_', clean)
    return clean[:max_len]


def extract_clips(
    video_path: Path,
    clips: list[ClipData],
    output_dir: Path,
) -> dict:
    """
    Extract clips from *video_path* based on the clips list.
    Returns summary dict with successful / failed counts.
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loop = asyncio.new_event_loop()
    total = len(clips)
    successful = 0
    failed = 0
    results: list[dict] = []

    for i, clip in enumerate(clips, 1):
        pct = (i / total) * 100
        title = clip.title
        safe_title = sanitize_filename(title)
        output_file = output_dir / f"clip_{clip.clip_number:02d}_{safe_title}.mp4"

        start = clip.start_time
        end = clip.end_time
        duration = end - start

        try:
            loop.run_until_complete(
                ws_manager.send_progress("extract", pct, f"Extracting clip {i}/{total}: {title[:40]}…")
            )
        except Exception:
            pass

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start),
            '-i', str(video_path),
            '-t', str(duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-preset', 'fast',
            '-avoid_negative_ts', 'make_zero',
            str(output_file),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')

        if result.returncode == 0:
            successful += 1
            results.append({"clip_number": clip.clip_number, "file": output_file.name, "status": "ok"})
        else:
            failed += 1
            results.append({"clip_number": clip.clip_number, "file": output_file.name,
                            "status": "error", "error": result.stderr[:300]})

    try:
        loop.run_until_complete(
            ws_manager.send_complete("extract", f"Extracted {successful}/{total} clips", {"results": results})
        )
    except Exception:
        pass
    loop.close()

    return {"successful": successful, "failed": failed, "total": total, "results": results}
