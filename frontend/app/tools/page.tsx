"use client";

import { useState, useRef } from "react";
import {
  Scissors,
  Music,
  Trash2,
  Upload,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { tools, media } from "@/lib/api";

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

function TimeInput({ label, totalSeconds, onChange }: { label: string; totalSeconds: number; onChange: (s: number) => void }) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.round((totalSeconds % 60) * 10) / 10;

  const update = (newH: number, newM: number, newS: number) => {
    onChange(Math.max(0, newH * 3600 + newM * 60 + newS));
  };

  const inputStyle = { background: "var(--background)", border: "1px solid var(--border)" };

  return (
    <label className="block">
      <span className="text-xs" style={{ color: "var(--muted)" }}>{label}</span>
      <div className="mt-1 flex items-center gap-1">
        <input
          type="number"
          min={0}
          value={h}
          onChange={(e) => update(parseInt(e.target.value) || 0, m, s)}
          className="w-14 rounded px-2 py-1.5 text-sm text-center"
          style={inputStyle}
          title="Hours"
        />
        <span className="text-xs" style={{ color: "var(--muted)" }}>h</span>
        <input
          type="number"
          min={0}
          max={59}
          value={m}
          onChange={(e) => update(h, parseInt(e.target.value) || 0, s)}
          className="w-14 rounded px-2 py-1.5 text-sm text-center"
          style={inputStyle}
          title="Minutes"
        />
        <span className="text-xs" style={{ color: "var(--muted)" }}>m</span>
        <input
          type="number"
          min={0}
          max={59.9}
          step={0.1}
          value={s}
          onChange={(e) => update(h, m, parseFloat(e.target.value) || 0)}
          className="w-16 rounded px-2 py-1.5 text-sm text-center"
          style={inputStyle}
          title="Seconds"
        />
        <span className="text-xs" style={{ color: "var(--muted)" }}>s</span>
      </div>
    </label>
  );
}

type ToolResult = { success: boolean; message: string } | null;

