# AutoShorts 🎬

Web-based application to convert podcast videos into vertical shorts ready for Instagram, TikTok, and YouTube Shorts. Features a **Next.js frontend** and **FastAPI backend** with real-time progress via WebSockets.

## Quick Start

```bash
# 1. Create Python venv & install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Launch both servers
start.bat
```

This opens:
- **Frontend** → http://localhost:3000
- **Backend API** → http://localhost:8000
- **API Docs** → http://localhost:8000/docs

## Pipeline Overview

```
Upload / Select Input Video
         ↓
  [1] Transcribe (WhisperX + diarization)
         ↓
  [2] AI Analysis → clips.json (external LLM or built-in)
         ↓
  [3] Extract Clips
         ↓
  [4] Crop to Vertical (9:16)
         ↓
  [5] Add Karaoke Subtitles
         ↓
  View & Download in Shorts page 🎉
```

All steps are run and monitored from the web UI. Each step can be triggered independently.

## Web Interface Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Input video management (upload, star active, delete), pipeline progress overview, quick stats |
| **Pipeline** | Run each step with configuration panels, select which input video to process, real-time progress bars |
| **Transcript** | View and edit transcription segments, fix speaker labels, bulk rename speakers, preview video |
| **Clips** | Edit `clips.json` clip list, generate clips via LLM, inline transcript editing per clip |
| **Tools** | Cut video (h:m:s input), add background music, clean output — with option to save results back to input |
| **Shorts** | Browse all final videos, click to preview/play, download, regenerate subtitles per video |

## Features

- **🌐 Web UI** — Full control from the browser, no terminal needed for normal workflow
- **📂 Multi-Video Input** — Upload multiple videos, star the active one, switch per pipeline step
- **🎙️ Speaker-Aware Dynamic Cropping** — Shows 3 speakers at a time for 4-5 person episodes based on who's talking
- **🎯 Speaker Diarization** — WhisperX automatically identifies different speakers
- **🤖 AI Clip Selection** — Generate clips.json via built-in LLM integration or paste from external AI
- **📱 Vertical Format** — 9:16 output for Reels, TikTok, Shorts
- **📝 Karaoke Subtitles** — Word-by-word highlighting, fully configurable style
- **🔄 Per-Video Subtitle Regen** — Regenerate subtitles for a single final video after transcript edits
- **✂️ Pre-Processing Tools** — Cut video segments, add background music before running the pipeline
- **📡 Real-Time Progress** — WebSocket-based progress bars for all long-running operations
- **⚡ GPU-Accelerated** — CUDA-powered transcription via WhisperX

## Architecture

```
autoshorts/
├── start.bat                     # Launch backend + frontend
├── backend/                      # Python FastAPI server
│   ├── main.py                   # App entry point, CORS, router mounts
│   ├── models.py                 # Pydantic models for all API types
│   ├── ws.py                     # WebSocket manager for progress
│   ├── requirements.txt          # Python dependencies
│   ├── api/                      # API route modules
│   │   ├── pipeline.py           # Pipeline steps, status, input video management
│   │   ├── transcript.py         # Transcript CRUD, speaker management
│   │   ├── clips.py              # Clips CRUD, LLM generation, prompt templates
│   │   ├── media.py              # File upload, video serving, thumbnails
│   │   ├── tools.py              # Cut video, add music, clean output
│   │   └── config.py             # App configuration
│   └── services/                 # Core processing logic
│       ├── transcriber.py        # WhisperX transcription + diarization
│       ├── ai_analyzer.py        # LLM-based clip analysis
│       ├── clip_extractor.py     # FFmpeg clip extraction
│       ├── cropper.py            # 9:16 cropping with speaker tracking
│       ├── subtitler.py          # ASS subtitle generation + burning
│       └── utils.py              # FFmpeg wrappers (cut, music, info)
├── frontend/                     # Next.js 16 + React 19 + Tailwind
│   ├── app/                      # Pages (file-based routing)
│   │   ├── page.tsx              # Dashboard
│   │   ├── pipeline/page.tsx     # Pipeline runner
│   │   ├── transcript/page.tsx   # Transcript editor
│   │   ├── clips/page.tsx        # Clips editor
│   │   ├── tools/page.tsx        # Pre-processing tools
│   │   └── shorts/page.tsx       # Final video gallery
│   ├── components/               # Shared UI components
│   │   ├── Sidebar.tsx           # Navigation sidebar
│   │   ├── VideoPlayer.tsx       # Video player + upload zone
│   │   ├── CropPreview.tsx       # Crop position preview
│   │   └── ProgressBar.tsx       # Progress indicator
│   └── lib/                      # Client utilities
│       ├── api.ts                # Typed API client for all endpoints
│       └── useWebSocket.ts       # WebSocket hook for real-time progress
├── input/                        # Source videos (upload via UI or drop here)
├── output/
│   ├── transcripts/              # Transcription JSON + text files
│   ├── ai_analysis/              # clips.json (generated or manual)
│   ├── extracted/                # Raw extracted clips
│   ├── cropped/                  # Vertical format clips
│   └── final/                    # Final subtitled videos
├── scripts/                      # Standalone utility scripts (optional)
│   ├── steps/                    # Original CLI pipeline steps
│   └── utils/                    # Trending topics, hooks, helpers
├── clip_extraction_prompt.txt    # Prompt template for clip analysis
└── hook_extraction_prompt.txt    # Prompt template for hooks analysis
```

