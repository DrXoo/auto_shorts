"use client";

import { useEffect, useState } from "react";
import {
  Download,
  Play,
  RefreshCw,
  RotateCcw,
  X,
  Clock,
  Clapperboard,
} from "lucide-react";
import { pipeline, media, FileInfo } from "@/lib/api";

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ShortsPage() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingVideo, setPlayingVideo] = useState<string | null>(null);
  const [regenLoading, setRegenLoading] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const f = await media.listFiles("final");
      setFiles(f);
    } catch {
      // backend offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleRegenSubtitle = async (name: string) => {
    setRegenLoading(name);
    try {
      await pipeline.regenSubtitle(name);
      refresh();
    } catch (e) {
      alert("Regen failed: " + (e instanceof Error ? e.message : "Error"));
    } finally {
      setRegenLoading(null);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Shorts</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Final generated videos — click to preview, download or regenerate subtitles
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

      {/* Video Player Modal */}
      {playingVideo && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0,0,0,0.85)" }}
          onClick={() => setPlayingVideo(null)}
        >
          <div
            className="relative max-w-sm w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPlayingVideo(null)}
              className="absolute -top-10 right-0 p-1 rounded-full"
              style={{ color: "white" }}
            >
              <X size={24} />
            </button>
            <video
              src={media.fileUrl("final", playingVideo)}
              controls
              autoPlay
              className="w-full rounded-lg"
              style={{ maxHeight: "85vh" }}
            />
            <p
              className="text-center text-sm mt-2"
              style={{ color: "rgba(255,255,255,0.7)" }}
            >
              {playingVideo}
            </p>
          </div>
        </div>
      )}

      {/* Gallery */}
      {files.length === 0 ? (
        <section
          className="rounded-lg p-10 text-center"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <Clapperboard size={40} style={{ color: "var(--muted)", margin: "0 auto 12px" }} />
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No final videos yet. Run the full pipeline to generate shorts.
          </p>
        </section>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {files.map((f) => (
            <div
              key={f.name}
              className="rounded-lg overflow-hidden"
              style={{
                background: "var(--card)",
                border: "1px solid var(--border)",
              }}
            >
              <div
                className="aspect-[9/16] relative cursor-pointer group"
                onClick={() => setPlayingVideo(f.name)}
              >
                <img
                  src={media.thumbnailUrl("final", f.name)}
                  alt={f.name}
                  className="w-full h-full object-cover"
                />
                {/* Play overlay */}
                <div
                  className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ background: "rgba(0,0,0,0.4)" }}
                >
                  <Play size={40} fill="white" style={{ color: "white" }} />
                </div>
                {f.duration && (
                  <span
                    className="absolute bottom-1 right-1 text-xs px-1.5 py-0.5 rounded"
                    style={{ background: "rgba(0,0,0,0.7)" }}
                  >
                    {formatDuration(f.duration)}
                  </span>
                )}
              </div>
              <div className="p-2">
                <p className="text-xs truncate" title={f.name}>
                  {f.name}
                </p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    {formatSize(f.size)}
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleRegenSubtitle(f.name)}
                      title="Regenerate subtitles"
                      disabled={regenLoading === f.name}
                      className="p-1 rounded hover:opacity-80 transition-opacity"
                      style={{ color: "var(--warning, #f59e0b)" }}
                    >
                      <RotateCcw
                        size={14}
                        className={regenLoading === f.name ? "animate-spin" : ""}
                      />
                    </button>
                    <a
                      href={media.fileUrl("final", f.name)}
                      download
                      className="p-1 rounded hover:opacity-80"
                      style={{ color: "var(--accent)" }}
                    >
                      <Download size={14} />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Summary */}
      {files.length > 0 && (
        <p className="text-xs text-center" style={{ color: "var(--muted)" }}>
          {files.length} short{files.length !== 1 ? "s" : ""} generated
          {files.reduce((sum, f) => sum + (f.duration || 0), 0) > 0 && (
            <> · Total {formatDuration(files.reduce((sum, f) => sum + (f.duration || 0), 0))}</>
          )}
        </p>
      )}
    </div>
  );
}