export default function ToolsPage() {
  // Cut Video
  const [cutVideoPath, setCutVideoPath] = useState("");
  const [cutStart, setCutStart] = useState(0);
  const [cutEnd, setCutEnd] = useState(60);
  const [cutRunning, setCutRunning] = useState(false);
  const [cutResult, setCutResult] = useState<ToolResult>(null);
  const [cutToInput, setCutToInput] = useState(true);

  // Add Music
  const [musicVideoPath, setMusicVideoPath] = useState("");
  const [musicPath, setMusicPath] = useState("");
  const [musicDb, setMusicDb] = useState(-18);
  const [musicFadeIn, setMusicFadeIn] = useState(2);
  const [musicDelay, setMusicDelay] = useState(0);
  const [musicRunning, setMusicRunning] = useState(false);
  const [musicResult, setMusicResult] = useState<ToolResult>(null);
  const musicFileRef = useRef<HTMLInputElement>(null);
  const [musicToInput, setMusicToInput] = useState(true);

  // Clean Output
  const [cleanRunning, setCleanRunning] = useState(false);
  const [cleanResult, setCleanResult] = useState<ToolResult>(null);

  // Available files
  const [inputFiles, setInputFiles] = useState<string[]>([]);
  const [extractedFiles, setExtractedFiles] = useState<string[]>([]);

  // Load files on mount
  useState(() => {
    Promise.all([
      media.listFiles("input"),
      media.listFiles("extracted"),
    ]).then(([inp, ext]) => {
      setInputFiles(inp.map((f) => f.name));
      setExtractedFiles(ext.map((f) => f.name));
    }).catch(() => {});
  });

  const handleCut = async () => {
    if (!cutVideoPath) return;
    setCutRunning(true);
    setCutResult(null);
    try {
      await tools.cutVideo({
        video_path: cutVideoPath,
        start_time: cutStart,
        end_time: cutEnd,
        output_to_input: cutToInput,
      });
      setCutResult({ success: true, message: `Video cut successfully!${cutToInput ? " Saved to input folder." : ""}` });
      // Refresh file lists
      Promise.all([
        media.listFiles("input"),
        media.listFiles("extracted"),
      ]).then(([inp, ext]) => {
        setInputFiles(inp.map((f) => f.name));
        setExtractedFiles(ext.map((f) => f.name));
      }).catch(() => {});
    } catch (e) {
      setCutResult({ success: false, message: e instanceof Error ? e.message : "Error" });
    } finally {
      setCutRunning(false);
    }
  };

  const handleUploadMusic = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await tools.uploadMusic(file);
      setMusicPath(res.path || file.name);
    } catch {
      alert("Error uploading music file");
    }
  };

  const handleAddMusic = async () => {
    if (!musicVideoPath || !musicPath) return;
    setMusicRunning(true);
    setMusicResult(null);
    try {
      await tools.addMusic({
        video_path: musicVideoPath,
        music_path: musicPath,
        music_db: musicDb,
        fade_in: musicFadeIn,
        start_delay_seconds: musicDelay,
        output_to_input: musicToInput,
      });
      setMusicResult({ success: true, message: `Background music added!${musicToInput ? " Saved to input folder." : ""}` });
      // Refresh file lists
      Promise.all([
        media.listFiles("input"),
        media.listFiles("extracted"),
      ]).then(([inp, ext]) => {
        setInputFiles(inp.map((f) => f.name));
        setExtractedFiles(ext.map((f) => f.name));
      }).catch(() => {});
    } catch (e) {
      setMusicResult({ success: false, message: e instanceof Error ? e.message : "Error" });
    } finally {
      setMusicRunning(false);
    }
  };

  const handleClean = async () => {
    if (!confirm("Delete all output files? This cannot be undone.")) return;
    setCleanRunning(true);
    setCleanResult(null);
    try {
      await tools.cleanOutput();
      setCleanResult({ success: true, message: "Output cleaned successfully!" });
    } catch (e) {
      setCleanResult({ success: false, message: e instanceof Error ? e.message : "Error" });
    } finally {
      setCleanRunning(false);
    }
  };

  const ResultBanner = ({ result }: { result: ToolResult }) => {
    if (!result) return null;
    return (
      <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs mt-3"
        style={{
          background: result.success ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
          color: result.success ? "var(--success)" : "var(--error)",
          border: `1px solid ${result.success ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)"}`,
        }}>
        {result.success ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
        {result.message}
      </div>
    );
  };

  const allVideoFiles = [...new Set([...inputFiles, ...extractedFiles])];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Tools</h1>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Utility tools for video post-processing
        </p>
      </div>

      {/* Cut Video */}
      <div className="rounded-lg p-5 space-y-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Scissors size={16} /> Cut Video
        </h2>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Extract a segment from a video by specifying start and end times. Leave end at 0:00:00 to cut from start to the end of the video.
        </p>
        <div className="grid grid-cols-3 gap-3">
          <label className="block col-span-3">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Video File</span>
            <select
              value={cutVideoPath}
              onChange={(e) => setCutVideoPath(e.target.value)}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            >
              <option value="">Select video...</option>
              {allVideoFiles.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </label>
          <div className="col-span-3 grid grid-cols-2 gap-3">
            <TimeInput label="Start" totalSeconds={cutStart} onChange={setCutStart} />
            <TimeInput label="End" totalSeconds={cutEnd} onChange={setCutEnd} />
          </div>
          <div className="col-span-3 flex items-end">
            <button
              onClick={handleCut}
              disabled={cutRunning || !cutVideoPath}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              {cutRunning ? <Loader2 size={14} className="animate-spin" /> : <Scissors size={14} />}
              {cutRunning ? "Cutting..." : "Cut"}
            </button>
          </div>
        </div>
        <label className="flex items-center gap-2 mt-2">
          <input
            type="checkbox"
            checked={cutToInput}
            onChange={(e) => setCutToInput(e.target.checked)}
          />
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            Save to input folder (available as pipeline input)
          </span>
        </label>
        <ResultBanner result={cutResult} />
      </div>

      {/* Add Background Music */}
      <div className="rounded-lg p-5 space-y-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Music size={16} /> Add Background Music
        </h2>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Mix background music into a video with configurable volume, fade-in, and delay.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Video File</span>
            <select
              value={musicVideoPath}
              onChange={(e) => setMusicVideoPath(e.target.value)}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            >
              <option value="">Select video...</option>
              {allVideoFiles.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Music File</span>
            <div className="mt-1 flex gap-1">
              <input
                value={musicPath}
                onChange={(e) => setMusicPath(e.target.value)}
                placeholder="Path or upload..."
                className="flex-1 rounded px-2 py-1.5 text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)" }}
              />
              <button
                onClick={() => musicFileRef.current?.click()}
                className="px-2 py-1.5 rounded text-xs"
                style={{ background: "var(--background)", border: "1px solid var(--border)" }}
              >
                <Upload size={14} />
              </button>
              <input
                ref={musicFileRef}
                type="file"
                accept="audio/*"
                className="hidden"
                onChange={handleUploadMusic}
              />
            </div>
          </label>
          <label className="block">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Volume (dB)</span>
            <input
              type="number"
              value={musicDb}
              onChange={(e) => setMusicDb(parseInt(e.target.value))}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            />
          </label>
          <label className="block">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Fade In (seconds)</span>
            <input
              type="number"
              step="0.5"
              value={musicFadeIn}
              onChange={(e) => setMusicFadeIn(parseFloat(e.target.value))}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            />
          </label>
          <label className="block">
            <span className="text-xs" style={{ color: "var(--muted)" }}>Start Delay (seconds)</span>
            <input
              type="number"
              step="0.5"
              value={musicDelay}
              onChange={(e) => setMusicDelay(parseFloat(e.target.value))}
              className="mt-1 w-full rounded px-2 py-1.5 text-sm"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            />
          </label>
          <div className="flex items-end">
            <button
              onClick={handleAddMusic}
              disabled={musicRunning || !musicVideoPath || !musicPath}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              {musicRunning ? <Loader2 size={14} className="animate-spin" /> : <Music size={14} />}
              {musicRunning ? "Adding..." : "Add Music"}
            </button>
          </div>
        </div>
        <label className="flex items-center gap-2 mt-2">
          <input
            type="checkbox"
            checked={musicToInput}
            onChange={(e) => setMusicToInput(e.target.checked)}
          />
          <span className="text-xs" style={{ color: "var(--muted)" }}>
            Save to input folder (available as pipeline input)
          </span>
        </label>
        <ResultBanner result={musicResult} />
      </div>

      {/* Clean Output */}
      <div className="rounded-lg p-5 space-y-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <Trash2 size={16} /> Clean Output
        </h2>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          Delete all generated files (extracted clips, cropped videos, final outputs, transcripts).
          Input files are preserved.
        </p>
        <button
          onClick={handleClean}
          disabled={cleanRunning}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium disabled:opacity-40"
          style={{ background: "rgba(239,68,68,0.15)", color: "var(--error)", border: "1px solid rgba(239,68,68,0.3)" }}
        >
          {cleanRunning ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
          {cleanRunning ? "Cleaning..." : "Clean All Output"}
        </button>
        <ResultBanner result={cleanResult} />
      </div>
    </div>
  );
}
