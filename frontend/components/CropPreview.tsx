"use client";

import { useRef, useEffect, useState, useCallback } from "react";

interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
  color?: string;
}

interface CropPreviewProps {
  /** URL of the source video frame or image */
  imageSrc: string;
  /** Source video dimensions */
  sourceWidth: number;
  sourceHeight: number;
  /** Output dimensions */
  outputWidth: number;
  outputHeight: number;
  /** Crop regions to draw */
  regions: CropRegion[];
  /** Called when a region is dragged to a new position */
  onRegionChange?: (index: number, region: CropRegion) => void;
  /** Canvas height in CSS pixels */
  canvasHeight?: number;
}

const REGION_COLORS = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
];

/**
 * Canvas-based crop preview. Shows the source frame with overlay rectangles
 * for each crop region. Regions can be dragged to adjust positions.
 */
export function CropPreview({
  imageSrc,
  sourceWidth,
  sourceHeight,
  outputWidth,
  outputHeight,
  regions,
  onRegionChange,
  canvasHeight = 400,
}: CropPreviewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [dragging, setDragging] = useState<{ idx: number; offX: number; offY: number } | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Scale factor: how many CSS pixels per source pixel
  const scale = canvasHeight / sourceHeight;
  const canvasWidth = sourceWidth * scale;

  // Load image
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      imgRef.current = img;
      setLoaded(true);
    };
    img.src = imageSrc;
  }, [imageSrc]);

  // Draw
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imgRef.current;
    if (!canvas || !ctx || !img) return;

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw source image
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    // Darken non-crop areas
    ctx.fillStyle = "rgba(0,0,0,0.4)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw each region
    regions.forEach((r, i) => {
      const sx = r.x * scale;
      const sy = r.y * scale;
      const sw = r.width * scale;
      const sh = r.height * scale;
      const color = r.color || REGION_COLORS[i % REGION_COLORS.length];

      // Clip and draw the image portion for this region (bright)
      ctx.save();
      ctx.beginPath();
      ctx.rect(sx, sy, sw, sh);
      ctx.clip();
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      ctx.restore();

      // Border
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(sx, sy, sw, sh);

      // Label
      if (r.label) {
        ctx.fillStyle = color;
        ctx.font = "bold 12px sans-serif";
        ctx.fillText(r.label, sx + 4, sy + 14);
      }

      // Dimensions text
      ctx.fillStyle = "rgba(255,255,255,0.7)";
      ctx.font = "10px monospace";
      ctx.fillText(`${r.width}×${r.height}`, sx + 4, sy + sh - 6);
    });
  }, [regions, scale, loaded]);

  useEffect(() => { draw(); }, [draw]);

  // Mouse handlers for dragging
  const getRegionAt = (cx: number, cy: number): number => {
    for (let i = regions.length - 1; i >= 0; i--) {
      const r = regions[i];
      const sx = r.x * scale;
      const sy = r.y * scale;
      const sw = r.width * scale;
      const sh = r.height * scale;
      if (cx >= sx && cx <= sx + sw && cy >= sy && cy <= sy + sh) return i;
    }
    return -1;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!onRegionChange) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const idx = getRegionAt(cx, cy);
    if (idx >= 0) {
      const r = regions[idx];
      setDragging({ idx, offX: cx - r.x * scale, offY: cy - r.y * scale });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !onRegionChange) return;
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const r = { ...regions[dragging.idx] };
    r.x = Math.max(0, Math.min(sourceWidth - r.width, (cx - dragging.offX) / scale));
    r.y = Math.max(0, Math.min(sourceHeight - r.height, (cy - dragging.offY) / scale));
    r.x = Math.round(r.x);
    r.y = Math.round(r.y);
    onRegionChange(dragging.idx, r);
  };

  const handleMouseUp = () => setDragging(null);

  return (
    <div className="inline-block rounded-lg overflow-hidden" style={{ border: "1px solid var(--border)" }}>
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        style={{ width: canvasWidth, height: canvasHeight, cursor: dragging ? "grabbing" : "grab" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
    </div>
  );
}

export default CropPreview;
