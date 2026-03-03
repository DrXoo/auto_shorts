"""
Cropper service — crops horizontal video to vertical 9:16 with speaker-aware dynamic cropping.

Refactored from scripts/steps/3_crop_to_vertical.py.
All interactive input() calls removed; configuration is passed in as parameters.
"""

import asyncio
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from backend.models import CropConfig, CropRegion
from backend.ws import manager as ws_manager

# ── Defaults (match original script) ────────────────────────────────

DEFAULT_CROP_POSITIONS = {
    3: {
        'speakers': [
            {'x': 30, 'y': 30, 'width': 1180, 'height': 685},
            {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},
            {'x': 684, 'y': 715, 'width': 1180, 'height': 685},
        ],
        'content': {'x': 1728, 'y': 0, 'width': 810, 'height': 1440},
    },
    4: {
        'speakers': [
            {'x': 30, 'y': 30, 'width': 1180, 'height': 685},
            {'x': 1342, 'y': 32, 'width': 1180, 'height': 685},
            {'x': 30, 'y': 715, 'width': 1180, 'height': 685},
            {'x': 1342, 'y': 715, 'width': 1180, 'height': 685},
        ],
        'content': [
            {'x': 1600, 'y': 0, 'width': 900, 'height': 480},
            {'x': 1600, 'y': 480, 'width': 900, 'height': 480},
            {'x': 1600, 'y': 960, 'width': 900, 'height': 480},
            {'x': 1600, 'y': 960, 'width': 900, 'height': 480},
        ],
    },
    5: {
        'speakers': [
            {'x': 58, 'y': 169, 'width': 778, 'height': 437},
            {'x': 895, 'y': 160, 'width': 778, 'height': 437},
            {'x': 1726, 'y': 160, 'width': 778, 'height': 437},
            {'x': 436, 'y': 825, 'width': 778, 'height': 437},
            {'x': 1271, 'y': 818, 'width': 778, 'height': 437},
        ],
        'content': [
            {'x': 72, 'y': 58, 'width': 708, 'height': 398},
            {'x': 917, 'y': 58, 'width': 708, 'height': 398},
            {'x': 1777, 'y': 58, 'width': 708, 'height': 398},
            {'x': 1777, 'y': 518, 'width': 708, 'height': 398},
            {'x': 1777, 'y': 993, 'width': 708, 'height': 398},
        ],
    },
}

DEFAULT_SPEAKER_MAPPING = {
    3: {'SPEAKER_00': 0, 'SPEAKER_01': 1, 'SPEAKER_02': 2},
    4: {'SPEAKER_00': 0, 'SPEAKER_01': 1, 'SPEAKER_02': 2, 'SPEAKER_03': 3},
    5: {'SPEAKER_00': 0, 'SPEAKER_01': 1, 'SPEAKER_02': 2, 'SPEAKER_03': 3, 'SPEAKER_04': 4},
}

DEFAULT_AUTO_DETECT = {
    'enabled': True,
    'default': {
        'pixel_position': (82, 1156),
        'speakers_color': (0, 0, 0),
        'content_color': (0, 216, 217),
        'tolerance': 100,
    },
    'by_num_speakers': {
        5: {'pixel_position': (178, 1352), 'speakers_color': (0, 0, 7),
            'content_color': (23, 197, 200), 'tolerance': 100},
    },
}


# ── Helper functions (ported directly) ──────────────────────────────

def extract_frame(video_path: Path, time_sec: float = 5):
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-ss', str(time_sec), '-vframes', '1',
        '-f', 'image2pipe', '-pix_fmt', 'bgr24', '-vcodec', 'rawvideo', '-',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        probe_cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height', '-of', 'csv=p=0',
            str(video_path),
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        w, h = map(int, probe.stdout.strip().split(','))
        frame = np.frombuffer(result.stdout, dtype=np.uint8).reshape((h, w, 3))
        return frame
    except Exception:
        return None


