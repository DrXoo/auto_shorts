# AutoShorts — Copilot Instructions

## What This Project Does
Converts podcast videos into vertical short-form clips (9:16) for Instagram/TikTok/YouTube Shorts.
A **Next.js 15 frontend** talks to a **FastAPI backend** via REST + WebSockets.

## Running Locally
```bat
start.bat          # Opens backend (port 8000) + frontend (port 3000) in separate cmd windows
```
Backend only: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`  
Frontend only: `cd frontend && npm run dev`  
API docs: http://localhost:8000/docs

## Architecture Overview
```
input/              ← source videos (upload via UI or drop files here)
output/
  transcripts/      ← *_transcript.json (segments + per-word speaker labels)
  ai_analysis/      ← clips.json
  extracted/        ← raw FFmpeg-cut clips
  cropped/          ← vertical 9:16 clips
  final/            ← subtitled final videos
  pipeline_state.json  ← step completion tracking
```

Pipeline steps (always run in order): **Transcribe → AI Analysis → Extract → Crop → Subtitle**

## Key Patterns

### Adding a new backend feature
1. Add Pydantic request/response models to `backend/models.py`
2. Add the route to the relevant `backend/api/*.py` router (prefix already set on the router)
3. Import the model in that router file — all models are in one flat file
4. If it's a long-running operation, run it in a background thread and push progress via `ws_manager.send_progress(step, percent, message)` (see `backend/api/pipeline.py`)
5. Do **not** create new router files — use the existing six: `pipeline`, `transcript`, `clips`, `media`, `tools`, `config`

### Adding a new frontend API call
All API calls live in `frontend/lib/api.ts` as typed methods grouped by domain (`pipeline`, `transcript`, `clips`, `media`). Add new methods there — never use raw `fetch` elsewhere. Every call goes through the shared `request<T>()` helper which handles base URL and error throwing.

### Real-time progress flow
Backend → `await ws_manager.send_progress(step, percent, msg)` (from any async context) or `asyncio.run(ws_manager.send_progress(...))` from sync threads. Frontend → `useWebSocket()` hook (`frontend/lib/useWebSocket.ts`) exposes `lastEvent` and `logs[]`.

### Transcript data shape
The canonical transcript file is `output/transcripts/*_transcript.json`:
```json
{ "segments": [{ "start": 0.0, "end": 2.5, "text": "...", "speaker": "SPEAKER_00",
    "words": [{ "word": "hello", "start": 0.0, "end": 0.4, "score": 0.9, "speaker": "SPEAKER_00" }] }] }
```
Words carry their own speaker label (can differ from segment-level speaker — see Fix Consistency). Transcript edits always go through `POST /api/transcript/save` or the specific mutation endpoints.

### Multi-video support
The active video is **not** stored server-side; the frontend stores it in `localStorage` under `"autoshorts_active_video"` and passes `?video_name=<name>` to pipeline run endpoints. `pipeline.py` uses `_find_video(name)` to resolve it.

### Path resolution convention
Every backend file resolves `PROJECT_ROOT` as:
```python
PROJECT_ROOT = Path(__file__).parent.parent.parent  # from backend/api/
PROJECT_ROOT = Path(__file__).parent.parent          # from backend/
```
Never hardcode paths — always derive from `PROJECT_ROOT`.

### Background pipeline tasks
Long steps (transcribe, extract, crop, subtitle) are launched via `Thread(target=..., daemon=True).start()` — **not** FastAPI `BackgroundTasks` — because they need to run after the HTTP response returns. Progress is pushed over WebSocket inside the thread using `asyncio.run(ws_manager.send_progress(...))`.

## Tech Stack
| Layer | Stack |
|---|---|
| Frontend | Next.js 15, React 19, Tailwind CSS, Lucide icons, `"use client"` pages |
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| ML | WhisperX (ASR), pyannote (diarization), CUDA/float16 |
| Video | FFmpeg (all cutting, cropping, subtitle burning) |
| Subtitles | ASS format generated in `services/subtitler.py` |

## Important Files
- `backend/models.py` — single source of truth for all Pydantic types
- `backend/ws.py` — `ConnectionManager` singleton (`manager`) imported everywhere as `ws_manager`
- `frontend/lib/api.ts` — all typed API calls; also exports TS interfaces mirroring backend models
- `frontend/lib/useWebSocket.ts` — real-time progress hook
- `output/pipeline_state.json` — tracks which steps are complete (read by `/api/pipeline/status`)
