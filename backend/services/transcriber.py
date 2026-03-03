"""
Transcription service — wraps whisperx for ASR + diarization.

Refactored from scripts/steps/1_transcribe.py.
All hardcoded values are now parameters with sensible defaults.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, Optional

from backend.ws import manager as ws_manager


async def _send(step: str, percent: float, msg: str):
    await ws_manager.send_progress(step, percent, msg)


def transcribe(
    video_path: Path,
    output_dir: Path,
    *,
    language: str = "es",
    model_name: str = "large-v3",
    batch_size: int = 32,
    compute_type: str = "float16",
    device: str = "cuda",
    hf_token: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    Run full transcription pipeline: ASR → alignment → diarization.

    Returns the transcript dict with segments and per-word speaker labels.
    Also writes three files into *output_dir*:
        <stem>_transcript.json
        <stem>_transcript.txt
        <stem>_transcript_detailed.txt
    """
    import torch

    # Monkey-patch torch.load for pyannote compatibility
    _original = torch.load

    def _patched(f, map_location=None, pickle_module=None, *, weights_only=None, mmap=None, **kw):
        return _original(f, map_location=map_location, pickle_module=pickle_module,
                         weights_only=False, mmap=mmap, **kw)

    torch.load = _patched

    import whisperx
    from whisperx.diarize import DiarizationPipeline

    loop = asyncio.new_event_loop()

    def _progress(pct: float, msg: str):
        if progress_callback:
            progress_callback(pct, msg)
        try:
            loop.run_until_complete(_send("transcribe", pct, msg))
        except Exception:
            pass

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem

    # Resolve HF token
    if not hf_token:
        from dotenv import load_dotenv
        load_dotenv()
        hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        raise ValueError("HF_TOKEN is required for speaker diarization")

    # Step 1: Load model & transcribe
    _progress(5, "Loading Whisper model…")
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=language)

    _progress(10, "Loading audio…")
    audio = whisperx.load_audio(str(video_path))

    _progress(15, "Transcribing audio…")
    result = model.transcribe(audio, batch_size=batch_size, language=language)
    _progress(40, "Transcription complete")

    # Step 2: Align
    _progress(45, "Aligning word-level timestamps…")
    model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
    result = whisperx.align(
        result["segments"], model_a, metadata, audio, device,
        return_char_alignments=False,
    )
    _progress(65, "Alignment complete")

    # Step 3: Diarize
    _progress(70, "Performing speaker diarization…")
    diarize_model = DiarizationPipeline(use_auth_token=hf_token, device=device)
    diarize_segments = diarize_model(audio)
    result = whisperx.assign_word_speakers(diarize_segments, result)
    _progress(90, "Diarization complete")

    # Save outputs
    _progress(92, "Saving transcript files…")
    transcript = {"segments": result["segments"]}

    # JSON
    json_path = output_dir / f"{stem}_transcript.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    # Human-readable text
    txt_path = output_dir / f"{stem}_transcript.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        current_speaker = None
        for seg in result["segments"]:
            speaker = seg.get("speaker", "Unknown")
            if speaker != current_speaker:
                f.write(f"\n{speaker}:\n")
                current_speaker = speaker
            f.write(f"{seg['text']}\n")

    # Detailed text
    det_path = output_dir / f"{stem}_transcript_detailed.txt"
    with open(det_path, "w", encoding="utf-8") as f:
        for seg in result["segments"]:
            speaker = seg.get("speaker", "Unknown")
            f.write(f"[{seg['start']:.2f}s - {seg['end']:.2f}s] {speaker}: {seg['text']}\n")

    _progress(100, "Transcription pipeline finished")
    loop.close()

    speakers = sorted({seg.get("speaker", "Unknown") for seg in result["segments"]})
    return {
        "transcript_path": str(json_path),
        "speakers": speakers,
        "segment_count": len(result["segments"]),
    }