def detect_crop_mode(video_file: Path, num_speakers: int, auto_detect_cfg: dict | None = None) -> str | None:
    cfg = auto_detect_cfg or DEFAULT_AUTO_DETECT
    if not cfg.get('enabled', True):
        return None

    base = cfg.get('default', {})
    override = cfg.get('by_num_speakers', {}).get(num_speakers, {})
    merged = {**base, **override}

    frame = extract_frame(video_file)
    if frame is None:
        return None

    x, y = merged['pixel_position']
    if y >= frame.shape[0] or x >= frame.shape[1]:
        return None

    pixel = frame[y, x]
    dist_s = np.linalg.norm(pixel - np.array(merged['speakers_color']))
    dist_c = np.linalg.norm(pixel - np.array(merged['content_color']))
    tol = merged.get('tolerance', 100)

    if dist_s < dist_c and dist_s < tol:
        return 'speakers'
    elif dist_c < dist_s and dist_c < tol:
        return 'content'
    return None


def get_clip_timestamps(clip_file: Path, clips_json_path: Path):
    if not clips_json_path.exists():
        return None
    match = re.search(r'clip_(\d+)', clip_file.stem)
    if not match:
        return None
    clip_number = int(match.group(1))
    try:
        with open(clips_json_path, 'r', encoding='utf-8') as f:
            clips_data = json.load(f)
        for clip in clips_data:
            if clip.get('clip_number') == clip_number:
                return (float(clip['start_time']), float(clip['end_time']))
    except Exception:
        pass
    return None


