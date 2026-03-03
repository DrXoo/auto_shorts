/**
 * WebSocket hook for receiving real-time progress updates from the backend.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/ws/progress";

export interface ProgressEvent {
  type: "progress" | "log" | "error" | "complete";
  step?: string;
  percent?: number;
  message: string;
  data?: Record<string, unknown>;
}

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<ProgressEvent | null>(null);
  const [logs, setLogs] = useState<ProgressEvent[]>([]);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      setConnected(true);
      // Start ping interval
      const ping = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send("ping");
        }
      }, 30000);
      socket.addEventListener("close", () => clearInterval(ping));
    };

    socket.onmessage = (event) => {
      if (event.data === "pong") return;
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        setLastEvent(data);
        setLogs((prev) => [...prev.slice(-200), data]); // Keep last 200 entries
      } catch {
        // ignore non-JSON
      }
    };

    socket.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    socket.onerror = () => {
      socket.close();
    };

    ws.current = socket;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const clearLogs = useCallback(() => setLogs([]), []);

  return { connected, lastEvent, logs, clearLogs };
}
