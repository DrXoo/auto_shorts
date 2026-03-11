"""
Editor Renderer service — renders a custom composition from the web editor.

Supports segment-based rendering where each segment can either show:
  - The default speaker crop (no content segment)
  - Fullscreen content crop
  - Split-screen: content top / speaker bottom  (layout="split_top")
  - Split-screen: speaker top / content bottom  (layout="split_bottom")

Strategy: cut each chunk (speaker / content), render it, then concat via
          `ffmpeg -f concat`. Uses stream-copy for audio throughout.
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from backend.models import ContentSegment, CropRegion, EditorRenderRequest
from backend.ws import manager as ws_manager


# ─── Helper: run ffmpeg and capture errors ──────────────────────────

def _run(cmd: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return result.returncode == 0, result.stderr[-800:] if result.stderr else ""


def _send(loop: asyncio.AbstractEventLoop, pct: float, msg: str) -> None:
    try:
        loop.run_until_complete(ws_manager.send_progress("editor", pct, msg))
    except Exception:
        pass


# ─── Per-chunk render helpers ────────────────────────────────────────

def _scale_pad(label: str, w: int, h: int) -> str:
    """Scale + pad a labeled stream to exact dimensions."""
    return (
        f"[{label}]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[{label}out]"
    )


def _render_speaker_chunk(
    src: Path,
    start: float,
    end: float,
    region: CropRegion,
    out: Path,
    out_w: int,
    out_h: int,
) -> tuple[bool, str]:
    """Render a speaker-only vertical chunk."""
    fc = (
        f"[0:v]crop={region.width}:{region.height}:{region.x}:{region.y}[c];"
        f"[c]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[out]"
    )
    return _run([
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(src),
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ])


def _render_fullscreen_content_chunk(
    src: Path,
    start: float,
    end: float,
    region: CropRegion,
    out: Path,
    out_w: int,
    out_h: int,
) -> tuple[bool, str]:
    """Render a fullscreen content vertical chunk."""
    fc = (
        f"[0:v]crop={region.width}:{region.height}:{region.x}:{region.y}[c];"
        f"[c]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[out]"
    )
    return _run([
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(src),
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ])


def _render_split_chunk(
    src: Path,
    start: float,
    end: float,
    content_region: CropRegion,
    speaker_region: CropRegion,
    layout: str,   # "split_top" | "split_bottom"
    out: Path,
    out_w: int,
    out_h: int,
) -> tuple[bool, str]:
    """Render a split-screen (content + speaker) vertical chunk."""
    half_h = out_h // 2

    if layout == "split_top":
        # content on top, speaker on bottom
        top_r, bot_r = content_region, speaker_region
    else:
        # speaker on top, content on bottom
        top_r, bot_r = speaker_region, content_region

    fc = (
        f"[0:v]crop={top_r.width}:{top_r.height}:{top_r.x}:{top_r.y}[top_raw];"
        f"[0:v]crop={bot_r.width}:{bot_r.height}:{bot_r.x}:{bot_r.y}[bot_raw];"
        f"[top_raw]scale={out_w}:{half_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{half_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[top];"
        f"[bot_raw]scale={out_w}:{half_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{half_h}:(ow-iw)/2:(oh-ih)/2,setsar=1[bot];"
        f"[top][bot]vstack=inputs=2[out]"
    )
    return _run([
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(src),
        "-filter_complex", fc,
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        str(out),
    ])


# ─── Concat helper ────────────────────────────────────────────────────

def _concat_chunks(chunk_paths: list[Path], output: Path) -> tuple[bool, str]:
    """Concatenate rendered chunks using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for p in chunk_paths:
            f.write(f"file '{p.as_posix()}'\n")
        list_path = f.name

    ok, err = _run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        str(output),
    ])
    # clean up list file
    try:
        Path(list_path).unlink()
    except Exception:
        pass
    return ok, err


# ─── Timeline builder ────────────────────────────────────────────────

def _build_timeline(
    duration: float,
    segments: list[ContentSegment],
    default_speaker_region: CropRegion,
) -> list[dict]:
    """
    Convert a list of ContentSegments + a total duration into an ordered
    list of 'chunks' describing what to render for each time interval.

    Returns list of dicts:
        { "start": float, "end": float, "type": "speaker"|"content",
          "segment": ContentSegment|None }
    """
    # Sort segments by start time
    segs = sorted(segments, key=lambda s: s.start)

    chunks: list[dict] = []
    cursor = 0.0

    for seg in segs:
        s_start = max(0.0, seg.start)
        s_end = min(duration, seg.end)
        if s_end <= s_start:
            continue

        # Gap before this segment → speaker chunk
        if s_start > cursor:
            chunks.append({
                "start": cursor,
                "end": s_start,
                "type": "speaker",
                "segment": None,
            })

        # Content chunk
        chunks.append({
            "start": s_start,
            "end": s_end,
            "type": "content",
            "segment": seg,
        })
        cursor = s_end

    # Trailing speaker chunk
    if cursor < duration:
        chunks.append({
            "start": cursor,
            "end": duration,
            "type": "speaker",
            "segment": None,
        })

    return chunks


