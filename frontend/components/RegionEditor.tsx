"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import type { CropRegion } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────

export type RegionType = "content" | "speaker";

export interface EditorRegion extends CropRegion {
  type: RegionType;
  label?: string;
}

interface RegionEditorProps {
  /** JPEG URL for the current frame */
  frameSrc: string | null;
  /** Source video pixel dimensions */
  sourceWidth: number;
  sourceHeight: number;
  /** The two regions being edited */
  contentRegion: CropRegion | null;
  speakerRegion: CropRegion | null;
  /** Which region type is currently "active" (will receive draw/drag interactions) */
  activeRegionType: RegionType;
  /** Callbacks */
  onContentRegionChange: (r: CropRegion) => void;
  onSpeakerRegionChange: (r: CropRegion) => void;
  /** Canvas display height (px) */
  canvasHeight?: number;
}

// ─── Constants ────────────────────────────────────────────────────

const HANDLE_SIZE = 10; // grab radius in canvas pixels
const CONTENT_COLOR = "#f59e0b"; // amber  — content region
const SPEAKER_COLOR = "#6366f1"; // indigo — speaker region
const ASPECT = 9 / 16;           // locked aspect ratio (width / height) — portrait 9:16
const MIN_W = 80;                 // minimum region width in source pixels

type HandlePos =
  | "tl" | "tm" | "tr"
  | "ml" | "mr"
  | "bl" | "bm" | "br"
  | "body";

interface DragState {
  regionType: RegionType;
  handle: HandlePos;
  startX: number;   // canvas px
  startY: number;
  origRegion: CropRegion;
}

// ─── Helpers ─────────────────────────────────────────────────────

function hitHandle(
  cx: number, cy: number,
  r: CropRegion,
  scale: number,
): HandlePos | null {
  const sx = r.x * scale;
  const sy = r.y * scale;
  const sw = r.width * scale;
  const sh = r.height * scale;
  const H = HANDLE_SIZE;

  const handles: Array<[HandlePos, number, number]> = [
    ["tl", sx,        sy       ],
    ["tm", sx + sw/2, sy       ],
    ["tr", sx + sw,   sy       ],
    ["ml", sx,        sy + sh/2],
    ["mr", sx + sw,   sy + sh/2],
    ["bl", sx,        sy + sh  ],
    ["bm", sx + sw/2, sy + sh  ],
    ["br", sx + sw,   sy + sh  ],
  ];

  for (const [name, hx, hy] of handles) {
    if (Math.abs(cx - hx) <= H && Math.abs(cy - hy) <= H) return name;
  }

  // Body (interior)
  if (cx >= sx && cx <= sx + sw && cy >= sy && cy <= sy + sh) return "body";
  return null;
}

function applyDrag(
  drag: DragState,
  cx: number,
  cy: number,
  scale: number,
  sourceWidth: number,
  sourceHeight: number,
): CropRegion {
  const dx = (cx - drag.startX) / scale;
  const dy = (cy - drag.startY) / scale;
  const o = drag.origRegion;
  let { x, y, width, height } = o;

  switch (drag.handle) {
    // ── Move ────────────────────────────────────────────────────────
    case "body":
      x = Math.max(0, Math.min(sourceWidth - width, x + dx));
      y = Math.max(0, Math.min(sourceHeight - height, y + dy));
      break;

    // ── Corner handles: drive width from dx, lock height to 16:9 ───
    case "tl":
      width  = Math.max(MIN_W, o.width - dx);
      height = width / ASPECT;
      x = o.x + o.width  - width;
      y = o.y + o.height - height;
      break;
    case "tr":
      width  = Math.max(MIN_W, o.width + dx);
      height = width / ASPECT;
      // x stays anchored to left
      y = o.y + o.height - height;  // anchor bottom
      break;
    case "bl":
      width  = Math.max(MIN_W, o.width - dx);
      height = width / ASPECT;
      x = o.x + o.width - width;    // anchor right
      // y stays anchored to top
      break;
    case "br":
      width  = Math.max(MIN_W, o.width + dx);
      height = width / ASPECT;
      break;

    // ── Top/bottom edge: drive height from dy, lock width ───────────
    case "tm": {
      height = Math.max(MIN_W / ASPECT, o.height - dy);
      width  = height * ASPECT;
      x = o.x + (o.width - width) / 2;  // keep centered
      y = o.y + o.height - height;       // anchor bottom
      break;
    }
    case "bm": {
      height = Math.max(MIN_W / ASPECT, o.height + dy);
      width  = height * ASPECT;
      x = o.x + (o.width - width) / 2;  // keep centered
      // y stays anchored to top
      break;
    }

    // ── Left/right edge: drive width from dx, lock height ───────────
    case "ml":
      width  = Math.max(MIN_W, o.width - dx);
      height = width / ASPECT;
      x = o.x + o.width  - width;        // anchor right
      y = o.y + (o.height - height) / 2; // keep centered
      break;
    case "mr":
      width  = Math.max(MIN_W, o.width + dx);
      height = width / ASPECT;
      // x stays anchored to left
      y = o.y + (o.height - height) / 2; // keep centered
      break;
  }

  // Clamp to source bounds
  x = Math.max(0, Math.min(sourceWidth  - width,  x));
  y = Math.max(0, Math.min(sourceHeight - height, y));
  width  = Math.min(width,  sourceWidth  - x);
  height = Math.min(height, sourceHeight - y);

  return {
    x: Math.round(x),
    y: Math.round(y),
    width:  Math.round(width),
    height: Math.round(height),
  };
}

