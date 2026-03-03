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
} from "lucide-react";
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
        setClips(res.clips);
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
        setClips(res.clips);
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

  // Update a segment's text and rebuild its word list
  const updateSegmentText = (segIdx: number, newText: string) => {
    if (!transcriptData) return;
    const updated = { ...transcriptData };
    const seg = { ...updated.segments[segIdx] };
    seg.text = newText;
    // Rebuild words preserving timing: distribute timing across new words
    const newWords = newText.split(/\s+/).filter(Boolean);
    const oldWords = seg.words;
    const segDuration = seg.end - seg.start;
    seg.words = newWords.map((word, i) => {
      // Try to reuse old word data if the word matches at same position
      if (i < oldWords.length && oldWords[i].word.replace(/[^a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]/g, "").toLowerCase() === word.replace(/[^a-zA-ZáéíóúñÁÉÍÓÚÑ0-9]/g, "").toLowerCase()) {
        return { ...oldWords[i], word };
      }
      // Otherwise distribute evenly
      const wordDuration = segDuration / newWords.length;
      return {
        word,
        start: seg.start + (i * wordDuration),
        end: seg.start + ((i + 1) * wordDuration),
        score: 0.8,
        speaker: oldWords[0]?.speaker || "UNKNOWN",
      };
    });
    updated.segments = [...updated.segments];
    updated.segments[segIdx] = seg;
    setTranscriptData(updated);
    setTranscriptDirty(true);
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
                    {parsing ? "Parsing..." : "Import Clips"}
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
                    {generating ? "Generating..." : "Generate Clips"}
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
                      <div className="space-y-1.5 max-h-64 overflow-y-auto">
                        {getClipSegments(clip).map(({ seg, idx }) => (
                          <div key={idx} className="flex gap-2 items-start rounded p-2"
                            style={{ background: "var(--background)" }}>
                            <span className="text-[10px] font-mono pt-1 flex-shrink-0 w-16 text-right" style={{ color: "var(--muted)" }}>
                              {fmtTime(seg.start)}
                            </span>
                            {seg.speaker && (
                              <span className="text-[10px] font-medium pt-1 flex-shrink-0 w-20 truncate" style={{ color: "var(--accent)" }}>
                                {seg.speaker}
                              </span>
                            )}
                            <input
                              value={seg.text}
                              onChange={(e) => updateSegmentText(idx, e.target.value)}
                              className="flex-1 text-xs bg-transparent outline-none px-1 py-0.5 rounded"
                              style={{ border: "1px solid transparent" }}
                              onFocus={(e) => (e.target.style.borderColor = "var(--border)")}
                              onBlur={(e) => (e.target.style.borderColor = "transparent")}
                            />
                          </div>
                        ))}
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
