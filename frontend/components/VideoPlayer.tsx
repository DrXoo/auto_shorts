"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X } from "lucide-react";
import { media } from "@/lib/api";

interface VideoPlayerProps {
  src?: string;
  onTimeUpdate?: (time: number) => void;
}

export function VideoPlayer({ src, onTimeUpdate }: VideoPlayerProps) {
  const ref = useRef<HTMLVideoElement>(null);

  const seekTo = useCallback((time: number) => {
    if (ref.current) {
      ref.current.currentTime = time;
      ref.current.play();
    }
  }, []);

  if (!src) {
    return (
      <div className="rounded-lg flex items-center justify-center h-48"
        style={{ background: "var(--card)", border: "1px dashed var(--border)" }}>
        <p className="text-sm" style={{ color: "var(--muted)" }}>No video loaded</p>
      </div>
    );
  }

  return (
    <video
      ref={ref}
      src={src}
      controls
      className="w-full rounded-lg"
      style={{ maxHeight: 400 }}
      onTimeUpdate={() => {
        if (ref.current && onTimeUpdate) {
          onTimeUpdate(ref.current.currentTime);
        }
      }}
    />
  );
}

// Attach seekTo to a ref for parent control
export function useVideoPlayer() {
  const ref = useRef<HTMLVideoElement>(null);

  const seekTo = useCallback((time: number) => {
    if (ref.current) {
      ref.current.currentTime = time;
      ref.current.play();
    }
  }, []);

  return { ref, seekTo };
}

// ─── Upload Zone ──────────────────────────────────────────────────

interface UploadZoneProps {
  onUploaded?: (info: Record<string, unknown>) => void;
  accept?: string;
  label?: string;
}

export function UploadZone({ onUploaded, accept = "video/*", label = "Drop video here or click to upload" }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    setUploading(true);
    try {
      const info = await media.upload(file);
      onUploaded?.(info);
    } catch (err) {
      alert("Upload failed: " + (err as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div
      className="rounded-lg p-8 text-center cursor-pointer transition-colors"
      style={{
        background: dragging ? "var(--card-hover)" : "var(--card)",
        border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
      }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
      {uploading ? (
        <p className="text-sm" style={{ color: "var(--accent)" }}>Uploading…</p>
      ) : (
        <>
          <Upload size={32} className="mx-auto mb-2" style={{ color: "var(--muted)" }} />
          <p className="text-sm" style={{ color: "var(--muted)" }}>{label}</p>
        </>
      )}
    </div>
  );
}
