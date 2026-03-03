"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Mic,
  Scissors,
  Crop,
  Type,
  Play,
  CheckCircle2,
  Circle,
  Loader2,
  RotateCcw,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { pipeline, PipelineStatus, PipelineStepStatus, InputVideoInfo } from "@/lib/api";
import { useWebSocket } from "@/lib/useWebSocket";
import { ProgressBar, LogPanel } from "@/components/ProgressBar";

const STEP_ICONS = [Mic, Scissors, Crop, Type];
const STEP_LABELS = ["Transcribe", "Extract Clips", "Crop to Vertical", "Add Subtitles"];
// Backend step numbers: 1=Transcribe, 2=AI Analysis (external), 3=Extract, 4=Crop, 5=Subtitles
// Frontend display steps 1-4 map to backend steps:
const BACKEND_STEP = [1, 3, 4, 5];

interface StepConfig {
  // transcribe
  language?: string;
  model_name?: string;
  batch_size?: number;
  compute_type?: string;
  // crop
  num_speakers?: number;
  scene_type?: string;
  dynamic_enabled?: boolean;
  // subtitle style
  font_name?: string;
  font_size?: number;
  primary_color?: string;
  karaoke_color?: string;
}

export default function PipelinePage() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<number | null>(null);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [inputVideos, setInputVideos] = useState<InputVideoInfo[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const ws = useWebSocket();

  // Configs per step
  const [transcribeConfig, setTranscribeConfig] = useState<StepConfig>({
    language: "es",
    model_name: "large-v3",
    batch_size: 32,
    compute_type: "float16",
  });
  const [cropConfig, setCropConfig] = useState<StepConfig>({
    num_speakers: 3,
    dynamic_enabled: true,
  });
  const [subtitleConfig, setSubtitleConfig] = useState<StepConfig>({
    font_name: "Montserrat",
    font_size: 80,
    primary_color: "&H00FFFFFF",
    karaoke_color: "&H0000FFFF",
  });

  const refresh = useCallback(async () => {
    try {
      const [s, videos] = await Promise.all([
        pipeline.status(),
        pipeline.listInputVideos(),
      ]);
      setStatus(s);
      setInputVideos(videos);
      // Restore selected video from localStorage or use first
      const saved = localStorage.getItem("autoshorts_active_video");
      if (saved && videos.some((v) => v.name === saved)) {
        setSelectedVideo(saved);
      } else if (videos.length > 0) {
        setSelectedVideo(videos[0].name);
      }
    } catch { /* backend off */ }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  // Watch for WS complete events
  useEffect(() => {
    if (ws.lastEvent?.type === "complete") {
      setRunning(null);
      refresh();
    }
    if (ws.lastEvent?.type === "error") {
      setRunning(null);
    }
  }, [ws.lastEvent, refresh]);

  const runStep = async (step: number) => {
    setRunning(step);
    ws.clearLogs();
    try {
      const videoName = selectedVideo || undefined;
      switch (step) {
        case 1:
          await pipeline.runTranscribe(transcribeConfig as Record<string, unknown>, videoName);
          break;
        case 2:
          await pipeline.runExtract(videoName);
          break;
        case 3:
          await pipeline.runCrop({
            num_speakers: cropConfig.num_speakers ?? 3,
            scene_type: cropConfig.scene_type,
            dynamic_enabled: cropConfig.dynamic_enabled,
          });
          break;
        case 4:
          await pipeline.runSubtitle(subtitleConfig as Record<string, unknown>);
          break;
      }
    } catch (e: unknown) {
      setRunning(null);
    }
  };

  const handleReset = async () => {
    if (!confirm("Reset pipeline state? Output files will be cleaned.")) return;
    await pipeline.reset();
    refresh();
  };

  const stepStatus = (step: number): PipelineStepStatus | undefined =>
    status?.steps.find((s) => s.step === BACKEND_STEP[step - 1]);

  const canRun = (step: number): boolean => {
    if (running !== null) return false;
    if (!selectedVideo) return false;
    if (step === 1) return true;
    // Step 2 (Extract) requires clips.json to exist
    if (step === 2 && !status?.has_clips_json) return false;
    // Step N requires step N-1 completed
    const prev = stepStatus(step - 1);
    return prev?.status === "completed";
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Pipeline</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Run each step individually with custom settings
          </p>
        </div>
        <button
          onClick={handleReset}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--error)" }}
        >
          <RotateCcw size={14} /> Reset
        </button>
      </div>

      {!selectedVideo && !loading && inputVideos.length === 0 && (
        <div className="rounded-lg p-4 text-sm text-center"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--muted)" }}>
          Upload a video on the Dashboard before running the pipeline.
        </div>
      )}

      {/* Video Selector */}
      {inputVideos.length > 0 && (
        <div className="rounded-lg p-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <label className="block">
            <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>
              Input Video for Pipeline
            </span>
            <select
              value={selectedVideo || ""}
              onChange={(e) => {
                setSelectedVideo(e.target.value);
                localStorage.setItem("autoshorts_active_video", e.target.value);
              }}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            >
              {inputVideos.map((v) => (
                <option key={v.name} value={v.name}>
                  {v.name} {v.duration ? `(${Math.floor(v.duration / 60)}:${String(Math.floor(v.duration % 60)).padStart(2, "0")})` : ""}
                </option>
              ))}
            </select>
          </label>
          {inputVideos.length > 1 && (
            <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
              You can run each step with a different video. E.g., transcribe without music first, then switch to the version with background music for extraction.
            </p>
          )}
        </div>
      )}

      {/* Steps */}
      {[1, 2, 3, 4].map((step) => {
        const Icon = STEP_ICONS[step - 1];
        const ss = stepStatus(step);
        const isRunning = running === step;
        const isExpanded = expandedStep === step;
        const completed = ss?.status === "completed";

        return (
          <div
            key={step}
            className="rounded-lg overflow-hidden"
            style={{
              background: "var(--card)",
              border: `1px solid ${isRunning ? "var(--accent)" : "var(--border)"}`,
            }}
          >
            {/* Step header */}
            <div
              className="flex items-center gap-3 p-4 cursor-pointer select-none"
              onClick={() => setExpandedStep(isExpanded ? null : step)}
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center"
                style={{
                  background: completed ? "rgba(34,197,94,0.15)" : isRunning ? "rgba(99,102,241,0.15)" : "var(--background)",
                }}
              >
                {isRunning ? (
                  <Loader2 size={16} className="animate-spin" style={{ color: "var(--accent)" }} />
                ) : completed ? (
                  <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
                ) : (
                  <Icon size={16} style={{ color: "var(--muted)" }} />
                )}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">
                  Step {step}: {STEP_LABELS[step - 1]}
                </p>
                <p className="text-xs" style={{ color: step === 2 && !status?.has_clips_json && !completed ? "var(--error)" : "var(--muted)" }}>
                  {step === 2 && !status?.has_clips_json && !completed
                    ? "Requires clips.json — generate or import clips first"
                    : ss?.description || "Not started"}
                </p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  if (canRun(step)) runStep(step);
                }}
                disabled={!canRun(step)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
                style={{
                  background: canRun(step) ? "var(--accent)" : "var(--background)",
                  color: canRun(step) ? "#fff" : "var(--muted)",
                }}
              >
                <Play size={12} /> Run
              </button>
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>

            {/* Config panel */}
            {isExpanded && (
              <div className="px-4 pb-4 space-y-3" style={{ borderTop: "1px solid var(--border)" }}>
                {step === 1 && (
                  <div className="grid grid-cols-2 gap-3 pt-3">
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Language</span>
                      <input
                        value={transcribeConfig.language}
                        onChange={(e) => setTranscribeConfig((c) => ({ ...c, language: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Model</span>
                      <select
                        value={transcribeConfig.model_name}
                        onChange={(e) => setTranscribeConfig((c) => ({ ...c, model_name: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      >
                        <option value="large-v3">large-v3</option>
                        <option value="large-v2">large-v2</option>
                        <option value="medium">medium</option>
                        <option value="small">small</option>
                        <option value="base">base</option>
                      </select>
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Batch Size</span>
                      <input
                        type="number"
                        value={transcribeConfig.batch_size}
                        onChange={(e) => setTranscribeConfig((c) => ({ ...c, batch_size: parseInt(e.target.value) }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Compute Type</span>
                      <select
                        value={transcribeConfig.compute_type}
                        onChange={(e) => setTranscribeConfig((c) => ({ ...c, compute_type: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      >
                        <option value="float16">float16</option>
                        <option value="float32">float32</option>
                        <option value="int8">int8</option>
                      </select>
                    </label>
                  </div>
                )}

                {step === 3 && (
                  <div className="grid grid-cols-2 gap-3 pt-3">
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Number of Speakers</span>
                      <select
                        value={cropConfig.num_speakers}
                        onChange={(e) => setCropConfig((c) => ({ ...c, num_speakers: parseInt(e.target.value) }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      >
                        {[1, 2, 3, 4, 5].map((n) => (
                          <option key={n} value={n}>{n} speaker{n > 1 ? "s" : ""}</option>
                        ))}
                      </select>
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Scene Type</span>
                      <select
                        value={cropConfig.scene_type || ""}
                        onChange={(e) => setCropConfig((c) => ({ ...c, scene_type: e.target.value || undefined }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      >
                        <option value="">Auto detect</option>
                        <option value="podcast">Podcast</option>
                        <option value="gameplay">Gameplay</option>
                      </select>
                    </label>
                    <label className="flex items-center gap-2 pt-2">
                      <input
                        type="checkbox"
                        checked={cropConfig.dynamic_enabled ?? true}
                        onChange={(e) => setCropConfig((c) => ({ ...c, dynamic_enabled: e.target.checked }))}
                      />
                      <span className="text-xs">Dynamic crop (follow active speaker)</span>
                    </label>
                  </div>
                )}

                {step === 4 && (
                  <div className="grid grid-cols-2 gap-3 pt-3">
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Font</span>
                      <input
                        value={subtitleConfig.font_name}
                        onChange={(e) => setSubtitleConfig((c) => ({ ...c, font_name: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Font Size</span>
                      <input
                        type="number"
                        value={subtitleConfig.font_size}
                        onChange={(e) => setSubtitleConfig((c) => ({ ...c, font_size: parseInt(e.target.value) }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Primary Color (ASS format)</span>
                      <input
                        value={subtitleConfig.primary_color}
                        onChange={(e) => setSubtitleConfig((c) => ({ ...c, primary_color: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Karaoke Color (ASS format)</span>
                      <input
                        value={subtitleConfig.karaoke_color}
                        onChange={(e) => setSubtitleConfig((c) => ({ ...c, karaoke_color: e.target.value }))}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      />
                    </label>
                  </div>
                )}

                {step === 2 && (
                  <p className="text-xs pt-3" style={{ color: "var(--muted)" }}>
                    Clips are extracted using the clips JSON generated by AI analysis or manual editing.
                    No additional configuration needed.
                  </p>
                )}
              </div>
            )}

            {/* Progress for running step */}
            {isRunning && (
              <div className="px-4 pb-4">
                <ProgressBar step={`step_${step}`} />
              </div>
            )}
          </div>
        );
      })}

      {/* Log Panel */}
      {running !== null && (
        <div className="rounded-lg overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="p-3" style={{ borderBottom: "1px solid var(--border)" }}>
            <h3 className="text-xs font-semibold">Live Logs</h3>
          </div>
          <LogPanel />
        </div>
      )}
    </div>
  );
}
