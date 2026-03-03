"use client";

import { useWebSocket, ProgressEvent } from "@/lib/useWebSocket";

interface ProgressBarProps {
  step?: string;
  className?: string;
}

export function ProgressBar({ step, className = "" }: ProgressBarProps) {
  const { lastEvent, logs } = useWebSocket();

  const relevant = step
    ? logs.filter((e) => e.step === step)
    : logs;

  const current = step
    ? relevant.findLast((e) => e.step === step)
    : lastEvent;

  if (!current) return null;

  const pct = current.percent ?? 0;
  const isComplete = current.type === "complete";
  const isError = current.type === "error";

  return (
    <div className={className}>
      {/* Bar */}
      <div className="w-full h-2 rounded-full overflow-hidden"
        style={{ background: "var(--border)" }}>
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: isError ? "var(--error)" : isComplete ? "var(--success)" : "var(--accent)",
          }}
        />
      </div>
      {/* Message */}
      <p className="text-xs mt-1.5" style={{
        color: isError ? "var(--error)" : "var(--muted)"
      }}>
        {current.message}
        {pct > 0 && !isComplete && ` (${Math.round(pct)}%)`}
      </p>
    </div>
  );
}

export function LogPanel({ step }: { step?: string }) {
  const { logs } = useWebSocket();
  const relevant = step ? logs.filter((e) => e.step === step) : logs;

  return (
    <div className="rounded-lg p-3 text-xs font-mono overflow-y-auto max-h-48"
      style={{ background: "#0d0d0d", border: "1px solid var(--border)" }}>
      {relevant.length === 0 && (
        <p style={{ color: "var(--muted)" }}>Waiting for activity…</p>
      )}
      {relevant.map((e, i) => (
        <div key={i} className="py-0.5" style={{
          color: e.type === "error" ? "var(--error)"
            : e.type === "complete" ? "var(--success)"
            : "var(--muted)"
        }}>
          [{e.step}] {e.message}
        </div>
      ))}
    </div>
  );
}
