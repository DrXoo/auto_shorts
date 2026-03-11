"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import {
  Users,
  Merge,
  Save,
  Wand2,
  Search,
  Play,
  ChevronDown,
  Replace,
  Plus,
  X,
} from "lucide-react";
import {
  transcript as transcriptApi,
  pipeline as pipelineApi,
  TranscriptData,
  TranscriptSegment,
  SpeakerInfo,
  media,
  InputVideoInfo,
} from "@/lib/api";

// ─── Utilities ────────────────────────────────────────────────────

const SPEAKER_COLORS: Record<string, string> = {};
const PALETTE = [
  "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6",
  "#ec4899", "#14b8a6", "#f97316", "#3b82f6", "#84cc16",
];

function getSpeakerColor(speaker: string): string {
  if (!SPEAKER_COLORS[speaker]) {
    const idx = Object.keys(SPEAKER_COLORS).length % PALETTE.length;
    SPEAKER_COLORS[speaker] = PALETTE[idx];
  }
  return SPEAKER_COLORS[speaker];
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

// ─── Speaker Badge ────────────────────────────────────────────────

function SpeakerBadge({
  speaker,
  allSpeakers,
  onChange,
  small,
}: {
  speaker: string;
  allSpeakers: string[];
  onChange: (s: string) => void;
  small?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className={`inline-flex items-center gap-1 rounded-full font-medium ${small ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"}`}
        style={{
          background: `${getSpeakerColor(speaker)}22`,
          color: getSpeakerColor(speaker),
          border: `1px solid ${getSpeakerColor(speaker)}44`,
        }}
      >
        {speaker}
        <ChevronDown size={small ? 10 : 12} />
      </button>
      {open && (
        <div
          className="absolute top-full left-0 mt-1 rounded-lg shadow-xl z-50 min-w-[120px] py-1"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          {allSpeakers.map((s) => (
            <button
              key={s}
              onClick={() => { onChange(s); setOpen(false); }}
              className={`w-full text-left px-3 py-1.5 text-xs hover:opacity-80 flex items-center gap-2 ${s === speaker ? "font-bold" : ""}`}
            >
              <span
                className="w-2 h-2 rounded-full inline-block"
                style={{ background: getSpeakerColor(s) }}
              />
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────

export default function TranscriptPage() {
  const [data, setData] = useState<TranscriptData | null>(null);
  const [speakers, setSpeakers] = useState<SpeakerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpeakerFilter, setSelectedSpeakerFilter] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  // Merge modal
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeSource, setMergeSource] = useState("");
  const [mergeTarget, setMergeTarget] = useState("");

  // Fix words modal
  const [fixWordsOpen, setFixWordsOpen] = useState(false);
  const [wordPairs, setWordPairs] = useState<{ find: string; replace: string }[]>([
    { find: "", replace: "" },
  ]);
  const [fixWordsWorking, setFixWordsWorking] = useState(false);
  const [fixWordsResult, setFixWordsResult] = useState<string | null>(null);

  // Video ref
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [inputVideos, setInputVideos] = useState<InputVideoInfo[]>([]);
  const [selectedVideoName, setSelectedVideoName] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [t, sp, videos] = await Promise.all([
        transcriptApi.get(),
        transcriptApi.getSpeakers(),
        pipelineApi.listInputVideos(),
      ]);
      setData(t.data);
      setSpeakers(sp);
      setInputVideos(videos);
      if (videos.length > 0 && !selectedVideoName) {
        // Use the active video from localStorage, or the first one
        const saved = localStorage.getItem("autoshorts_active_video");
        const pick = saved && videos.some((v) => v.name === saved) ? saved : videos[0].name;
        setSelectedVideoName(pick);
        setVideoSrc(media.fileUrl("input", pick));
      }
    } catch {
      // no transcript yet
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const allSpeakers = useMemo(() => {
    if (!data) return [];
    const set = new Set<string>();
    data.segments.forEach((seg) => {
      seg.words.forEach((w) => { if (w.speaker) set.add(w.speaker); });
      if (seg.speaker) set.add(seg.speaker);
    });
    return Array.from(set).sort();
  }, [data]);

  const filteredSegments = useMemo(() => {
    if (!data) return [];
    return data.segments.filter((seg, _i) => {
      if (selectedSpeakerFilter && seg.speaker !== selectedSpeakerFilter) {
        // Check if any word in segment matches speaker
        const hasWord = seg.words.some((w) => w.speaker === selectedSpeakerFilter);
        if (!hasWord && seg.speaker !== selectedSpeakerFilter) return false;
      }
      if (searchQuery) {
        return seg.text.toLowerCase().includes(searchQuery.toLowerCase());
      }
      return true;
    });
  }, [data, selectedSpeakerFilter, searchQuery]);

  // Update a segment's speaker (all words)
  const updateSegmentSpeaker = (segIndex: number, newSpeaker: string) => {
    if (!data) return;
    const updated = { ...data };
    const realIndex = data.segments.indexOf(filteredSegments[segIndex]);
    const seg = { ...updated.segments[realIndex] };
    seg.speaker = newSpeaker;
    seg.words = seg.words.map((w) => ({ ...w, speaker: newSpeaker }));
    updated.segments = [...updated.segments];
    updated.segments[realIndex] = seg;
    setData(updated);
    setDirty(true);
  };

  // Update a single word's speaker
  const updateWordSpeaker = (segFilterIdx: number, wordIdx: number, newSpeaker: string) => {
    if (!data) return;
    const updated = { ...data };
    const realIndex = data.segments.indexOf(filteredSegments[segFilterIdx]);
    const seg = { ...updated.segments[realIndex] };
    seg.words = [...seg.words];
    seg.words[wordIdx] = { ...seg.words[wordIdx], speaker: newSpeaker };
    updated.segments = [...updated.segments];
    updated.segments[realIndex] = seg;
    setData(updated);
    setDirty(true);
  };

  // Bulk merge speakers
  const handleMerge = async () => {
    if (!mergeSource || !mergeTarget) return;
    try {
      await transcriptApi.bulkRename(mergeSource, mergeTarget);
      setMergeOpen(false);
      setMergeSource("");
      setMergeTarget("");
      setDirty(false);
      refresh();
    } catch (e) {
      alert("Error merging speakers");
    }
  };

  // Save transcript
  const handleSave = async () => {
    if (!data) return;
    setSaving(true);
    try {
      await transcriptApi.save(data);
      setDirty(false);
      // Refresh speaker info
      const sp = await transcriptApi.getSpeakers();
      setSpeakers(sp);
    } catch {
      alert("Error saving transcript");
    } finally {
      setSaving(false);
    }
  };

  // Fix consistency
  const handleFixConsistency = async () => {
    try {
      await transcriptApi.fixConsistency();
      refresh();
    } catch {
      alert("Error fixing consistency");
    }
  };

  // Fix words
  const handleFixWords = async () => {
    const validPairs = wordPairs.filter((p) => p.find.trim());
    if (!validPairs.length) return;
    setFixWordsWorking(true);
    setFixWordsResult(null);
    try {
      const res = await transcriptApi.replaceWords(validPairs);
      setFixWordsResult(res.message);
      setDirty(false);
      refresh();
    } catch {
      setFixWordsResult("Error applying replacements");
    } finally {
      setFixWordsWorking(false);
    }
  };

  // Seek video to timestamp
  const seekTo = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm" style={{ color: "var(--muted)" }}>Loading transcript...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-sm" style={{ color: "var(--muted)" }}>No transcript found.</p>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Run Step 1 (Transcribe) from the Pipeline page first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold">Transcript Editor</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {data.segments.length} segments · {allSpeakers.length} speakers
            {dirty && <span className="ml-2 text-xs" style={{ color: "var(--error)" }}>· Unsaved changes</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMergeOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <Merge size={14} /> Merge Speakers
          </button>
          <button
            onClick={() => {
              setFixWordsResult(null);
              setWordPairs([{ find: "", replace: "" }]);
              setFixWordsOpen(true);
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <Replace size={14} /> Fix Words
          </button>
          <button
            onClick={handleFixConsistency}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <Wand2 size={14} /> Fix Consistency
          </button>
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-40"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            <Save size={14} /> {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      {/* Video + Controls row */}
      <div className="flex gap-4 flex-shrink-0">
        {/* Video player */}
        {videoSrc && (
          <div className="flex-shrink-0" style={{ width: 320 }}>
            {inputVideos.length > 1 && (
              <select
                value={selectedVideoName || ""}
                onChange={(e) => {
                  setSelectedVideoName(e.target.value);
                  setVideoSrc(media.fileUrl("input", e.target.value));
                }}
                className="w-full rounded px-2 py-1 text-xs mb-1"
                style={{ background: "var(--background)", border: "1px solid var(--border)" }}
              >
                {inputVideos.map((v) => (
                  <option key={v.name} value={v.name}>{v.name}</option>
                ))}
              </select>
            )}
            <div className="rounded-lg overflow-hidden" style={{ background: "var(--card)" }}>
              <video
                ref={videoRef}
                src={videoSrc}
                controls
                className="w-full"
                onTimeUpdate={() => {
                  if (videoRef.current) setCurrentTime(videoRef.current.currentTime);
                }}
              />
            </div>
          </div>
        )}

        {/* Speaker Legend + Filters */}
        <div className="flex-1 space-y-3">
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--muted)" }} />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transcript..."
              className="w-full rounded-lg pl-9 pr-3 py-2 text-sm"
              style={{ background: "var(--card)", border: "1px solid var(--border)" }}
            />
          </div>

          {/* Speaker filter chips */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedSpeakerFilter(null)}
              className={`px-2.5 py-1 rounded-full text-xs transition-colors ${!selectedSpeakerFilter ? "font-bold" : ""}`}
              style={{
                background: !selectedSpeakerFilter ? "var(--accent)" : "var(--card)",
                color: !selectedSpeakerFilter ? "#fff" : "var(--foreground)",
                border: "1px solid var(--border)",
              }}
            >
              All
            </button>
            {allSpeakers.map((s) => (
              <button
                key={s}
                onClick={() => setSelectedSpeakerFilter(selectedSpeakerFilter === s ? null : s)}
                className="px-2.5 py-1 rounded-full text-xs transition-colors"
                style={{
                  background: selectedSpeakerFilter === s ? `${getSpeakerColor(s)}33` : "var(--card)",
                  color: getSpeakerColor(s),
                  border: `1px solid ${selectedSpeakerFilter === s ? getSpeakerColor(s) : "var(--border)"}`,
                }}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Speaker stats */}
          <div className="grid grid-cols-2 gap-2">
            {speakers.slice(0, 6).map((sp) => (
              <div key={sp.speaker_id} className="flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg"
                style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                <span className="w-2 h-2 rounded-full" style={{ background: getSpeakerColor(sp.speaker_id) }} />
                <span className="font-medium flex-1">{sp.speaker_id}</span>
                <span style={{ color: "var(--muted)" }}>{sp.word_count} words · {fmtTime(sp.total_talk_time)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Transcript segments */}
      <div className="flex-1 overflow-y-auto space-y-1 min-h-0" style={{ maxHeight: "calc(100vh - 380px)" }}>
        {filteredSegments.map((seg, i) => {
          const isActive = currentTime >= seg.start && currentTime <= seg.end;
          return (
            <div
              key={i}
              className={`flex gap-3 rounded-lg p-3 transition-colors ${isActive ? "ring-1" : ""}`}
              style={{
                background: isActive ? "rgba(99,102,241,0.08)" : "transparent",

              }}
            >
              {/* Timestamp */}
              <button
                onClick={() => seekTo(seg.start)}
                className="text-xs font-mono flex-shrink-0 w-12 text-right pt-0.5 hover:underline"
                style={{ color: "var(--muted)" }}
                title="Click to seek"
              >
                {fmtTime(seg.start)}
              </button>

              {/* Speaker badge */}
              <div className="flex-shrink-0 w-24">
                <SpeakerBadge
                  speaker={seg.speaker || seg.words[0]?.speaker || "UNKNOWN"}
                  allSpeakers={allSpeakers}
                  onChange={(s) => updateSegmentSpeaker(i, s)}
                />
              </div>

              {/* Text with clickable words */}
              <div className="flex-1 text-sm leading-relaxed">
                {seg.words.map((w, wi) => {
                  const wordActive = currentTime >= w.start && currentTime <= w.end;
                  return (
                    <span
                      key={wi}
                      className={`inline cursor-pointer hover:underline ${wordActive ? "font-bold" : ""}`}
                      style={{
                        color: wordActive ? "var(--accent)" : undefined,
                        borderBottom: w.speaker !== (seg.speaker || seg.words[0]?.speaker) ? `2px solid ${getSpeakerColor(w.speaker)}` : undefined,
                      }}
                      onClick={() => seekTo(w.start)}
                      onContextMenu={(e) => {
                        e.preventDefault();
                        // Could open word-level speaker change, but for simplicity use tooltip
                      }}
                      title={`${w.speaker} (${fmtTime(w.start)} - ${fmtTime(w.end)}) score: ${w.score.toFixed(2)}`}
                    >
                      {w.word}{" "}
                    </span>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Fix Words Modal */}
      {fixWordsOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.6)" }}>
          <div className="rounded-xl p-6 w-[480px] space-y-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Replace size={18} /> Fix Words
            </h3>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Find and replace words or phrases across the entire transcript.
              Matching is case-insensitive; the replacement will use the casing you type.
            </p>

            {/* Pairs list */}
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {wordPairs.map((pair, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    value={pair.find}
                    onChange={(e) => {
                      const updated = [...wordPairs];
                      updated[i] = { ...updated[i], find: e.target.value };
                      setWordPairs(updated);
                    }}
                    placeholder="Find…"
                    className="flex-1 rounded px-2 py-1.5 text-xs"
                    style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                  />
                  <span className="text-xs" style={{ color: "var(--muted)" }}>→</span>
                  <input
                    value={pair.replace}
                    onChange={(e) => {
                      const updated = [...wordPairs];
                      updated[i] = { ...updated[i], replace: e.target.value };
                      setWordPairs(updated);
                    }}
                    placeholder="Replace with…"
                    className="flex-1 rounded px-2 py-1.5 text-xs"
                    style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                  />
                  <button
                    onClick={() => setWordPairs(wordPairs.filter((_, j) => j !== i))}
                    className="p-1 rounded hover:opacity-70"
                    style={{ color: "var(--muted)" }}
                    title="Remove"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setWordPairs([...wordPairs, { find: "", replace: "" }])}
              className="flex items-center gap-1.5 text-xs hover:opacity-70"
              style={{ color: "var(--accent)" }}
            >
              <Plus size={13} /> Add pair
            </button>

            {fixWordsResult && (
              <p className="text-xs px-2 py-1.5 rounded" style={{ background: "var(--background)", color: "var(--muted)" }}>
                {fixWordsResult}
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => { setFixWordsOpen(false); setFixWordsResult(null); }}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ border: "1px solid var(--border)" }}
              >
                Close
              </button>
              <button
                onClick={handleFixWords}
                disabled={fixWordsWorking || !wordPairs.some((p) => p.find.trim())}
                className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-40"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                {fixWordsWorking ? "Applying..." : "Apply"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Merge Modal */}
      {mergeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.6)" }}>
          <div className="rounded-xl p-6 w-[400px] space-y-4" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Users size={18} /> Merge Speakers
            </h3>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              All words from the source speaker will be reassigned to the target speaker.
              This is useful when the AI detected more speakers than actually exist.
            </p>
            <label className="block">
              <span className="text-xs mb-1 block" style={{ color: "var(--muted)" }}>Source (will be removed)</span>
              <select
                value={mergeSource}
                onChange={(e) => setMergeSource(e.target.value)}
                className="w-full rounded px-3 py-2 text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)" }}
              >
                <option value="">Select speaker...</option>
                {allSpeakers.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs mb-1 block" style={{ color: "var(--muted)" }}>Target (will keep)</span>
              <select
                value={mergeTarget}
                onChange={(e) => setMergeTarget(e.target.value)}
                className="w-full rounded px-3 py-2 text-sm"
                style={{ background: "var(--background)", border: "1px solid var(--border)" }}
              >
                <option value="">Select speaker...</option>
                {allSpeakers.filter((s) => s !== mergeSource).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setMergeOpen(false)}
                className="px-4 py-2 rounded-lg text-sm"
                style={{ border: "1px solid var(--border)" }}
              >
                Cancel
              </button>
              <button
                onClick={handleMerge}
                disabled={!mergeSource || !mergeTarget}
                className="px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-40"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                Merge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
