"""
Utility services — wraps the misc tools from scripts/utils/.

Each function is a self-contained operation (no interactive input).
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional


# ─── Video Cutting ──────────────────────────────────────────────────

def cut_video(
    video_path: Path,
    start_time: float,
    end_time: float,
    output_path: Path,
) -> dict:
    """Cut a video between two timestamps using stream copy (no re-encode).
    If end_time is 0 or <= start_time, cuts from start_time to the end of the video.
    """
    video_path, output_path = Path(video_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start_time),
        '-i', str(video_path),
    ]

    # end_time=0 or end <= start means "cut to end of video"
    if end_time > 0 and end_time > start_time:
        cmd += ['-to', str(end_time - start_time)]

    cmd += [
        '-c', 'copy',
        '-avoid_negative_ts', 'make_zero',
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode == 0:
        return {"status": "ok", "output": str(output_path)}
    return {"status": "error", "error": result.stderr[:500]}


# ─── Background Music ──────────────────────────────────────────────

def _ffprobe_duration(path: str) -> float | None:
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', path]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8', 'replace').strip()
        return float(out) if out else None
    except Exception:
        return None


def _has_audio_stream(path: str) -> bool:
    try:
        probe = subprocess.check_output(
            ['ffprobe', '-v', 'error', '-select_streams', 'a',
             '-show_entries', 'stream=index', '-of', 'csv=p=0', path],
            stderr=subprocess.STDOUT
        ).decode('utf-8', 'replace').strip()
        return bool(probe)
    except Exception:
        return True  # assume yes if ffprobe fails


def add_background_music(
    video_path: Path,
    music_path: Path,
    output_path: Path,
    *,
    music_db: float = -37,
    fade_in: float = 5.0,
    start_delay_seconds: float = 0.0,
    audio_bitrate: str = "192k",
) -> dict:
    """Mix background music into a video."""
    video_path, music_path, output_path = Path(video_path), Path(music_path), Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    music_chain = f"volume={music_db}dB"
    if fade_in > 0:
        music_chain += f",afade=t=in:st=0:d={fade_in}"

    if start_delay_seconds > 0:
        delay_ms = int(start_delay_seconds * 1000)
        music_chain = f"adelay={delay_ms}|{delay_ms}," + music_chain

    if _has_audio_stream(str(video_path)):
        fc = f"[1:a]{music_chain}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0[aout]"
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-stream_loop', '-1',
            '-i', str(music_path),
            '-filter_complex', fc,
            '-map', '0:v', '-map', '[aout]',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', audio_bitrate,
            '-shortest', str(output_path),
        ]
    else:
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-stream_loop', '-1',
            '-i', str(music_path),
            '-filter_complex', f"[1:a]{music_chain}[aout]",
            '-map', '0:v', '-map', '[aout]',
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', audio_bitrate,
            '-shortest', str(output_path),
        ]
        dur = _ffprobe_duration(str(video_path))
        if dur is not None:
            cmd.insert(-1, '-t')
            cmd.insert(-1, str(dur))

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode == 0:
        return {"status": "ok", "output": str(output_path)}
    return {"status": "error", "error": result.stderr[:500]}


# ─── Clean Output ──────────────────────────────────────────────────

def clean_output(output_dir: Path) -> dict:
    """Delete all generated files from output subdirectories."""
    output_dir = Path(output_dir)
    subdirs = ["ai_analysis", "cropped", "extracted", "final", "transcripts"]
    total = 0

    for name in subdirs:
        subdir = output_dir / name
        if not subdir.exists():
            continue
        for item in subdir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                    total += 1
                except Exception:
                    pass

    # Also remove pipeline_state.json and trending_topics.json
    for extra in ["pipeline_state.json", "trending_topics.json"]:
        p = output_dir / extra
        if p.exists():
            try:
                p.unlink()
                total += 1
            except Exception:
                pass

    return {"deleted": total}


# ─── Video Info ─────────────────────────────────────────────────────

def get_video_info(video_path: Path) -> dict:
    """Get video metadata via ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height,codec_name,duration',
        '-show_entries', 'format=duration,size',
        '-of', 'json',
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        stream = data.get('streams', [{}])[0]
        fmt = data.get('format', {})
        return {
            "width": int(stream.get('width', 0)),
            "height": int(stream.get('height', 0)),
            "codec": stream.get('codec_name', ''),
            "duration": float(fmt.get('duration', stream.get('duration', 0))),
            "size": int(fmt.get('size', 0)),
        }
    except Exception:
        return {}


def generate_thumbnail(video_path: Path, output_path: Path, time_sec: float = 5) -> bool:
    """Generate a JPEG thumbnail from a video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(time_sec),
        '-i', str(video_path),
        '-vframes', '1',
        '-q:v', '5',
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0