## Workflow

1. **Upload your video** — Drag & drop on Dashboard or place in `input/`
2. **Star the active video** — If you have multiple, star the one to process
3. **Pre-process (optional)** — Use Tools page to cut segments or add music, save back to input
4. **Run Pipeline** — Go to Pipeline page, run steps 1 through 4 in order
5. **AI Analysis** — After transcription, generate clips via built-in LLM or paste from external AI on Clips page
6. **Review & Edit** — Edit transcript speakers, adjust clip timings, tweak as needed
7. **View Shorts** — Browse final videos on Shorts page, play in-browser, download

## Step 2: AI Analysis

After transcription, provide `output/ai_analysis/clips.json`. You can:

- **Use the Clips page** — Paste a prompt into your LLM, paste the response back, or use built-in generation
- **Manually create** the file with this format:

```json
[
  {
    "clip_number": 1,
    "title": "Amazing Discussion About AI",
    "start_time": "2:30",
    "end_time": "3:15"
  }
]
```

## API Endpoints

The backend exposes a REST API (see full docs at http://localhost:8000/docs):

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pipeline/status` | Pipeline state + output counts |
| GET | `/api/pipeline/input-videos` | List input videos with metadata |
| POST | `/api/pipeline/run/transcribe` | Start transcription |
| POST | `/api/pipeline/run/extract` | Extract clips from video |
| POST | `/api/pipeline/run/crop` | Crop to 9:16 vertical |
| POST | `/api/pipeline/run/subtitle` | Add subtitles to all clips |
| POST | `/api/pipeline/run/subtitle/{file}` | Regenerate subtitles for one video |
| GET | `/api/transcript` | Get transcript JSON |
| POST | `/api/transcript/save` | Save edited transcript |
| GET/PUT | `/api/clips` | Get or update clips list |
| POST | `/api/clips/generate` | Generate clips via LLM |
| POST | `/api/tools/cut-video` | Cut a video segment |
| POST | `/api/tools/add-music` | Mix background music |
| GET | `/api/media/list/{stage}` | List files in a pipeline stage |
| GET | `/api/media/file/{stage}/{name}` | Stream a video file |
| WS | `/ws` | Real-time progress updates |

## Requirements

- **Python 3.10+** with a virtual environment
- **Node.js 18+** and npm
- **FFmpeg** installed and on PATH
- **CUDA-capable GPU** recommended (for WhisperX transcription)

### Python Dependencies

```
fastapi, uvicorn, python-multipart, websockets,
openai, anthropic, pydantic, aiofiles
+ whisperx (with torch CUDA)
```

### Speaker-Aware Cropping

For episodes with 4-5 speakers, the system dynamically shows the 3 most relevant speakers at any moment. See [SPEAKER_CONFIG_GUIDE.md](SPEAKER_CONFIG_GUIDE.md) for configuration.

### Hooks Compilation

Create teaser/intro videos from the most engaging moments. See [HOOKS_FEATURE_GUIDE.md](HOOKS_FEATURE_GUIDE.md) for details.

## Legacy CLI

The original standalone scripts in `scripts/` still work if you prefer CLI:

```bash
python run_pipeline.py                 # Run full pipeline
python run_pipeline.py --from-step 3   # Resume from step 3
python run_pipeline.py --reset         # Reset pipeline state
```

## Output

Final videos in `output/final/` are:
- ✅ Vertical 9:16 (810×1440)
- ✅ Karaoke-style subtitles
- ✅ Optimized for mobile
- ✅ Ready to upload

---

Made with ❤️ for content creators
