"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2,
  Circle,
  Film,
  Clock,
  RefreshCw,
  Trash2,
  Star,
  StarOff,
} from "lucide-react";
import { pipeline, media, PipelineStatus, InputVideoInfo } from "@/lib/api";
import { UploadZone } from "@/components/VideoPlayer";
import Link from "next/link";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function Home() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [inputVideos, setInputVideos] = useState<InputVideoInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeVideo, setActiveVideo] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, videos] = await Promise.all([
        pipeline.status(),
        pipeline.listInputVideos(),
      ]);
      setStatus(s);
      setInputVideos(videos);
      // Set active video from localStorage or first video
      const saved = localStorage.getItem("autoshorts_active_video");
      if (saved && videos.some((v) => v.name === saved)) {
        setActiveVideo(saved);
      } else if (videos.length > 0) {
        setActiveVideo(videos[0].name);
      }
    } catch {
      // backend offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const handleSetActive = (name: string) => {
    setActiveVideo(name);
    localStorage.setItem("autoshorts_active_video", name);
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete "${name}" from input? This cannot be undone.`)) return;
    try {
      await pipeline.deleteInputVideo(name);
      if (activeVideo === name) {
        localStorage.removeItem("autoshorts_active_video");
        setActiveVideo(null);
      }
      refresh();
    } catch (e) {
      alert("Delete failed: " + (e instanceof Error ? e.message : "Error"));
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Project overview and quick actions
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Input Videos */}
      <section className="rounded-lg p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Film size={16} /> Input Videos ({inputVideos.length})
          </h2>
          <Link
            href="/tools"
            className="text-xs px-2 py-1 rounded transition-colors"
            style={{ color: "var(--accent)" }}
          >
            Cut / Add Music →
          </Link>
        </div>
        {inputVideos.length > 0 ? (
          <div className="space-y-2">
            {inputVideos.map((v) => {
              const isActive = v.name === activeVideo;
              return (
                <div
                  key={v.name}
                  className="flex items-center gap-3 p-2 rounded-lg transition-colors"
                  style={{
                    background: isActive ? "rgba(99,102,241,0.08)" : "var(--background)",
                    border: `1px solid ${isActive ? "var(--accent)" : "var(--border)"}`,
                  }}
                >
                  <div className="rounded overflow-hidden flex-shrink-0" style={{ width: 120, height: 68, background: "var(--card)" }}>
                    <img
                      src={media.thumbnailUrl("input", v.name)}
                      alt={v.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{v.name}</p>
                    <div className="flex items-center gap-3 mt-1">
                      {v.duration && (
                        <span className="text-xs flex items-center gap-1" style={{ color: "var(--muted)" }}>
                          <Clock size={11} /> {formatDuration(v.duration)}
                        </span>
                      )}
                      <span className="text-xs" style={{ color: "var(--muted)" }}>
                        {formatSize(v.size)}
                      </span>
                      {v.width && v.height && (
                        <span className="text-xs" style={{ color: "var(--muted)" }}>
                          {v.width}×{v.height}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleSetActive(v.name)}
                      title={isActive ? "Active for pipeline" : "Set as active video"}
                      className="p-1.5 rounded transition-colors"
                      style={{ color: isActive ? "var(--accent)" : "var(--muted)" }}
                    >
                      {isActive ? <Star size={16} fill="currentColor" /> : <StarOff size={16} />}
                    </button>
                    <button
                      onClick={() => handleDelete(v.name)}
                      title="Delete"
                      className="p-1.5 rounded transition-colors hover:opacity-80"
                      style={{ color: "var(--error)" }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
            {/* Upload more */}
            <div className="pt-2">
              <UploadZone onUploaded={() => refresh()} label="Drop another video here or click to upload" />
            </div>
          </div>
        ) : (
          <UploadZone onUploaded={() => refresh()} />
        )}
        {inputVideos.length > 1 && (
          <p className="text-xs mt-3" style={{ color: "var(--muted)" }}>
            ★ = active video for pipeline. Use Tools page to cut or add music, then save back to input.
          </p>
        )}
      </section>

      {/* Pipeline Progress */}
      <section className="rounded-lg p-5" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Pipeline Progress</h2>
          <Link
            href="/pipeline"
            className="text-xs px-2 py-1 rounded transition-colors"
            style={{ color: "var(--accent)" }}
          >
            Open Pipeline →
          </Link>
        </div>
        <div className="space-y-2">
          {status?.steps.map((s) => (
            <div key={s.step} className="flex items-center gap-3">
              {s.status === "completed" ? (
                <CheckCircle2 size={16} style={{ color: "var(--success)" }} />
              ) : (
                <Circle size={16} style={{ color: "var(--muted)" }} />
              )}
              <span className="text-sm flex-1">{s.name}</span>
              <span className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: s.status === "completed" ? "rgba(34,197,94,0.15)" : "var(--background)",
                  color: s.status === "completed" ? "var(--success)" : "var(--muted)",
                }}>
                {s.status}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Quick Stats */}
      {status && (
        <div className="grid grid-cols-3 gap-3">
          {Object.entries(status.output_counts).map(([key, count]) => (
            <div key={key} className="rounded-lg p-4 text-center"
              style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
              <p className="text-2xl font-bold" style={{ color: "var(--accent)" }}>{count}</p>
              <p className="text-xs capitalize" style={{ color: "var(--muted)" }}>{key}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
