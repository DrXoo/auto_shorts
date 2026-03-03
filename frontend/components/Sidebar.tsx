"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  PlayCircle,
  FileText,
  Scissors,
  Wrench,
  Clapperboard,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useWebSocket } from "@/lib/useWebSocket";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/pipeline", label: "Pipeline", icon: PlayCircle },
  { href: "/transcript", label: "Transcript", icon: FileText },
  { href: "/clips", label: "Clips", icon: Scissors },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/shorts", label: "Shorts", icon: Clapperboard },
];

export function Sidebar() {
  const pathname = usePathname();
  const { connected } = useWebSocket();

  return (
    <aside className="w-56 flex-shrink-0 border-r flex flex-col"
      style={{ borderColor: "var(--border)", background: "var(--card)" }}>
      {/* Logo */}
      <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
        <h1 className="text-lg font-bold tracking-tight"
          style={{ color: "var(--accent)" }}>
          ✂️ AutoShorts
        </h1>
        <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
          Podcast → Shorts
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href ||
            (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-4 py-2.5 text-sm transition-colors"
              style={{
                color: active ? "var(--accent)" : "var(--foreground)",
                background: active ? "var(--card-hover)" : "transparent",
                borderRight: active ? "2px solid var(--accent)" : "2px solid transparent",
              }}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Connection status */}
      <div className="p-4 border-t flex items-center gap-2 text-xs"
        style={{ borderColor: "var(--border)", color: "var(--muted)" }}>
        {connected ? (
          <>
            <Wifi size={14} style={{ color: "var(--success)" }} />
            <span>Backend connected</span>
          </>
        ) : (
          <>
            <WifiOff size={14} style={{ color: "var(--error)" }} />
            <span>Backend offline</span>
          </>
        )}
      </div>
    </aside>
  );
}
