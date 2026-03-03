"""
AutoShorts Web — FastAPI application entry point.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from backend.api import pipeline, transcript, clips, media, tools, config
from backend.ws import manager as ws_manager

PROJECT_ROOT = Path(__file__).parent.parent

app = FastAPI(
    title="AutoShorts",
    description="Podcast → Short Video automation pipeline",
    version="2.0.0",
)

# CORS for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(pipeline.router)
app.include_router(transcript.router)
app.include_router(clips.router)
app.include_router(media.router)
app.include_router(tools.router)
app.include_router(config.router)


# ─── WebSocket ──────────────────────────────────────────────────────

@app.websocket("/api/ws/progress")
async def websocket_progress(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive — client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


# ─── Health check ───────────────────────────────────────────────────

@app.get("/api/health")
def health():
    import shutil
    ffmpeg_ok = shutil.which("ffmpeg") is not None

    gpu_ok = False
    try:
        import torch
        gpu_ok = torch.cuda.is_available()
    except Exception:
        pass

    return {
        "status": "ok",
        "ffmpeg": ffmpeg_ok,
        "gpu": gpu_ok,
        "project_root": str(PROJECT_ROOT),
    }
