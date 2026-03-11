"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Film,
  Plus,
  Trash2,
  Play,
  Camera,
  Send,
  Save,
  RotateCcw,
  Maximize2,
  LayoutTemplate,
  SplitSquareVertical,
} from "lucide-react";
import { media, tools } from "@/lib/api";
import type {
  FileInfo,
  CropRegion,
  ContentSegment,
  ContentLayout,
  EditorVideoInfo,
} from "@/lib/api";
import type { RegionType } from "@/components/RegionEditor";
import RegionEditor from "@/components/RegionEditor";
import { useWebSocket } from "@/lib/useWebSocket";

// ─── Helpers ──────────────────────────────────────────────────────

function fmt(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function parseFmt(v: string): number {
  const parts = v.split(":").map(Number);
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return parseFloat(v) || 0;
}

const LAYOUT_ICONS: Record<ContentLayout, React.ReactNode> = {
  fullscreen: <Maximize2 size={14} />,
  split_top: <LayoutTemplate size={14} />,
  split_bottom: <SplitSquareVertical size={14} />,
};

const LAYOUT_LABELS: Record<ContentLayout, string> = {
  fullscreen: "Full",
  split_top: "Content↑ Speaker↓",
  split_bottom: "Speaker↑ Content↓",
};

// ─── Default region helpers ───────────────────────────────────────

function defaultContentRegion(w: number, h: number): CropRegion {
  // 9:16 portrait region — width drives size, height = width * 16/9
  const rw = Math.round(w * 0.35);
  const rh = Math.round(rw * 16 / 9);
  const clampedH = Math.min(rh, h);
  const clampedW = Math.round(clampedH * 9 / 16);
  return { x: w - clampedW, y: Math.round((h - clampedH) / 2), width: clampedW, height: clampedH };
}

function defaultSpeakerRegion(w: number, h: number): CropRegion {
  // 9:16 portrait region — width drives size, height = width * 16/9
  const rw = Math.round(w * 0.28);
  const rh = Math.round(rw * 16 / 9);
  const clampedH = Math.min(rh, h);
  const clampedW = Math.round(clampedH * 9 / 16);
  return { x: 0, y: Math.round((h - clampedH) / 2), width: clampedW, height: clampedH };
}

// ─── Segment row ──────────────────────────────────────────────────

interface SegmentRowProps {
  seg: ContentSegment;
  index: number;
  duration: number;
  onDelete: () => void;
  onChange: (s: ContentSegment) => void;
  onSeek: (t: number) => void;
}

function SegmentRow({ seg, index, duration, onDelete, onChange, onSeek }: SegmentRowProps) {
  return (
    <div
      className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm"
      style={{ background: "var(--card-hover)", border: "1px solid var(--border)" }}
    >
      {/* Index */}
      <span
        className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
        style={{ background: "var(--accent)", color: "#fff" }}
      >
        {index + 1}
      </span>

      {/* Time inputs */}
      <div className="flex items-center gap-1">
        <input
          type="text"
          value={fmt(seg.start)}
          onChange={(e) => onChange({ ...seg, start: parseFmt(e.target.value) })}
          onBlur={(e) => onSeek(parseFmt(e.target.value))}
          className="w-16 px-1 py-0.5 rounded text-center text-xs"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)" }}
        />
        <span style={{ color: "var(--muted)" }}>→</span>
        <input
          type="text"
          value={fmt(seg.end)}
          onChange={(e) => onChange({ ...seg, end: parseFmt(e.target.value) })}
          className="w-16 px-1 py-0.5 rounded text-center text-xs"
          style={{ background: "var(--card)", border: "1px solid var(--border)", color: "var(--foreground)" }}
        />
      </div>

      {/* Layout selector */}
      <div className="flex gap-1 flex-shrink-0">
        {(["fullscreen", "split_top", "split_bottom"] as ContentLayout[]).map((l) => (
          <button
            key={l}
            title={LAYOUT_LABELS[l]}
            onClick={() => onChange({ ...seg, layout: l })}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs"
            style={{
              background: seg.layout === l ? "var(--accent)" : "var(--card)",
              border: "1px solid var(--border)",
              color: seg.layout === l ? "#fff" : "var(--muted)",
            }}
          >
            {LAYOUT_ICONS[l]}
          </button>
        ))}
      </div>

      {/* Duration badge */}
      <span className="text-xs" style={{ color: "var(--muted)" }}>
        {(seg.end - seg.start).toFixed(1)}s
      </span>

      <div className="flex-1" />

      {/* Seek button */}
      <button
        title="Seek to start"
        onClick={() => onSeek(seg.start)}
        className="p-1 rounded hover:opacity-70"
        style={{ color: "var(--accent)" }}
      >
        <Play size={12} />
      </button>

      {/* Delete */}
      <button
        onClick={onDelete}
        className="p-1 rounded hover:opacity-70"
        style={{ color: "var(--destructive, #ef4444)" }}
      >
        <Trash2 size={13} />
      </button>
    </div>
  );
}