function handleCursor(h: HandlePos | null): string {
  if (!h) return "crosshair";
  const map: Record<HandlePos, string> = {
    body: "move",
    tl: "nw-resize", tm: "n-resize", tr: "ne-resize",
    ml: "w-resize",                  mr: "e-resize",
    bl: "sw-resize", bm: "s-resize", br: "se-resize",
  };
  return map[h];
}

// ─── Draw helper ─────────────────────────────────────────────────

function drawRegion(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  r: CropRegion,
  color: string,
  label: string,
  scale: number,
  isActive: boolean,
) {
  const sx = r.x * scale;
  const sy = r.y * scale;
  const sw = r.width * scale;
  const sh = r.height * scale;

  // Reveal region on the darkened canvas
  ctx.save();
  ctx.beginPath();
  ctx.rect(sx, sy, sw, sh);
  ctx.clip();
  ctx.drawImage(img, 0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.restore();

  // Border
  ctx.strokeStyle = color;
  ctx.lineWidth = isActive ? 2.5 : 1.5;
  ctx.setLineDash(isActive ? [] : [6, 3]);
  ctx.strokeRect(sx, sy, sw, sh);
  ctx.setLineDash([]);

  // Label tag
  const tagH = 18;
  ctx.fillStyle = color;
  ctx.fillRect(sx, sy - tagH, 80, tagH);
  ctx.fillStyle = "#fff";
  ctx.font = "bold 11px sans-serif";
  ctx.fillText(label, sx + 4, sy - 4);

  // Dimensions
  ctx.fillStyle = "rgba(255,255,255,0.75)";
  ctx.font = "10px monospace";
  ctx.fillText(`${r.width}×${r.height}`, sx + 4, sy + sh - 5);

  // Resize handles (only for active region)
  if (isActive) {
    const H = HANDLE_SIZE;
    const handles: [number, number][] = [
      [sx,        sy       ],
      [sx + sw/2, sy       ],
      [sx + sw,   sy       ],
      [sx,        sy + sh/2],
      [sx + sw,   sy + sh/2],
      [sx,        sy + sh  ],
      [sx + sw/2, sy + sh  ],
      [sx + sw,   sy + sh  ],
    ];
    for (const [hx, hy] of handles) {
      ctx.fillStyle = "#fff";
      ctx.fillRect(hx - H / 2, hy - H / 2, H, H);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(hx - H / 2, hy - H / 2, H, H);
    }
  }
}

// ─── Component ───────────────────────────────────────────────────

export function RegionEditor({
  frameSrc,
  sourceWidth,
  sourceHeight,
  contentRegion,
  speakerRegion,
  activeRegionType,
  onContentRegionChange,
  onSpeakerRegionChange,
  canvasHeight = 420,
}: RegionEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [drag, setDrag] = useState<DragState | null>(null);
  const [drawing, setDrawing] = useState<{ startX: number; startY: number } | null>(null);
  const [cursor, setCursor] = useState("crosshair");

  const scale = sourceHeight > 0 ? canvasHeight / sourceHeight : 1;
  const canvasWidth = sourceWidth * scale;

  // Load frame image
  useEffect(() => {
    if (!frameSrc) { setLoaded(false); return; }
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => { imgRef.current = img; setLoaded(true); };
    img.onerror = () => setLoaded(false);
    img.src = frameSrc;
  }, [frameSrc]);

  // Draw canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imgRef.current;
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!img || !loaded) {
      // Placeholder
      ctx.fillStyle = "#1a1a2e";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#555";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        frameSrc ? "Loading frame…" : "Select a video to see a frame preview",
        canvas.width / 2,
        canvas.height / 2,
      );
      ctx.textAlign = "left";
      return;
    }

    // Source frame
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    // Darken
    ctx.fillStyle = "rgba(0,0,0,0.45)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Content region
    if (contentRegion) {
      drawRegion(
        ctx, img, contentRegion,
        CONTENT_COLOR, "Content",
        scale, activeRegionType === "content",
      );
    }

    // Speaker region
    if (speakerRegion) {
      drawRegion(
        ctx, img, speakerRegion,
        SPEAKER_COLOR, "Speaker",
        scale, activeRegionType === "speaker",
      );
    }
  }, [frameSrc, loaded, contentRegion, speakerRegion, activeRegionType, scale]);

  useEffect(() => { draw(); }, [draw]);

  // ── Mouse helpers ────────────────────────────────────────────────

  const canvasPos = (e: React.MouseEvent) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return { cx: 0, cy: 0 };
    return { cx: e.clientX - rect.left, cy: e.clientY - rect.top };
  };

  const getHit = (cx: number, cy: number): { type: RegionType; handle: HandlePos } | null => {
    // Active region gets priority
    const active = activeRegionType === "content" ? contentRegion : speakerRegion;
    if (active) {
      const h = hitHandle(cx, cy, active, scale);
      if (h) return { type: activeRegionType, handle: h };
    }
    // Check inactive region (body only)
    const inactive = activeRegionType === "content" ? speakerRegion : contentRegion;
    const inactiveType: RegionType = activeRegionType === "content" ? "speaker" : "content";
    if (inactive) {
      const h = hitHandle(cx, cy, inactive, scale);
      if (h) return { type: inactiveType, handle: h };
    }
    return null;
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    const { cx, cy } = canvasPos(e);
    const hit = getHit(cx, cy);

    if (hit) {
      const region = hit.type === "content" ? contentRegion! : speakerRegion!;
      setDrag({ regionType: hit.type, handle: hit.handle, startX: cx, startY: cy, origRegion: region });
    } else {
      // Start drawing a new region for the active type
      setDrawing({ startX: cx, startY: cy });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const { cx, cy } = canvasPos(e);

    if (drag) {
      const updated = applyDrag(drag, cx, cy, scale, sourceWidth, sourceHeight);
      if (drag.regionType === "content") onContentRegionChange(updated);
      else onSpeakerRegionChange(updated);
      return;
    }

    if (drawing) {
      // Width drives; height is locked to 16:9
      const rawW = Math.abs(cx - drawing.startX) / scale;
      const rawH = rawW / ASPECT;
      const startXSrc = drawing.startX / scale;
      const startYSrc = drawing.startY / scale;
      const newX = cx < drawing.startX ? startXSrc - rawW : startXSrc;
      const newY = cy < drawing.startY ? startYSrc - rawH : startYSrc;
      if (rawW > 30) {
        const newR: CropRegion = {
          x: Math.round(Math.max(0, newX)),
          y: Math.round(Math.max(0, newY)),
          width:  Math.round(rawW),
          height: Math.round(rawH),
        };
        if (activeRegionType === "content") onContentRegionChange(newR);
        else onSpeakerRegionChange(newR);
      }
      return;
    }

    // Update cursor
    const hit = getHit(cx, cy);
    if (hit) setCursor(handleCursor(hit.handle));
    else setCursor("crosshair");
  };

  const handleMouseUp = () => {
    setDrag(null);
    setDrawing(null);
  };

  return (
    <div
      className="inline-block rounded-lg overflow-hidden select-none"
      style={{ border: "1px solid var(--border)" }}
    >
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        style={{ width: canvasWidth, height: canvasHeight, cursor, display: "block" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />
    </div>
  );
}

export default RegionEditor;
