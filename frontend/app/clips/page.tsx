"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Sparkles,
  Plus,
  Trash2,
  Save,
  Play,
  Clock,
  GripVertical,
  Copy,
  Download,
  ClipboardPaste,
  Check,
  FileText,
  Loader2,
  LetterText,
  Merge,
} from "lucide-react";
import type { WordData } from "@/lib/api";
import {
  clips as clipsApi,
  ClipData,
  media,
  transcript as transcriptApi,
  TranscriptData,
  TranscriptSegment,
  pipeline as pipelineApi,
  InputVideoInfo,
} from "@/lib/api";

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function ClipsPage() {
  const [clips, setClips] = useState<ClipData[]>([]);
  const [exists, setExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);

  // AI generate panel
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [genMode, setGenMode] = useState<"external" | "api">("external");

  // API mode state
  const [aiProvider, setAiProvider] = useState("openai");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiModel, setAiModel] = useState("gpt-4o");
  const [aiPromptType, setAiPromptType] = useState("clips");

  // Import mode: replace all clips or append to existing
  const [importMode, setImportMode] = useState<"replace" | "append">("replace");

  // External mode state
  const [extPromptType, setExtPromptType] = useState("clip");
  const [promptCopied, setPromptCopied] = useState(false);
  const [pastedResponse, setPastedResponse] = useState("");
  const [parsing, setParsing] = useState(false);

  // Preview
  const [previewClip, setPreviewClip] = useState<number | null>(null);
  const [videoSrc, setVideoSrc] = useState<string | null>(null);
  const [inputVideos, setInputVideos] = useState<InputVideoInfo[]>([]);
  const [selectedVideoName, setSelectedVideoName] = useState<string | null>(null);

  // Transcript
  const [transcriptData, setTranscriptData] = useState<TranscriptData | null>(null);
  const [transcriptDirty, setTranscriptDirty] = useState(false);
  const [savingTranscript, setSavingTranscript] = useState(false);
  const [showTranscript, setShowTranscript] = useState<number | null>(null);
  const [wordEditMode, setWordEditMode] = useState<Record<number, boolean>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await clipsApi.get();
      setClips(res.clips);
      setExists(res.exists);
      // Get videos for preview
      const videos = await pipelineApi.listInputVideos();
      setInputVideos(videos);
      if (videos.length > 0 && !selectedVideoName) {
        const saved = localStorage.getItem("autoshorts_active_video");
        const pick = saved && videos.some((v) => v.name === saved) ? saved : videos[0].name;
        setSelectedVideoName(pick);
        setVideoSrc(media.fileUrl("input", pick));
      }
      // Load transcript
      try {
        const t = await transcriptApi.get();
        setTranscriptData(t.data);
      } catch { /* no transcript */ }
    } catch {
      // no clips
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await clipsApi.update(clips);
      setDirty(false);
    } catch {
      alert("Error saving clips");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (idx: number) => {
    const updated = clips.filter((_, i) => i !== idx);
    // Re-number
    const renumbered = updated.map((c, i) => ({ ...c, clip_number: i + 1 }));
    setClips(renumbered);
    setDirty(true);
  };

  const handleAdd = () => {
    const newClip: ClipData = {
      clip_number: clips.length + 1,
      title: "New Clip",
      start_time: 0,
      end_time: 60,
      duration_seconds: 60,
      speakers: [],
      description: "",
      viral_potential: "",
      why_viral: "",
    };
    setClips([...clips, newClip]);
    setEditingIdx(clips.length);
    setDirty(true);
  };

  const handleGenerate = async () => {
    if (!aiApiKey) {
      alert("Please enter an API key");
      return;
    }
    setGenerating(true);
    try {
      const res = await clipsApi.generate({
        provider: aiProvider,
        api_key: aiApiKey,
        model: aiModel,
        prompt_type: aiPromptType,
      });
      if (res.clips && res.clips.length > 0) {
        if (importMode === "append" && clips.length > 0) {
          const offset = clips.length;
          const renumbered = res.clips.map((c, i) => ({ ...c, clip_number: offset + i + 1 }));
          setClips([...clips, ...renumbered]);
        } else {
          setClips(res.clips);
        }
        setDirty(true);
        setShowGenerateForm(false);
      }
    } catch (e) {
      alert("Error generating clips: " + (e instanceof Error ? e.message : ""));
    } finally {
      setGenerating(false);
    }
  };

  // ─── External Mode: copy prompt, download transcript, paste result
  const handleCopyPrompt = async () => {
    try {
      const prompt = await clipsApi.getPrompt(extPromptType);
      await navigator.clipboard.writeText(prompt);
      setPromptCopied(true);
      setTimeout(() => setPromptCopied(false), 2000);
    } catch (e) {
      alert("Error copying prompt: " + (e instanceof Error ? e.message : ""));
    }
  };

  const handleParseResponse = async () => {
    if (!pastedResponse.trim()) { alert("Paste the LLM response first"); return; }
    setParsing(true);
    try {
      const res = await clipsApi.parseResponse(pastedResponse);
      if (res.clips && res.clips.length > 0) {
        if (importMode === "append" && clips.length > 0) {
          const offset = clips.length;
          const renumbered = res.clips.map((c, i) => ({ ...c, clip_number: offset + i + 1 }));
          setClips([...clips, ...renumbered]);
        } else {
          setClips(res.clips);
        }
        setDirty(true);
        setPastedResponse("");
        setShowGenerateForm(false);
      } else {
        alert("No clips found in the response");
      }
    } catch (e) {
      alert("Error parsing response: " + (e instanceof Error ? e.message : ""));
    } finally {
      setParsing(false);
    }
  };

  const updateClip = (idx: number, field: keyof ClipData, value: unknown) => {
    const updated = [...clips];
    updated[idx] = { ...updated[idx], [field]: value };
    if (field === "start_time" || field === "end_time") {
      updated[idx].duration_seconds =
        (updated[idx].end_time || 0) - (updated[idx].start_time || 0);
    }
    setClips(updated);
    setDirty(true);
  };

  // Get transcript segments that overlap with a clip's time range
  const getClipSegments = (clip: ClipData): { seg: TranscriptSegment; idx: number }[] => {
    if (!transcriptData) return [];
    return transcriptData.segments
      .map((seg, idx) => ({ seg, idx }))
      .filter(({ seg }) => seg.end > clip.start_time && seg.start < clip.end_time);
  };

  // ─── LCS-based word alignment ────────────────────────────────────
  const normalize = (w: string) => w.replace(/[^a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]/g, "").toLowerCase();

  /** Compute LCS table and return matched index pairs (oldIdx, newIdx) */
  const lcsAlign = (oldW: string[], newW: string[]): [number, number][] => {
    const m = oldW.length, n = newW.length;
    const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++)
      for (let j = 1; j <= n; j++)
        dp[i][j] = normalize(oldW[i - 1]) === normalize(newW[j - 1])
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
    // Back-trace
    const pairs: [number, number][] = [];
    let i = m, j = n;
    while (i > 0 && j > 0) {
      if (normalize(oldW[i - 1]) === normalize(newW[j - 1])) {
        pairs.push([i - 1, j - 1]);
        i--; j--;
      } else if (dp[i - 1][j] >= dp[i][j - 1]) {
        i--;
      } else {
        j--;
      }
    }
    return pairs.reverse();
  };

  // Update a segment's text and rebuild its word list with LCS alignment
  const updateSegmentText = (segIdx: number, newText: string) => {
    if (!transcriptData) return;
    const updated = { ...transcriptData };
    const seg = { ...updated.segments[segIdx] };
    seg.text = newText;
    const newTokens = newText.split(/\s+/).filter(Boolean);
    const oldWords = seg.words;
    const oldTokens = oldWords.map(w => w.word);

    // LCS alignment: find which old words match which new words
    const matches = lcsAlign(oldTokens, newTokens);
    const oldMatched = new Map<number, number>(); // oldIdx → newIdx
    const newMatched = new Map<number, number>(); // newIdx → oldIdx
    for (const [oi, ni] of matches) {
      oldMatched.set(oi, ni);
      newMatched.set(ni, oi);
    }

    // Build result words
    const result: WordData[] = new Array(newTokens.length);

    // 1. Place matched words (keep original timing)
    for (const [oi, ni] of matches) {
      result[ni] = { ...oldWords[oi], word: newTokens[ni] };
    }

    // 2. Fill unmatched new words — find surrounding timing context
    for (let ni = 0; ni < newTokens.length; ni++) {
      if (result[ni]) continue;
      // Find the contiguous run of unmatched new indices
      let runStart = ni;
      let runEnd = ni;
      while (runEnd + 1 < newTokens.length && !result[runEnd + 1]) runEnd++;
      const runLen = runEnd - runStart + 1;

      // Time range: from previous matched word's end to next matched word's start
      let tStart = seg.start;
      let tEnd = seg.end;
      for (let k = runStart - 1; k >= 0; k--) {
        if (result[k]) { tStart = result[k].end; break; }
      }
      for (let k = runEnd + 1; k < newTokens.length; k++) {
        if (result[k]) { tEnd = result[k].start; break; }
      }

      // Also check if there are old words in the same region to steal their span
      // Find old words that were between the same matched anchors
      const prevMatchOld = (() => {
        for (let k = runStart - 1; k >= 0; k--) {
          const oi2 = newMatched.get(k);
          if (oi2 !== undefined) return oi2;
        }
        return -1;
      })();
      const nextMatchOld = (() => {
        for (let k = runEnd + 1; k < newTokens.length; k++) {
          const oi2 = newMatched.get(k);
          if (oi2 !== undefined) return oi2;
        }
        return oldWords.length;
      })();
      // Old words in the gap that weren't matched
      const gapOld = oldWords.filter((_, oi2) => oi2 > prevMatchOld && oi2 < nextMatchOld && !oldMatched.has(oi2));
      if (gapOld.length > 0) {
        tStart = Math.min(tStart, gapOld[0].start);
        tEnd = Math.max(tEnd, gapOld[gapOld.length - 1].end);
      }

      const span = tEnd - tStart;
      const wordDur = span / runLen;
      for (let r = 0; r < runLen; r++) {
        result[runStart + r] = {
          word: newTokens[runStart + r],
          start: parseFloat((tStart + r * wordDur).toFixed(3)),
          end: parseFloat((tStart + (r + 1) * wordDur).toFixed(3)),
          score: 0.5,
          speaker: oldWords[0]?.speaker || "UNKNOWN",
        };
      }
      ni = runEnd; // skip rest of run
    }

    seg.words = result;
    updated.segments = [...updated.segments];
    updated.segments[segIdx] = seg;
    setTranscriptData(updated);
    setTranscriptDirty(true);
  };

  // ─── Word-level mutation helpers ────────────────────────────────
  const mutateSegment = (segIdx: number, mutator: (seg: TranscriptSegment) => TranscriptSegment) => {
    if (!transcriptData) return;
    const updated = { ...transcriptData };
    updated.segments = [...updated.segments];
    updated.segments[segIdx] = mutator({ ...updated.segments[segIdx] });
    // Sync seg.text from words
    updated.segments[segIdx].text = updated.segments[segIdx].words.map(w => w.word).join(" ");
    setTranscriptData(updated);
    setTranscriptDirty(true);
  };

  const updateWordText = (segIdx: number, wordIdx: number, text: string) => {
    mutateSegment(segIdx, (seg) => {
      seg.words = [...seg.words];
      seg.words[wordIdx] = { ...seg.words[wordIdx], word: text };
      return seg;
    });
  };

  const updateWordTiming = (segIdx: number, wordIdx: number, field: "start" | "end", value: number) => {
    mutateSegment(segIdx, (seg) => {
      seg.words = [...seg.words];
      seg.words[wordIdx] = { ...seg.words[wordIdx], [field]: value };
      return seg;
    });
  };

  const deleteWord = (segIdx: number, wordIdx: number) => {
    mutateSegment(segIdx, (seg) => {
      seg.words = seg.words.filter((_, i) => i !== wordIdx);
      return seg;
    });
  };

  const mergeWithNext = (segIdx: number, wordIdx: number) => {
    mutateSegment(segIdx, (seg) => {
      if (wordIdx >= seg.words.length - 1) return seg;
      const w1 = seg.words[wordIdx];
      const w2 = seg.words[wordIdx + 1];
      const merged: WordData = {
        word: w1.word + " " + w2.word,
        start: w1.start,
        end: w2.end,
        score: Math.min(w1.score, w2.score),
        speaker: w1.speaker,
      };
      seg.words = [...seg.words];
      seg.words.splice(wordIdx, 2, merged);
      return seg;
    });
  };

  const addWordAfter = (segIdx: number, wordIdx: number) => {
    mutateSegment(segIdx, (seg) => {
      const prev = seg.words[wordIdx];
      const next = seg.words[wordIdx + 1];
      const newStart = prev ? prev.end : seg.start;
      const newEnd = next ? next.start : seg.end;
      const mid = (newStart + newEnd) / 2;
      const newWord: WordData = {
        word: "___",
        start: parseFloat(newStart.toFixed(3)),
        end: parseFloat(mid.toFixed(3)),
        score: 0.5,
        speaker: prev?.speaker || seg.words[0]?.speaker || "UNKNOWN",
      };
      seg.words = [...seg.words];
      seg.words.splice(wordIdx + 1, 0, newWord);
      return seg;
    });
  };

  const toggleWordEditMode = (segIdx: number) => {
    setWordEditMode(prev => ({ ...prev, [segIdx]: !prev[segIdx] }));
  };

  const handleSaveTranscript = async () => {
    if (!transcriptData) return;
    setSavingTranscript(true);
    try {
      await transcriptApi.save(transcriptData);
      setTranscriptDirty(false);
    } catch {
      alert("Error saving transcript");
    } finally {
      setSavingTranscript(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-sm" style={{ color: "var(--muted)" }}>Loading clips...</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Clips Editor</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            {clips.length} clip{clips.length !== 1 ? "s" : ""} defined
            {dirty && <span className="ml-2 text-xs" style={{ color: "var(--error)" }}>· Unsaved</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGenerateForm(!showGenerateForm)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <Sparkles size={14} /> AI Generate
          </button>
          <button
            onClick={handleAdd}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
            style={{ background: "var(--card)", border: "1px solid var(--border)" }}
          >
            <Plus size={14} /> Add Clip
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

      {/* Video Selector */}
      {inputVideos.length > 1 && (
        <div className="rounded-lg p-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <label className="flex items-center gap-3">
            <span className="text-xs font-medium flex-shrink-0" style={{ color: "var(--muted)" }}>Preview video</span>
            <select
              value={selectedVideoName || ""}
              onChange={(e) => {
                setSelectedVideoName(e.target.value);
                setVideoSrc(media.fileUrl("input", e.target.value));
              }}
              className="flex-1 rounded px-2 py-1 text-xs"
              style={{ background: "var(--background)", border: "1px solid var(--border)" }}
            >
              {inputVideos.map((v) => (
                <option key={v.name} value={v.name}>{v.name}</option>
              ))}
            </select>
          </label>
        </div>
      )}

      {/* AI Generate Panel */}
      {showGenerateForm && (
        <div className="rounded-lg overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          {/* Tab selector */}
          <div className="flex" style={{ borderBottom: "1px solid var(--border)" }}>
            <button
              onClick={() => setGenMode("external")}
              className="flex-1 px-4 py-2.5 text-xs font-medium transition-colors"
              style={{
                background: genMode === "external" ? "var(--background)" : "transparent",
                color: genMode === "external" ? "var(--foreground)" : "var(--muted)",
                borderBottom: genMode === "external" ? "2px solid var(--accent)" : "2px solid transparent",
              }}
            >
              External LLM (copy &amp; paste)
            </button>
            <button
              onClick={() => setGenMode("api")}
              className="flex-1 px-4 py-2.5 text-xs font-medium transition-colors"
              style={{
                background: genMode === "api" ? "var(--background)" : "transparent",
                color: genMode === "api" ? "var(--foreground)" : "var(--muted)",
                borderBottom: genMode === "api" ? "2px solid var(--accent)" : "2px solid transparent",
              }}
            >
              API Key (automatic)
            </button>
          </div>

          <div className="p-4 space-y-3">
            {/* ─── External LLM Tab ─────────────────────────────── */}
            {genMode === "external" && (
              <>
                <p className="text-xs" style={{ color: "var(--muted)" }}>
                  Copy the prompt and download the transcript, then paste them into ChatGPT, Claude, or any LLM.
                  Paste the JSON response below to import the clips.
                </p>

                {/* Step 1 & 2: Prompt + Transcript */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <label className="block">
                      <span className="text-xs" style={{ color: "var(--muted)" }}>Prompt Type</span>
                      <select
                        value={extPromptType}
                        onChange={(e) => setExtPromptType(e.target.value)}
                        className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                      >
                        <option value="clip">Clip Extraction</option>
                        <option value="hook">Hook Extraction</option>
                      </select>
                    </label>
                    <button
                      onClick={handleCopyPrompt}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors"
                      style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                    >
                      {promptCopied ? <Check size={14} style={{ color: "var(--success)" }} /> : <Copy size={14} />}
                      {promptCopied ? "Copied!" : "Step 1: Copy Prompt"}
                    </button>
                  </div>
                  <div className="flex flex-col justify-end gap-2">
                    <a
                      href={clipsApi.transcriptDownloadUrl()}
                      download
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors text-center"
                      style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--foreground)", textDecoration: "none" }}
                    >
                      <Download size={14} />
                      Step 2: Download Transcript
                    </a>
                    <p className="text-[10px] text-center" style={{ color: "var(--muted)" }}>
                      Detailed transcript with timestamps
                    </p>
                  </div>
                </div>

                {/* Step 3: Paste response */}
                <label className="block">
                  <span className="text-xs" style={{ color: "var(--muted)" }}>
                    Step 3: Paste the LLM response (JSON)
                  </span>
                  <textarea
                    value={pastedResponse}
                    onChange={(e) => setPastedResponse(e.target.value)}
                    rows={6}
                    placeholder={'Paste the JSON response from the LLM here...\n[\n  {\n    "clip_number": 1,\n    "title": "...",\n    "start_time": 120,\n    "end_time": 180\n  }\n]'}
                    className="mt-1 w-full rounded px-3 py-2 text-xs font-mono resize-y"
                    style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                  />
                </label>

                {/* Import mode toggle */}
                <div className="flex items-center gap-3 rounded-lg px-3 py-2" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                  <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>Import mode:</span>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" name="importMode" value="replace" checked={importMode === "replace"} onChange={() => setImportMode("replace")} className="accent-[var(--accent)]" />
                    <span className="text-xs">Replace all</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" name="importMode" value="append" checked={importMode === "append"} onChange={() => setImportMode("append")} className="accent-[var(--accent)]" />
                    <span className="text-xs">Append to existing{clips.length > 0 ? ` (${clips.length} clips)` : ""}</span>
                  </label>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowGenerateForm(false)}
                    className="px-3 py-1.5 rounded-lg text-xs"
                    style={{ border: "1px solid var(--border)" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleParseResponse}
                    disabled={parsing || !pastedResponse.trim()}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
                    style={{ background: "var(--accent)", color: "#fff" }}
                  >
                    <ClipboardPaste size={14} />
                    {parsing ? "Parsing..." : importMode === "append" ? "Append Clips" : "Import Clips"}
                  </button>
                </div>
              </>
            )}

            {/* ─── API Key Tab ──────────────────────────────────── */}
            {genMode === "api" && (
              <>
                <p className="text-xs" style={{ color: "var(--muted)" }}>
                  Enter your API key to automatically send the transcript to an LLM and receive clips.
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <label className="block">
                    <span className="text-xs" style={{ color: "var(--muted)" }}>Provider</span>
                    <select
                      value={aiProvider}
                      onChange={(e) => {
                        setAiProvider(e.target.value);
                        setAiModel(e.target.value === "openai" ? "gpt-4o" : "claude-sonnet-4-20250514");
                      }}
                      className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                      style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                    >
                      <option value="openai">OpenAI</option>
                      <option value="anthropic">Anthropic</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs" style={{ color: "var(--muted)" }}>Model</span>
                    <input
                      value={aiModel}
                      onChange={(e) => setAiModel(e.target.value)}
                      className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                      style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                    />
                  </label>
                  <label className="block col-span-2">
                    <span className="text-xs" style={{ color: "var(--muted)" }}>API Key</span>
                    <input
                      type="password"
                      value={aiApiKey}
                      onChange={(e) => setAiApiKey(e.target.value)}
                      placeholder="sk-..."
                      className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                      style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                    />
                  </label>
                  <label className="block">
                    <span className="text-xs" style={{ color: "var(--muted)" }}>Prompt Type</span>
                    <select
                      value={aiPromptType}
                      onChange={(e) => setAiPromptType(e.target.value)}
                      className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                      style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                    >
                      <option value="clips">Clips</option>
                      <option value="hooks">Hooks</option>
                    </select>
                  </label>
                </div>
                {/* Import mode toggle */}
                <div className="flex items-center gap-3 rounded-lg px-3 py-2" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
                  <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>Import mode:</span>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" name="importMode" value="replace" checked={importMode === "replace"} onChange={() => setImportMode("replace")} className="accent-[var(--accent)]" />
                    <span className="text-xs">Replace all</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input type="radio" name="importMode" value="append" checked={importMode === "append"} onChange={() => setImportMode("append")} className="accent-[var(--accent)]" />
                    <span className="text-xs">Append to existing{clips.length > 0 ? ` (${clips.length} clips)` : ""}</span>
                  </label>
                </div>

                <div className="flex justify-end gap-2 pt-1">
                  <button
                    onClick={() => setShowGenerateForm(false)}
                    className="px-3 py-1.5 rounded-lg text-xs"
                    style={{ border: "1px solid var(--border)" }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleGenerate}
                    disabled={generating || !aiApiKey}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium disabled:opacity-40"
                    style={{ background: "var(--accent)", color: "#fff" }}
                  >
                    {generating ? "Generating..." : importMode === "append" ? "Generate & Append" : "Generate Clips"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Clips List */}
      {clips.length === 0 ? (
        <div
          className="rounded-lg p-8 text-center"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            No clips defined. Use AI Generate or add clips manually.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {clips.map((clip, i) => {
            const isEditing = editingIdx === i;
            return (
              <div
                key={i}
                className="rounded-lg overflow-hidden"
                style={{ background: "var(--card)", border: "1px solid var(--border)" }}
              >
                {/* Clip header */}
                <div
                  className="flex items-center gap-3 p-3 cursor-pointer"
                  onClick={() => setEditingIdx(isEditing ? null : i)}
                >
                  <GripVertical size={14} style={{ color: "var(--muted)" }} />
                  <span className="text-xs font-mono w-6 text-center" style={{ color: "var(--muted)" }}>
                    #{clip.clip_number}
                  </span>
                  <span className="flex-1 text-sm font-medium truncate">{clip.title}</span>
                  <span className="text-xs flex items-center gap-1" style={{ color: "var(--muted)" }}>
                    <Clock size={12} />
                    {fmtTime(clip.start_time)} - {fmtTime(clip.end_time)}
                    ({fmtTime(clip.duration_seconds || 0)})
                  </span>
                  {clip.viral_potential && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full"
                      style={{
                        background: clip.viral_potential === "high" ? "rgba(34,197,94,0.15)" :
                          clip.viral_potential === "medium" ? "rgba(245,158,11,0.15)" : "var(--background)",
                        color: clip.viral_potential === "high" ? "var(--success)" :
                          clip.viral_potential === "medium" ? "#f59e0b" : "var(--muted)",
                      }}>
                      {clip.viral_potential}
                    </span>
                  )}
                  {videoSrc && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewClip(previewClip === i ? null : i);
                      }}
                      className="p-1 rounded hover:opacity-80"
                      style={{ color: "var(--accent)" }}
                    >
                      <Play size={14} />
                    </button>
                  )}
                  {transcriptData && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowTranscript(showTranscript === i ? null : i);
                      }}
                      className="p-1 rounded hover:opacity-80"
                      style={{ color: showTranscript === i ? "var(--accent)" : "var(--muted)" }}
                      title="Show transcript"
                    >
                      <FileText size={14} />
                    </button>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(i);
                    }}
                    className="p-1 rounded hover:opacity-80"
                    style={{ color: "var(--error)" }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* Edit panel */}
                {isEditing && (
                  <div className="px-4 pb-4 space-y-3" style={{ borderTop: "1px solid var(--border)" }}>
                    <div className="grid grid-cols-2 gap-3 pt-3">
                      <label className="block col-span-2">
                        <span className="text-xs" style={{ color: "var(--muted)" }}>Title</span>
                        <input
                          value={clip.title}
                          onChange={(e) => updateClip(i, "title", e.target.value)}
                          className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                          style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs" style={{ color: "var(--muted)" }}>Start Time (seconds)</span>
                        <input
                          type="number"
                          step="0.1"
                          value={clip.start_time}
                          onChange={(e) => updateClip(i, "start_time", parseFloat(e.target.value))}
                          className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                          style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                        />
                      </label>
                      <label className="block">
                        <span className="text-xs" style={{ color: "var(--muted)" }}>End Time (seconds)</span>
                        <input
                          type="number"
                          step="0.1"
                          value={clip.end_time}
                          onChange={(e) => updateClip(i, "end_time", parseFloat(e.target.value))}
                          className="mt-1 w-full rounded px-2 py-1.5 text-sm"
                          style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                        />
                      </label>
                      <label className="block col-span-2">
                        <span className="text-xs" style={{ color: "var(--muted)" }}>Description</span>
                        <textarea
                          value={clip.description || ""}
                          onChange={(e) => updateClip(i, "description", e.target.value)}
                          rows={2}
                          className="mt-1 w-full rounded px-2 py-1.5 text-sm resize-none"
                          style={{ background: "var(--background)", border: "1px solid var(--border)" }}
                        />
                      </label>
                      {clip.why_viral && (
                        <div className="col-span-2 text-xs rounded-lg p-2"
                          style={{ background: "var(--background)", color: "var(--muted)" }}>
                          <strong>Why viral:</strong> {clip.why_viral}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Video preview */}
                {previewClip === i && videoSrc && (
                  <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--border)" }}>
                    <video
                      src={`${videoSrc}#t=${clip.start_time},${clip.end_time}`}
                      controls
                      autoPlay
                      className="w-full rounded-lg mt-3"
                      style={{ maxHeight: 200 }}
                    />
                  </div>
                )}

                {/* Transcript for this clip */}
                {showTranscript === i && transcriptData && (
                  <div className="px-4 pb-4" style={{ borderTop: "1px solid var(--border)" }}>
                    <div className="flex items-center justify-between mt-3 mb-2">
                      <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>
                        Transcript ({getClipSegments(clip).length} segments)
                      </span>
                      {transcriptDirty && (
                        <button
                          onClick={handleSaveTranscript}
                          disabled={savingTranscript}
                          className="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium disabled:opacity-40"
                          style={{ background: "var(--accent)", color: "#fff" }}
                        >
                          {savingTranscript ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />}
                          {savingTranscript ? "Saving..." : "Save Transcript"}
                        </button>
                      )}
                    </div>
                    {getClipSegments(clip).length === 0 ? (
                      <p className="text-xs" style={{ color: "var(--muted)" }}>No transcript segments in this time range.</p>
                    ) : (
                      <div className="space-y-1.5 max-h-[420px] overflow-y-auto">
                        {getClipSegments(clip).map(({ seg, idx }) => {
                          const isWordMode = !!wordEditMode[idx];
                          return (
                            <div key={idx} className="rounded p-2" style={{ background: "var(--background)" }}>
                              {/* Segment header: timestamp + speaker + mode toggle */}
                              <div className="flex gap-2 items-center mb-1">
                                <span className="text-[10px] font-mono flex-shrink-0 w-16 text-right" style={{ color: "var(--muted)" }}>
                                  {fmtTime(seg.start)}
                                </span>
                                {seg.speaker && (
                                  <span className="text-[10px] font-medium flex-shrink-0 w-20 truncate" style={{ color: "var(--accent)" }}>
                                    {seg.speaker}
                                  </span>
                                )}
                                <div className="flex-1" />
                                <button
                                  onClick={() => toggleWordEditMode(idx)}
                                  title={isWordMode ? "Switch to sentence edit" : "Switch to word timing edit"}
                                  className="p-0.5 rounded hover:opacity-80 transition-opacity"
                                  style={{ color: isWordMode ? "var(--accent)" : "var(--muted)" }}
                                >
                                  <LetterText size={13} />
                                </button>
                              </div>

                              {/* Sentence mode */}
                              {!isWordMode && (
                                <div className="pl-[88px]">
                                  <input
                                    value={seg.text}
                                    onChange={(e) => updateSegmentText(idx, e.target.value)}
                                    className="w-full text-xs bg-transparent outline-none px-1 py-0.5 rounded"
                                    style={{ border: "1px solid transparent" }}
                                    onFocus={(e) => (e.target.style.borderColor = "var(--border)")}
                                    onBlur={(e) => (e.target.style.borderColor = "transparent")}
                                  />
                                </div>
                              )}

                              {/* Word timing mode */}
                              {isWordMode && (
                                <div className="flex flex-wrap gap-1 mt-1 items-start">
                                  {seg.words.map((w, wi) => (
                                    <div key={`${idx}-${wi}`} className="group relative">
                                      <div
                                        className="rounded px-1.5 py-1 flex flex-col items-center gap-0.5"
                                        style={{
                                          background: "var(--card)",
                                          border: `1px solid ${w.score < 0.6 ? "var(--warning, #f59e0b)" : "var(--border)"}`,
                                          minWidth: 48,
                                        }}
                                      >
                                        {/* Word text */}
                                        <input
                                          value={w.word}
                                          onChange={(e) => updateWordText(idx, wi, e.target.value)}
                                          className="text-[11px] text-center bg-transparent outline-none w-full font-medium"
                                          style={{ maxWidth: Math.max(40, w.word.length * 7 + 12) }}
                                        />
                                        {/* Timing inputs */}
                                        <div className="flex items-center gap-0.5">
                                          <input
                                            type="number"
                                            step="0.01"
                                            value={parseFloat(w.start.toFixed(2))}
                                            onChange={(e) => updateWordTiming(idx, wi, "start", parseFloat(e.target.value) || 0)}
                                            className="text-[9px] font-mono bg-transparent outline-none text-center rounded"
                                            style={{ width: 42, color: "var(--muted)", border: "1px solid transparent" }}
                                            onFocus={(e) => (e.target.style.borderColor = "var(--border)")}
                                            onBlur={(e) => (e.target.style.borderColor = "transparent")}
                                          />
                                          <span className="text-[8px]" style={{ color: "var(--muted)" }}>-</span>
                                          <input
                                            type="number"
                                            step="0.01"
                                            value={parseFloat(w.end.toFixed(2))}
                                            onChange={(e) => updateWordTiming(idx, wi, "end", parseFloat(e.target.value) || 0)}
                                            className="text-[9px] font-mono bg-transparent outline-none text-center rounded"
                                            style={{ width: 42, color: "var(--muted)", border: "1px solid transparent" }}
                                            onFocus={(e) => (e.target.style.borderColor = "var(--border)")}
                                            onBlur={(e) => (e.target.style.borderColor = "transparent")}
                                          />
                                        </div>
                                        {/* Action buttons on hover */}
                                        <div className="absolute -top-3 right-0 hidden group-hover:flex gap-0.5 rounded px-0.5"
                                          style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
                                          {wi < seg.words.length - 1 && (
                                            <button
                                              onClick={() => mergeWithNext(idx, wi)}
                                              title="Merge with next word"
                                              className="p-0.5 rounded hover:opacity-80"
                                              style={{ color: "var(--accent)" }}
                                            >
                                              <Merge size={10} />
                                            </button>
                                          )}
                                          <button
                                            onClick={() => deleteWord(idx, wi)}
                                            title="Delete word"
                                            className="p-0.5 rounded hover:opacity-80"
                                            style={{ color: "var(--error)" }}
                                          >
                                            <Trash2 size={10} />
                                          </button>
                                        </div>
                                      </div>
                                      {/* Add word button between chips */}
                                      {wi < seg.words.length - 1 && (
                                        <button
                                          onClick={() => addWordAfter(idx, wi)}
                                          title="Insert word here"
                                          className="absolute -right-2 top-1/2 -translate-y-1/2 z-10 hidden group-hover:flex items-center justify-center rounded-full"
                                          style={{
                                            width: 14, height: 14, fontSize: 10,
                                            background: "var(--accent)", color: "#fff",
                                          }}
                                        >
                                          +
                                        </button>
                                      )}
                                    </div>
                                  ))}
                                  {/* Add word at end */}
                                  <button
                                    onClick={() => addWordAfter(idx, seg.words.length - 1)}
                                    title="Add word at end"
                                    className="rounded px-2 py-1 text-[10px] self-center hover:opacity-80"
                                    style={{ border: "1px dashed var(--border)", color: "var(--muted)" }}
                                  >
                                    + word
                                  </button>
                                </div>
                              )}

                              {/* Synthetic timing warning */}
                              {isWordMode && seg.words.some(w => w.score < 0.6) && (
                                <p className="text-[9px] mt-1 pl-1" style={{ color: "var(--warning, #f59e0b)" }}>
                                  ⚠ Yellow-bordered words have estimated timing — adjust manually for precise karaoke sync
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
