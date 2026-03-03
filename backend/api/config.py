"""
Config API — read/write app configuration.
"""

import json
from pathlib import Path

from fastapi import APIRouter

from backend.models import AppConfig, SubtitleStyle, TranscriptionConfig, CropConfig
from backend.services.cropper import DEFAULT_CROP_POSITIONS, DEFAULT_SPEAKER_MAPPING

router = APIRouter(prefix="/api/config", tags=["config"])

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config.json"


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    return {}


def _save_config(data: dict):
    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


@router.get("")
def get_config():
    """Return all configurable settings."""
    saved = _load_config()
    return {
        "transcription": saved.get("transcription", TranscriptionConfig().model_dump()),
        "subtitle_style": saved.get("subtitle_style", SubtitleStyle().model_dump()),
        "crop_positions": saved.get("crop_positions", DEFAULT_CROP_POSITIONS),
        "speaker_mapping": saved.get("speaker_mapping", DEFAULT_SPEAKER_MAPPING),
    }


@router.put("")
def update_config(body: dict):
    """Update configuration (partial update supported)."""
    current = _load_config()
    current.update(body)
    _save_config(current)
    return {"message": "Configuration saved"}
