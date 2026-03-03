"""
Pydantic models for the AutoShorts web application.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ─── Transcript Models ───────────────────────────────────────────────

class WordData(BaseModel):
    word: str
    start: float
    end: float
    score: float = 0.0
    speaker: str = "UNKNOWN"


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[WordData] = []


class Transcript(BaseModel):
    segments: list[TranscriptSegment]


class SpeakerInfo(BaseModel):
    speaker_id: str
    word_count: int = 0
    total_talk_time: float = 0.0
    segment_count: int = 0


class SpeakerRenameRequest(BaseModel):
    old_name: str
    new_name: str


class SpeakerBulkRenameRequest(BaseModel):
    """Merge one speaker into another (e.g. fix misdetected speakers)"""
    source_speaker: str
    target_speaker: str


class SegmentSpeakerUpdate(BaseModel):
    speaker: str


# ─── Clip Models ─────────────────────────────────────────────────────

class ClipData(BaseModel):
    clip_number: int
    title: str
    start_time: float
    end_time: float
    duration_seconds: Optional[float] = None
    speakers: Optional[list[str]] = None
    description: Optional[str] = None
    viral_potential: Optional[str] = None
    why_viral: Optional[str] = None
    hook: Optional[str] = None


class ClipsUpdateRequest(BaseModel):
    clips: list[ClipData]


# ─── Hook Models ─────────────────────────────────────────────────────

class HookData(BaseModel):
    hook_number: int
    type: Optional[str] = None
    title: str
    start_time: float
    end_time: float
    duration: Optional[float] = None
    text: Optional[str] = None
    reason: Optional[str] = None
    energy_level: Optional[str] = None


# ─── Pipeline Models ─────────────────────────────────────────────────

class PipelineStep(str, Enum):
    TRANSCRIBE = "transcribe"
    AI_ANALYSIS = "ai_analysis"
    EXTRACT = "extract"
    CROP = "crop"
    SUBTITLE = "subtitle"


class PipelineState(BaseModel):
    completed_steps: list[int] = []
    last_run: Optional[str] = None


class PipelineStepStatus(BaseModel):
    step: int
    name: str
    status: str  # "pending", "completed", "running", "error"
    description: str = ""


class PipelineStatus(BaseModel):
    steps: list[PipelineStepStatus]
    input_video: Optional[str] = None
    input_video_duration: Optional[float] = None
    has_transcript: bool = False
    has_clips_json: bool = False
    output_counts: dict[str, int] = {}


# ─── Crop Configuration Models ───────────────────────────────────────

class CropRegion(BaseModel):
    x: int
    y: int
    width: int
    height: int


class CropPositions(BaseModel):
    speakers: list[CropRegion] = []
    content: list[CropRegion] | CropRegion | None = None


class SpeakerMappingEntry(BaseModel):
    speaker_id: str
    position_index: int


class DynamicCropConfig(BaseModel):
    enabled: bool = True
    speakers_shown: int = 3
    transition_duration: float = 0.5
    min_segment_duration: float = 2.0


class AutoDetectPixelConfig(BaseModel):
    pixel_position: tuple[int, int] = (82, 1156)
    speakers_color: tuple[int, int, int] = (0, 0, 0)
    content_color: tuple[int, int, int] = (0, 216, 217)
    tolerance: int = 100


class AutoDetectConfig(BaseModel):
    enabled: bool = True
    default: AutoDetectPixelConfig = AutoDetectPixelConfig()
    by_num_speakers: dict[int, AutoDetectPixelConfig] = {}


class CropConfig(BaseModel):
    num_speakers: int = 3
    scene_type: Optional[str] = None  # 'speakers', 'content', or None for auto
    crop_positions: dict[int, CropPositions] = {}
    speaker_mapping: dict[int, dict[str, int]] = {}
    dynamic_config: DynamicCropConfig = DynamicCropConfig()
    auto_detect: AutoDetectConfig = AutoDetectConfig()


# ─── Subtitle Configuration Models ───────────────────────────────────

class SubtitleStyle(BaseModel):
    font_name: str = "Montserrat"
    font_size: int = 80
    primary_color: str = "&H00FFFFFF"     # White (ASS BGR)
    secondary_color: str = "&H0000FFFF"   # Yellow (karaoke highlight)
    outline_color: str = "&H00000000"     # Black
    back_color: str = "&H80000000"
    bold: bool = True
    outline: int = 5
    shadow: int = 2
    alignment: int = 2
    margin_v: int = 461
    margin_l: int = 10
    margin_r: int = 10
    play_res_x: int = 810
    play_res_y: int = 1440
    max_words_per_chunk: int = 4
    pause_threshold: float = 0.3


# ─── Transcription Configuration ─────────────────────────────────────

class TranscriptionConfig(BaseModel):
    language: str = "es"
    model_name: str = "large-v3"
    batch_size: int = 32
    compute_type: str = "float16"
    device: str = "cuda"


# ─── AI Analysis Configuration ───────────────────────────────────────

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class AIAnalysisConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    prompt_type: str = "clips"  # "clips" or "hooks"


class AIAnalysisRequest(BaseModel):
    config: AIAnalysisConfig
    transcript_text: Optional[str] = None  # If None, uses saved transcript


# ─── Tool Configurations ─────────────────────────────────────────────

class CutVideoRequest(BaseModel):
    video_path: str
    start_time: float
    end_time: float
    output_name: Optional[str] = None
    output_to_input: bool = False


class AddMusicRequest(BaseModel):
    video_path: str
    music_path: str
    output_name: Optional[str] = None
    music_db: float = -37.0
    fade_in: float = 5.0
    start_delay_seconds: float = 0.0
    audio_bitrate: str = "192k"
    output_to_input: bool = False


class HooksCompilationRequest(BaseModel):
    transition: str = "fade"
    music_path: Optional[str] = None
    music_volume: float = 0.3
    max_duration: Optional[float] = None


# ─── App Configuration ───────────────────────────────────────────────

class AppConfig(BaseModel):
    transcription: TranscriptionConfig = TranscriptionConfig()
    crop: CropConfig = CropConfig()
    subtitle_style: SubtitleStyle = SubtitleStyle()


# ─── Progress / WebSocket Models ─────────────────────────────────────

class ProgressMessage(BaseModel):
    type: str = "progress"            # "progress", "log", "error", "complete"
    step: Optional[str] = None        # Which pipeline step
    percent: Optional[float] = None   # 0-100
    message: str = ""
    data: Optional[dict] = None


# ─── Media / File Models ─────────────────────────────────────────────

class FileInfo(BaseModel):
    name: str
    path: str
    size: int = 0
    duration: Optional[float] = None


class VideoInfo(BaseModel):
    name: str
    path: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    codec: Optional[str] = None
    size: int = 0