def analyze_speaker_timeline(transcript_path: Path, clip_start: float, clip_end: float):
    with open(transcript_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    segments = []
    current_speaker = None
    seg_start = None
    for seg in data.get('segments', []):
        for w in seg.get('words', []):
            ws, we, sp = w.get('start', 0), w.get('end', 0), w.get('speaker', 'UNKNOWN')
            if we < clip_start or ws > clip_end:
                continue
            adj_start = max(ws - clip_start, 0)
            if sp != current_speaker:
                if current_speaker is not None and seg_start is not None:
                    segments.append((seg_start, adj_start, current_speaker))
                current_speaker = sp
                seg_start = adj_start
    if current_speaker is not None and seg_start is not None:
        segments.append((seg_start, clip_end - clip_start, current_speaker))
    return segments


def calculate_speaker_activity(timeline, num_speakers, speaker_mapping):
    talk_time: dict[str, float] = defaultdict(float)
    for s, e, sp in timeline:
        talk_time[sp] += max(e - s, 0)
    all_speakers = sorted(speaker_mapping.keys())
    return sorted(all_speakers, key=lambda s: talk_time.get(s, 0), reverse=True), talk_time


def _build_vstack_filter(regions: list[dict], prefix: str = "v") -> str:
    """Build ffmpeg filter_complex for cropping multiple regions & vstacking."""
    crops = []
    for i, r in enumerate(regions):
        crops.append(f"[0:v]crop={r['width']}:{r['height']}:{r['x']}:{r['y']}[{prefix}{i}]")
    labels = ''.join(f"[{prefix}{i}]" for i in range(len(regions)))
    return ';'.join(crops) + f';{labels}vstack=inputs={len(regions)}[out]'


def _build_5speaker_grid_filter(crops: list[dict]) -> str:
    """Build 2×2+1 grid for 5-speaker layout."""
    parts = []
    for i, c in enumerate(crops[:5]):
        parts.append(f"[0:v]crop={c['width']}:{c['height']}:{c['x']}:{c['y']}[spk{i}]")

    return (
        ';'.join(parts) + ';'
        '[spk0]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top0];'
        '[spk1]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[top1];'
        '[top0][top1]hstack[top];'
        '[spk2]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid0];'
        '[spk3]scale=540:640:force_original_aspect_ratio=increase,crop=540:640,setsar=1[mid1];'
        '[mid0][mid1]hstack[mid];'
        '[spk4]crop=iw*8/9:ih:(iw-iw*8/9)/2:0,scale=1080:640:force_original_aspect_ratio=decrease,'
        'pad=1080:640:(ow-iw)/2:(oh-ih)/2,setsar=1[bottom];'
        '[top][mid][bottom]vstack=inputs=3[out]'
    )


# ── Main entry point ────────────────────────────────────────────────

def crop_videos(
    input_dir: Path,
    output_dir: Path,
    *,
    num_speakers: int = 3,
    scene_type: str | None = None,
    transcript_path: Path | None = None,
    clips_json_path: Path | None = None,
    crop_positions: dict | None = None,
    speaker_mapping: dict | None = None,
    dynamic_enabled: bool = True,
    speakers_shown: int = 3,
    auto_detect_cfg: dict | None = None,
) -> dict:
    """
    Crop all videos in *input_dir* to vertical format.

    Parameters
    ----------
    scene_type : 'speakers' | 'content' | None
        If None, auto-detect per video.
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    positions = crop_positions or DEFAULT_CROP_POSITIONS
    mapping = speaker_mapping or DEFAULT_SPEAKER_MAPPING

    config_for_n = positions.get(num_speakers, {})
    mapping_for_n = mapping.get(num_speakers, {})

    video_extensions = {'.mp4', '.mov', '.avi', '.mkv'}
    video_files = sorted(f for f in input_dir.iterdir()
                         if f.is_file() and f.suffix.lower() in video_extensions)

    loop = asyncio.new_event_loop()
    total = len(video_files)
    successful = 0
    failed = 0
    results: list[dict] = []

    for idx, vf in enumerate(video_files, 1):
        pct = (idx / total) * 100 if total else 100
        try:
            loop.run_until_complete(
                ws_manager.send_progress("crop", pct, f"Cropping {idx}/{total}: {vf.name}")
            )
        except Exception:
            pass

        # Determine scene type
        st = scene_type or detect_crop_mode(vf, num_speakers, auto_detect_cfg)
        if st is None:
            st = 'speakers'  # fallback

        output_file = output_dir / f"{vf.stem}_vertical{vf.suffix}"
        filter_complex = None
        single_crop = False

        if st == 'content':
            content_cfg = config_for_n.get('content')
            if content_cfg is None:
                results.append({"file": vf.name, "status": "skipped", "reason": "no content config"})
                continue

            if isinstance(content_cfg, dict):
                # Single crop (3 speakers content)
                x, y, w, h = content_cfg['x'], content_cfg['y'], content_cfg['width'], content_cfg['height']
                single_crop = True
            else:
                # Multi-position content
                if dynamic_enabled and num_speakers > 3 and transcript_path and clips_json_path:
                    ts = get_clip_timestamps(vf, clips_json_path)
                    if ts:
                        timeline = analyze_speaker_timeline(transcript_path, ts[0], ts[1])
                        if timeline:
                            sorted_spk, _ = calculate_speaker_activity(timeline, num_speakers, mapping_for_n)
                            if num_speakers == 5:
                                positions_idx = [mapping_for_n.get(s, i) for i, s in enumerate(sorted_spk)]
                                crop_list = [content_cfg[p] for p in positions_idx[:5] if p < len(content_cfg)]
                                while len(crop_list) < 5:
                                    crop_list.append(content_cfg[len(crop_list) % len(content_cfg)])
                                filter_complex = _build_5speaker_grid_filter(crop_list)
                            else:
                                positions_idx = [mapping_for_n.get(s, i % len(content_cfg)) for i, s in enumerate(sorted_spk[:3])]
                                crop_list = [content_cfg[p] for p in positions_idx if p < len(content_cfg)]
                                while len(crop_list) < 3:
                                    crop_list.append(content_cfg[len(crop_list) % len(content_cfg)])
                                filter_complex = _build_vstack_filter(crop_list[:3])

                if filter_complex is None:
                    regions = content_cfg[:3] if isinstance(content_cfg, list) else [content_cfg]
                    filter_complex = _build_vstack_filter(regions)
        else:
            # speakers scene
            speaker_pos = config_for_n.get('speakers', [])
            if not speaker_pos:
                results.append({"file": vf.name, "status": "skipped", "reason": "no speakers config"})
                continue

            if num_speakers <= 3 or not dynamic_enabled:
                regions = speaker_pos[:min(num_speakers, 3)]
                filter_complex = _build_vstack_filter(regions)
            else:
                # Dynamic: use transcript
                if transcript_path and clips_json_path:
                    ts = get_clip_timestamps(vf, clips_json_path)
                    if ts:
                        timeline = analyze_speaker_timeline(transcript_path, ts[0], ts[1])
                        if timeline:
                            sorted_spk, _ = calculate_speaker_activity(timeline, num_speakers, mapping_for_n)
                            if num_speakers == 5:
                                positions_idx = [mapping_for_n.get(s, i) for i, s in enumerate(sorted_spk)]
                                crop_list = [speaker_pos[p] for p in positions_idx[:5] if p < len(speaker_pos)]
                                while len(crop_list) < 5:
                                    crop_list.append(speaker_pos[len(crop_list) % len(speaker_pos)])
                                filter_complex = _build_5speaker_grid_filter(crop_list)
                            else:
                                positions_idx = [mapping_for_n.get(s, i) for i, s in enumerate(sorted_spk[:3])]
                                crop_list = [speaker_pos[p] for p in positions_idx if p < len(speaker_pos)]
                                while len(crop_list) < 3:
                                    crop_list.append(speaker_pos[len(crop_list) % len(speaker_pos)])
                                filter_complex = _build_vstack_filter(crop_list[:3])

                if filter_complex is None:
                    filter_complex = _build_vstack_filter(speaker_pos[:3])

        # Build ffmpeg command
        if single_crop:
            cmd = ['ffmpeg', '-i', str(vf), '-vf', f'crop={w}:{h}:{x}:{y}',
                   '-c:a', 'copy', '-y', str(output_file)]
        else:
            cmd = ['ffmpeg', '-i', str(vf), '-filter_complex', filter_complex,
                   '-map', '[out]', '-map', '0:a', '-c:a', 'copy', '-y', str(output_file)]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                successful += 1
                results.append({"file": output_file.name, "status": "ok"})
            else:
                failed += 1
                results.append({"file": vf.name, "status": "error", "error": res.stderr[:300]})
        except Exception as e:
            failed += 1
            results.append({"file": vf.name, "status": "error", "error": str(e)})

    try:
        loop.run_until_complete(
            ws_manager.send_complete("crop", f"Cropped {successful}/{total} videos")
        )
    except Exception:
        pass
    loop.close()

    return {"successful": successful, "failed": failed, "total": total, "results": results}


def generate_crop_preview(video_path: Path, num_speakers: int = 3,
                          crop_positions: dict | None = None,
                          time_sec: float = 5) -> bytes | None:
    """
    Extract a frame from *video_path* and return it as raw PNG bytes
    with crop rectangles drawn on it. Used for the web preview.
    """
    import io
    frame = extract_frame(video_path, time_sec)
    if frame is None:
        return None

    positions = (crop_positions or DEFAULT_CROP_POSITIONS).get(num_speakers, {})
    speaker_rects = positions.get('speakers', [])

    # Draw rectangles
    colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0), (255, 0, 255)]
    for i, rect in enumerate(speaker_rects):
        x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
        color = colors[i % len(colors)]
        # Draw rectangle border (3 px)
        frame[y:y+3, x:x+w] = color
        frame[y+h-3:y+h, x:x+w] = color
        frame[y:y+h, x:x+3] = color
        frame[y:y+h, x+w-3:x+w] = color

    # Encode as PNG
    try:
        import cv2
        _, buf = cv2.imencode('.png', frame)
        return buf.tobytes()
    except ImportError:
        # Fallback: return raw for now
        return frame.tobytes()