# ─── Frame extraction (used by the editor API for previews) ─────────

def extract_frame_jpeg(video_path: Path, time_sec: float) -> bytes | None:
    """Extract a single JPEG frame from a video at time_sec. Returns raw bytes."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(time_sec),
        "-i", str(video_path),
        "-vframes", "1",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout if result.stdout else None
    except subprocess.CalledProcessError:
        return None


# ─── Main entry point ────────────────────────────────────────────────

def render_composition(
    request: EditorRenderRequest,
    src: Path,
    output_dir: Path,
    temp_dir: Path,
) -> dict:
    """
    Render a full composition from an EditorRenderRequest.

    Parameters
    ----------
    request    : the render request from the frontend
    src        : resolved absolute path to the source video
    output_dir : where to write the final output (usually output/cropped)
    temp_dir   : writable temporary directory for intermediate chunks

    Returns dict with { "status": "ok"|"error", "output": str, "error": str }
    """
    loop = asyncio.new_event_loop()
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Get source video duration ──
    _send(loop, 0, "Reading source video…")
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(src),
            ],
            capture_output=True, text=True, check=True,
        )
        duration = float(probe.stdout.strip())
    except Exception as e:
        return {"status": "error", "error": f"ffprobe failed: {e}"}

    # ── Build timeline ──
    timeline = _build_timeline(duration, request.segments, request.default_speaker_region)
    total_chunks = len(timeline)
    _send(loop, 2, f"Timeline has {total_chunks} chunks")

    chunk_paths: list[Path] = []
    failed_chunks: list[str] = []

    for idx, chunk in enumerate(timeline):
        pct = 5 + (idx / total_chunks) * 85
        c_start = chunk["start"]
        c_end = chunk["end"]
        chunk_out = temp_dir / f"chunk_{idx:04d}.mp4"

        if chunk["type"] == "speaker":
            _send(loop, pct, f"Chunk {idx+1}/{total_chunks}: speaker ({c_start:.1f}s–{c_end:.1f}s)")
            ok, err = _render_speaker_chunk(
                src, c_start, c_end,
                request.default_speaker_region,
                chunk_out,
                request.output_width, request.output_height,
            )
        else:
            seg: ContentSegment = chunk["segment"]
            _send(loop, pct, f"Chunk {idx+1}/{total_chunks}: {seg.layout} ({c_start:.1f}s–{c_end:.1f}s)")

            if seg.layout == "fullscreen":
                ok, err = _render_fullscreen_content_chunk(
                    src, c_start, c_end,
                    seg.content_region,
                    chunk_out,
                    request.output_width, request.output_height,
                )
            else:
                # split_top or split_bottom — need a speaker region
                speaker_region = seg.speaker_region or request.default_speaker_region
                ok, err = _render_split_chunk(
                    src, c_start, c_end,
                    seg.content_region,
                    speaker_region,
                    seg.layout,
                    chunk_out,
                    request.output_width, request.output_height,
                )

        if ok:
            chunk_paths.append(chunk_out)
        else:
            failed_chunks.append(f"chunk {idx}: {err}")

    if not chunk_paths:
        return {"status": "error", "error": "All chunks failed: " + "; ".join(failed_chunks)}

    # ── Determine output filename ──
    out_name = request.output_name or f"{src.stem}_edited.mp4"
    if not out_name.endswith(".mp4"):
        out_name += ".mp4"
    output_path = output_dir / out_name

    # ── Concat ──
    _send(loop, 91, f"Concatenating {len(chunk_paths)} chunks…")

    if len(chunk_paths) == 1:
        # Only one chunk → just copy/rename
        import shutil
        shutil.copy2(chunk_paths[0], output_path)
        ok, err = True, ""
    else:
        ok, err = _concat_chunks(chunk_paths, output_path)

    # ── Cleanup temp chunks ──
    for p in chunk_paths:
        try:
            p.unlink()
        except Exception:
            pass

    if not ok:
        return {"status": "error", "error": f"Concat failed: {err}"}

    _send(loop, 100, f"Done → {output_path.name}")
    loop.close()

    return {
        "status": "ok",
        "output": str(output_path),
        "output_name": output_path.name,
        "skipped_chunks": failed_chunks,
    }