// ─── Timeline bar component ───────────────────────────────────────

interface TimelineBarProps {
  duration: number;
  segments: ContentSegment[];
  currentTime: number;
  onSeek: (t: number) => void;
}

function TimelineBar({ duration, segments, currentTime, onSeek }: TimelineBarProps) {
  const barRef = useRef<HTMLDivElement>(null);

  const handleClick = (e: React.MouseEvent) => {
    const rect = barRef.current?.getBoundingClientRect();
    if (!rect || duration <= 0) return;
    const t = ((e.clientX - rect.left) / rect.width) * duration;
    onSeek(Math.max(0, Math.min(duration, t)));
  };

  const pct = (t: number) => (t / duration) * 100;

  return (
    <div
      ref={barRef}
      className="relative h-8 rounded-md cursor-pointer overflow-hidden select-none"
      style={{ background: "var(--card-hover)", border: "1px solid var(--border)" }}
      onClick={handleClick}
      title="Click to seek"
    >
      {/* Base track */}
      <div className="absolute inset-0" style={{ background: "rgba(99,102,241,0.12)" }} />

      {/* Content segments */}
      {segments.map((s, i) => (
        <div
          key={i}
          className="absolute top-0 h-full rounded-sm"
          style={{
            left: `${pct(s.start)}%`,
            width: `${pct(s.end - s.start)}%`,
            background: "rgba(245,158,11,0.55)",
            borderLeft: "2px solid #f59e0b",
            borderRight: "2px solid #f59e0b",
          }}
          title={`Segment ${i + 1}: ${fmt(s.start)} – ${fmt(s.end)}`}
        />
      ))}

      {/* Playhead */}
      {duration > 0 && (
        <div
          className="absolute top-0 h-full w-0.5 bg-white pointer-events-none"
          style={{ left: `${pct(currentTime)}%`, opacity: 0.8 }}
        />
      )}

      {/* Time labels */}
      {duration > 0 && (
        <>
          <span
            className="absolute left-1 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
            style={{ color: "var(--muted)" }}
          >
            {fmt(0)}
          </span>
          <span
            className="absolute right-1 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
            style={{ color: "var(--muted)" }}
          >
            {fmt(duration)}
          </span>
        </>
      )}
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────────

export default function EditorPage() {
  // ── File / video state ─────────────────────────────────────────
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [videoInfo, setVideoInfo] = useState<EditorVideoInfo | null>(null);

  // ── Playback state ─────────────────────────────────────────────
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);

  // ── Frame / canvas state ───────────────────────────────────────
  const [frameSrc, setFrameSrc] = useState<string | null>(null);
  const [frameTime, setFrameTime] = useState(0);
  const [activeRegionType, setActiveRegionType] = useState<RegionType>("content");
  const [contentRegion, setContentRegion] = useState<CropRegion | null>(null);
  const [speakerRegion, setSpeakerRegion] = useState<CropRegion | null>(null);
  const [defaultSpeaker, setDefaultSpeaker] = useState<CropRegion | null>(null);

  // ── Segments ───────────────────────────────────────────────────
  const [segments, setSegments] = useState<ContentSegment[]>([]);

  // ── UI state ───────────────────────────────────────────────────
  const [status, setStatus] = useState<"idle" | "rendering" | "done" | "error">("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [renderProgress, setRenderProgress] = useState(0);
  const [outputName, setOutputName] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  const { lastEvent } = useWebSocket();

  // ── Load file list ─────────────────────────────────────────────
  useEffect(() => {
    media.listFiles("extracted").then(setFiles).catch(console.error);
  }, []);

  // ── Handle WebSocket progress ──────────────────────────────────
  useEffect(() => {
    if (!lastEvent || lastEvent.step !== "editor") return;
    const pct = lastEvent.percent ?? 0;
    setRenderProgress(pct);
    setStatusMsg(lastEvent.message || "");
    if (pct >= 100) setStatus("done");
  }, [lastEvent]);

  // ── Select video ───────────────────────────────────────────────
  const handleSelectVideo = useCallback(async (name: string) => {
    setSelectedFile(name);
    setSegments([]);
    setFrameSrc(null);
    setStatus("idle");
    setStatusMsg("");
    if (!name) { setVideoInfo(null); return; }

    try {
      const info = await tools.editorVideoInfo(name);
      setVideoInfo(info);

      // Set default regions based on video dimensions
      const cr = defaultContentRegion(info.width, info.height);
      const sr = defaultSpeakerRegion(info.width, info.height);
      setContentRegion(cr);
      setSpeakerRegion(sr);
      setDefaultSpeaker(sr);

      // Generate output name
      const stem = name.replace(/\.[^.]+$/, "");
      setOutputName(`${stem}_edited.mp4`);

      // Try to load saved composition
      const loaded = await tools.editorLoad(name);
      if (loaded.exists && loaded.composition) {
        const comp = loaded.composition;
        setSegments(comp.segments || []);
        if (comp.default_speaker_region) setDefaultSpeaker(comp.default_speaker_region);
        setSaveMsg("Composition loaded ✓");
        setTimeout(() => setSaveMsg(""), 2500);
      }

      // Capture frame at 5s (or 0 if short)
      const t = Math.min(5, (info.duration || 0) * 0.1);
      captureFrameAt(name, t);
    } catch (e: unknown) {
      console.error(e);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Capture frame ──────────────────────────────────────────────
  const captureFrameAt = (videoPath: string, t: number) => {
    const url = tools.editorFrameUrl(videoPath, t);
    setFrameSrc(url + "&_ts=" + Date.now());
    setFrameTime(t);
  };

  const handleCaptureFrame = () => {
    if (!selectedFile) return;
    const t = videoRef.current?.currentTime ?? currentTime;
    captureFrameAt(selectedFile, t);
  };

  // ── Seek video ─────────────────────────────────────────────────
  const seekTo = (t: number) => {
    if (videoRef.current) videoRef.current.currentTime = t;
    setCurrentTime(t);
  };

  // ── Add segment ────────────────────────────────────────────────
  const addSegment = () => {
    if (!contentRegion) return;
    const t = videoRef.current?.currentTime ?? 0;
    const dur = videoInfo?.duration ?? 0;
    const end = Math.min(t + 5, dur);
    const newSeg: ContentSegment = {
      start: parseFloat(t.toFixed(2)),
      end: parseFloat(end.toFixed(2)),
      content_region: { ...contentRegion },
      speaker_region: speakerRegion ? { ...speakerRegion } : null,
      layout: "fullscreen",
    };
    setSegments((prev) => [...prev, newSeg].sort((a, b) => a.start - b.start));
  };

  // ── Save composition ───────────────────────────────────────────
  const saveComposition = async () => {
    if (!selectedFile) return;
    try {
      await tools.editorSave({
        video_path: selectedFile,
        segments,
        default_speaker_region: defaultSpeaker ?? undefined,
      });
      setSaveMsg("Saved ✓");
      setTimeout(() => setSaveMsg(""), 2000);
    } catch (e: unknown) {
      setSaveMsg("Save failed");
    }
  };

  // ── Render ─────────────────────────────────────────────────────
  const handleRender = async () => {
    if (!selectedFile || !defaultSpeaker) return;
    setStatus("rendering");
    setRenderProgress(0);
    setStatusMsg("Starting render…");
    try {
      await tools.editorRender({
        video_path: selectedFile,
        segments,
        default_speaker_region: defaultSpeaker,
        output_name: outputName || undefined,
      });
    } catch (e: unknown) {
      setStatus("error");
      setStatusMsg(String(e));
    }
  };

  const videoUrl = selectedFile
    ? media.fileUrl("extracted", selectedFile)
    : null;

  const srcW = videoInfo?.width ?? 1920;
  const srcH = videoInfo?.height ?? 1080;
  const duration = videoInfo?.duration ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6 max-w-screen-2xl mx-auto">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <Film size={24} style={{ color: "var(--accent)" }} />
        <div>
          <h1 className="text-xl font-bold">Content Editor</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Recover shared content from extracted clips and compose vertical video
          </p>
        </div>
      </div>

      {/* ── Video selector ───────────────────────────────────────────── */}
      <div
        className="rounded-xl p-4 flex items-center gap-4"
        style={{ background: "var(--card)", border: "1px solid var(--border)" }}
      >
        <label className="text-sm font-medium min-w-max" style={{ color: "var(--muted)" }}>
          Source clip
        </label>
        <select
          className="flex-1 rounded-lg px-3 py-2 text-sm"
          style={{
            background: "var(--card-hover)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
          }}
          value={selectedFile}
          onChange={(e) => handleSelectVideo(e.target.value)}
        >
          <option value="">Select an extracted clip…</option>
          {files.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name}
              {f.duration ? ` — ${fmt(f.duration)}` : ""}
            </option>
          ))}
        </select>
        {videoInfo && (
          <span className="text-xs whitespace-nowrap" style={{ color: "var(--muted)" }}>
            {videoInfo.width}×{videoInfo.height} · {fmt(videoInfo.duration)}
          </span>
        )}
        {saveMsg && (
          <span className="text-xs" style={{ color: "var(--accent)" }}>
            {saveMsg}
          </span>
        )}
      </div>

      {/* ── Main layout ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">

        {/* ── Left: player + canvas ──────────────────────────────────── */}
        <div className="flex flex-col gap-4">

          {/* Video player */}
          {videoUrl && (
            <div
              className="rounded-xl overflow-hidden"
              style={{ background: "var(--card)", border: "1px solid var(--border)" }}
            >
              <video
                ref={videoRef}
                src={videoUrl}
                controls
                className="w-full"
                style={{ maxHeight: "240px", background: "#000" }}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              />
            </div>
          )}

          {/* Timeline bar */}
          {duration > 0 && (
            <TimelineBar
              duration={duration}
              segments={segments}
              currentTime={currentTime}
              onSeek={seekTo}
            />
          )}

          {/* Region editor canvas + controls */}
          <div
            className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            {/* Canvas toolbar */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">Frame preview</span>
              {frameTime > 0 && (
                <span className="text-xs" style={{ color: "var(--muted)" }}>
                  @ {fmt(frameTime)}
                </span>
              )}
              <div className="flex-1" />

              {/* Region type toggle */}
              <div
                className="flex rounded-lg overflow-hidden"
                style={{ border: "1px solid var(--border)" }}
              >
                {(["content", "speaker"] as RegionType[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setActiveRegionType(t)}
                    className="px-3 py-1.5 text-xs font-medium transition-colors"
                    style={{
                      background: activeRegionType === t ? "var(--accent)" : "var(--card-hover)",
                      color: activeRegionType === t ? "#fff" : "var(--foreground)",
                    }}
                  >
                    {t === "content" ? "🟡 Content" : "🟣 Speaker"}
                  </button>
                ))}
              </div>

              {/* Capture frame button */}
              <button
                onClick={handleCaptureFrame}
                disabled={!selectedFile}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-opacity disabled:opacity-40"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                <Camera size={13} />
                Capture frame
              </button>
            </div>

            {/* Tips */}
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              <strong>Draw</strong> to create a region · <strong>Drag</strong> to move ·{" "}
              <strong>Handles</strong> to resize · Toggle above to switch active region
            </p>

            {/* Canvas */}
            <div className="overflow-auto">
              <RegionEditor
                frameSrc={frameSrc}
                sourceWidth={srcW}
                sourceHeight={srcH}
                contentRegion={contentRegion}
                speakerRegion={speakerRegion}
                activeRegionType={activeRegionType}
                onContentRegionChange={setContentRegion}
                onSpeakerRegionChange={(r) => { setSpeakerRegion(r); }}
                canvasHeight={380}
              />
            </div>

            {/* Region info */}
            <div className="flex gap-4 text-xs" style={{ color: "var(--muted)" }}>
              {contentRegion && (
                <span>
                  🟡 Content: {contentRegion.x},{contentRegion.y} · {contentRegion.width}×{contentRegion.height}
                </span>
              )}
              {speakerRegion && (
                <span>
                  🟣 Speaker: {speakerRegion.x},{speakerRegion.y} · {speakerRegion.width}×{speakerRegion.height}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ── Right: segments + render ───────────────────────────────── */}
        <div className="flex flex-col gap-4">

          {/* Default speaker region note */}
          <div
            className="rounded-xl p-3 text-xs"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <p className="font-semibold mb-1" style={{ color: "var(--foreground)" }}>
              Default speaker crop
            </p>
            <p style={{ color: "var(--muted)" }}>
              Used for all non-content parts of the video. Set the 🟣 Speaker region on the canvas,
              then click the button below to update it.
            </p>
            <button
              className="mt-2 px-3 py-1 rounded-lg text-xs font-medium"
              style={{ background: "var(--accent)", color: "#fff" }}
              onClick={() => { if (speakerRegion) setDefaultSpeaker(speakerRegion); }}
              disabled={!speakerRegion}
            >
              Use current speaker region as default
            </button>
            {defaultSpeaker && (
              <p className="mt-1 font-mono" style={{ color: "var(--muted)" }}>
                {defaultSpeaker.x},{defaultSpeaker.y} · {defaultSpeaker.width}×{defaultSpeaker.height}
              </p>
            )}
          </div>

          {/* Segments */}
          <div
            className="rounded-xl p-4 flex flex-col gap-3 flex-1"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">
                Content segments
                <span
                  className="ml-1.5 text-xs font-normal"
                  style={{ color: "var(--muted)" }}
                >
                  ({segments.length})
                </span>
              </h2>
              <button
                onClick={addSegment}
                disabled={!selectedFile || !contentRegion}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                <Plus size={13} />
                Add at {fmt(currentTime)}
              </button>
            </div>

            {segments.length === 0 ? (
              <p className="text-sm text-center py-6" style={{ color: "var(--muted)" }}>
                No segments yet. Set region on canvas, then click "Add at…"
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                {segments.map((seg, i) => (
                  <SegmentRow
                    key={i}
                    seg={seg}
                    index={i}
                    duration={duration}
                    onDelete={() => setSegments((prev) => prev.filter((_, j) => j !== i))}
                    onChange={(updated) =>
                      setSegments((prev) =>
                        prev.map((s, j) => (j === i ? updated : s))
                      )
                    }
                    onSeek={seekTo}
                  />
                ))}
              </div>
            )}

            {/* Legend */}
            {segments.length > 0 && (
              <div className="text-xs pt-1 flex gap-4" style={{ color: "var(--muted)" }}>
                <span className="flex items-center gap-1">
                  {LAYOUT_ICONS.fullscreen} Full frame
                </span>
                <span className="flex items-center gap-1">
                  {LAYOUT_ICONS.split_top} Content top
                </span>
                <span className="flex items-center gap-1">
                  {LAYOUT_ICONS.split_bottom} Content bottom
                </span>
              </div>
            )}
          </div>

          {/* Render controls */}
          <div
            className="rounded-xl p-4 flex flex-col gap-3"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <h2 className="text-sm font-semibold">Render</h2>

            <div className="flex gap-2">
              <input
                type="text"
                placeholder="output_edited.mp4"
                value={outputName}
                onChange={(e) => setOutputName(e.target.value)}
                className="flex-1 px-2 py-1.5 rounded-lg text-sm"
                style={{
                  background: "var(--card-hover)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={saveComposition}
                disabled={!selectedFile}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium disabled:opacity-40"
                style={{
                  background: "var(--card-hover)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              >
                <Save size={14} />
                Save
              </button>

              <button
                onClick={() => {
                  setSegments([]);
                  setStatus("idle");
                  setStatusMsg("");
                }}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium"
                style={{
                  background: "var(--card-hover)",
                  border: "1px solid var(--border)",
                  color: "var(--foreground)",
                }}
              >
                <RotateCcw size={14} />
                Clear
              </button>

              <button
                onClick={handleRender}
                disabled={!selectedFile || !defaultSpeaker || status === "rendering"}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-40"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                <Send size={14} />
                {status === "rendering" ? "Rendering…" : "Render"}
              </button>
            </div>

            {/* Progress */}
            {(status === "rendering" || status === "done" || status === "error") && (
              <div className="flex flex-col gap-1.5 mt-1">
                {status === "rendering" && (
                  <div
                    className="rounded-full h-2 overflow-hidden"
                    style={{ background: "var(--card-hover)" }}
                  >
                    <div
                      className="h-full rounded-full transition-all duration-300"
                      style={{
                        width: `${renderProgress}%`,
                        background: "var(--accent)",
                      }}
                    />
                  </div>
                )}
                <p
                  className="text-xs"
                  style={{
                    color:
                      status === "error"
                        ? "#ef4444"
                        : status === "done"
                        ? "#10b981"
                        : "var(--muted)",
                  }}
                >
                  {status === "done" && "✓ "}
                  {status === "error" && "✗ "}
                  {statusMsg}
                </p>
                {status === "done" && (
                  <p className="text-xs" style={{ color: "var(--muted)" }}>
                    Output saved to <code>output/cropped/</code>. You can now run the Subtitle step.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
