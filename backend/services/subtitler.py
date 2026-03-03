"""
Subtitler service — generates ASS karaoke subtitles and burns them into video.

Refactored from scripts/steps/4_add_subtitles.py.
Subtitle style is now fully configurable.
"""

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from backend.models import SubtitleStyle
from backend.ws import manager as ws_manager

DEFAULT_STYLE = SubtitleStyle()


def seconds_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def create_ass_subtitle(
    words: list[dict],
    clip_start_time: float,
    output_path: Path,
    style: SubtitleStyle | None = None,
) -> Path:
    """Generate an ASS subtitle file with karaoke effect."""
    style = style or DEFAULT_STYLE
    bold_val = "-1" if style.bold else "0"

    ass_content = f"""[Script Info]
Title: Podcast Subtitle
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {style.play_res_x}
PlayResY: {style.play_res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{style.primary_color},{style.secondary_color},{style.outline_color},{style.back_color},{bold_val},0,0,0,100,100,0,0,1,{style.outline},{style.shadow},{style.alignment},{style.margin_l},{style.margin_r},{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Group words into chunks
    chunks: list[list[dict]] = []
    current: list[dict] = []

    for i, wd in enumerate(words):
        current.append(wd)
        if len(current) >= style.max_words_per_chunk:
            chunks.append(current)
            current = []
        elif i < len(words) - 1:
            nxt = words[i + 1]
            if nxt['start'] - wd['end'] > style.pause_threshold:
                chunks.append(current)
                current = []
    if current:
        chunks.append(current)

    for chunk in chunks:
        if not chunk:
            continue
        start = chunk[0]['start'] - clip_start_time
        end = chunk[-1]['end'] - clip_start_time
        if start < 0 or end < 0:
            continue

        karaoke = ""
        for wd in chunk:
            dur_cs = int((wd['end'] - wd['start']) * 100)
            karaoke += f"{{\\k{dur_cs}}}{wd['word']} "

        ass_content += (
            f"Dialogue: 0,{seconds_to_ass_time(start)},{seconds_to_ass_time(end)},"
            f"Default,,0,0,0,,{karaoke.strip()}\n"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    return output_path


def subtitle_single_video(
    filename: str,
    cropped_dir: Path,
    output_dir: Path,
    clips_json_path: Path,
    transcript_json_path: Path,
    style: SubtitleStyle | None = None,
) -> dict:
    """
    Re-burn subtitles for a single final video.
    `filename` is the name in the final/ dir (e.g. clip_1_cropped_subtitled.mp4).
    The corresponding cropped source is found by removing '_subtitled' suffix.
    """
    cropped_dir = Path(cropped_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive cropped source name
    stem = Path(filename).stem
    if stem.endswith("_subtitled"):
        cropped_stem = stem[: -len("_subtitled")]
    else:
        cropped_stem = stem
    cropped_file = cropped_dir / f"{cropped_stem}.mp4"
    if not cropped_file.exists():
        return {"status": "error", "error": f"Cropped source not found: {cropped_file.name}"}

    # Load clips
    with open(clips_json_path, 'r', encoding='utf-8') as f:
        clips = json.load(f)

    # Load transcript words
    with open(transcript_json_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)
    all_words: list[dict] = []
    for seg in transcript.get('segments', []):
        all_words.extend(seg.get('words', []))

    match = re.search(r'clip_(\d+)_', cropped_file.name)
    if not match:
        return {"status": "error", "error": "Cannot determine clip number"}

    clip_num = int(match.group(1))
    clip_data = next((c for c in clips if c.get('clip_number') == clip_num), None)
    if not clip_data:
        return {"status": "error", "error": f"No clip metadata for clip {clip_num}"}

    start_time = float(clip_data['start_time'])
    end_time = float(clip_data['end_time'])
    clip_words = [w for w in all_words if start_time <= w['start'] <= end_time]
    if not clip_words:
        return {"status": "error", "error": "No words found in clip time range"}

    ass_file = cropped_dir / f"{cropped_file.stem}.ass"
    create_ass_subtitle(clip_words, start_time, ass_file, style)

    output_file = output_dir / filename
    cmd = [
        'ffmpeg', '-i', str(cropped_file),
        '-vf', f'ass={ass_file.name}',
        '-c:a', 'copy', '-y', str(output_file),
    ]
    res = subprocess.run(cmd, cwd=cropped_dir, capture_output=True, text=True)
    try:
        ass_file.unlink()
    except Exception:
        pass

    if res.returncode == 0:
        return {"status": "ok", "file": filename}
    else:
        return {"status": "error", "error": res.stderr[:300]}


def add_subtitles(
    cropped_dir: Path,
    output_dir: Path,
    clips_json_path: Path,
    transcript_json_path: Path,
    style: SubtitleStyle | None = None,
) -> dict:
    """
    Burn karaoke subtitles into all cropped videos.
    Returns summary dict.
    """
    cropped_dir = Path(cropped_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load clips
    with open(clips_json_path, 'r', encoding='utf-8') as f:
        clips = json.load(f)

    # Load transcript and flatten words
    with open(transcript_json_path, 'r', encoding='utf-8') as f:
        transcript = json.load(f)

    all_words: list[dict] = []
    for seg in transcript.get('segments', []):
        all_words.extend(seg.get('words', []))

    video_files = sorted(cropped_dir.glob("*.mp4"))
    total = len(video_files)

    loop = asyncio.new_event_loop()
    successful = 0
    failed = 0
    results: list[dict] = []

    for i, vf in enumerate(video_files, 1):
        pct = (i / total) * 100 if total else 100
        try:
            loop.run_until_complete(
                ws_manager.send_progress("subtitle", pct, f"Adding subtitles {i}/{total}: {vf.name}")
            )
        except Exception:
            pass

        match = re.search(r'clip_(\d+)_', vf.name)
        if not match:
            results.append({"file": vf.name, "status": "skipped", "reason": "no clip number"})
            continue

        clip_num = int(match.group(1))
        clip_data = next((c for c in clips if c.get('clip_number') == clip_num), None)
        if not clip_data:
            results.append({"file": vf.name, "status": "skipped", "reason": "no clip metadata"})
            continue

        start_time = float(clip_data['start_time'])
        end_time = float(clip_data['end_time'])
        clip_words = [w for w in all_words if start_time <= w['start'] <= end_time]

        if not clip_words:
            results.append({"file": vf.name, "status": "skipped", "reason": "no words in range"})
            continue

        ass_file = cropped_dir / f"{vf.stem}.ass"
        create_ass_subtitle(clip_words, start_time, ass_file, style)

        output_file = output_dir / f"{vf.stem}_subtitled.mp4"
        cmd = [
            'ffmpeg', '-i', str(vf),
            '-vf', f'ass={ass_file.name}',
            '-c:a', 'copy', '-y', str(output_file),
        ]

        res = subprocess.run(cmd, cwd=cropped_dir, capture_output=True, text=True)
        if res.returncode == 0:
            successful += 1
            results.append({"file": output_file.name, "status": "ok"})
            try:
                ass_file.unlink()
            except Exception:
                pass
        else:
            failed += 1
            results.append({"file": vf.name, "status": "error", "error": res.stderr[:300]})

    try:
        loop.run_until_complete(
            ws_manager.send_complete("subtitle", f"Subtitled {successful}/{total} videos")
        )
    except Exception:
        pass
    loop.close()

    return {"successful": successful, "failed": failed, "total": total, "results": results}
