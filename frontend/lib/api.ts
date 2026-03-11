/**
 * API client for the AutoShorts backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ─── Pipeline ─────────────────────────────────────────────────────

export interface PipelineStepStatus {
  step: number;
  name: string;
  status: string;
  description: string;
}

export interface PipelineStatus {
  steps: PipelineStepStatus[];
  input_video: string | null;
  input_video_duration: number | null;
  has_transcript: boolean;
  has_clips_json: boolean;
  output_counts: Record<string, number>;
}

export interface InputVideoInfo {
  name: string;
  size: number;
  width?: number;
  height?: number;
  duration?: number;
  codec?: string;
}

export const pipeline = {
  status: () => request<PipelineStatus>("/api/pipeline/status"),
  listInputVideos: () => request<InputVideoInfo[]>("/api/pipeline/input-videos"),
  deleteInputVideo: (name: string) =>
    request(`/api/pipeline/input-videos/${encodeURIComponent(name)}`, { method: "DELETE" }),
  runTranscribe: (config?: Record<string, unknown>, videoName?: string) =>
    request(`/api/pipeline/run/transcribe${videoName ? `?video_name=${encodeURIComponent(videoName)}` : ""}`, {
      method: "POST",
      body: config ? JSON.stringify(config) : undefined,
    }),
  runExtract: (videoName?: string) =>
    request(`/api/pipeline/run/extract${videoName ? `?video_name=${encodeURIComponent(videoName)}` : ""}`, { method: "POST" }),
  runCrop: (params: { num_speakers: number; scene_type?: string; dynamic_enabled?: boolean }) =>
    request(`/api/pipeline/run/crop?num_speakers=${params.num_speakers}${params.scene_type ? `&scene_type=${params.scene_type}` : ""}${params.dynamic_enabled !== undefined ? `&dynamic_enabled=${params.dynamic_enabled}` : ""}`, { method: "POST" }),
  runSubtitle: (style?: Record<string, unknown>) =>
    request("/api/pipeline/run/subtitle", {
      method: "POST",
      body: style ? JSON.stringify(style) : undefined,
    }),
  regenSubtitle: (filename: string, style?: Record<string, unknown>) =>
    request(`/api/pipeline/run/subtitle/${encodeURIComponent(filename)}`, {
      method: "POST",
      body: style ? JSON.stringify(style) : undefined,
    }),
  reset: () => request("/api/pipeline/reset", { method: "POST" }),
};

// ─── Transcript ───────────────────────────────────────────────────

export interface WordData {
  word: string;
  start: number;
  end: number;
  score: number;
  speaker: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
  words: WordData[];
  speaker?: string;
}

export interface TranscriptData {
  segments: TranscriptSegment[];
}

export interface SpeakerInfo {
  speaker_id: string;
  word_count: number;
  total_talk_time: number;
  segment_count: number;
}

export const transcript = {
  get: () => request<{ path: string; data: TranscriptData }>("/api/transcript"),
  getSpeakers: () => request<SpeakerInfo[]>("/api/transcript/speakers"),
  updateSegmentSpeaker: (index: number, speaker: string) =>
    request(`/api/transcript/segment/${index}`, {
      method: "PUT",
      body: JSON.stringify({ speaker }),
    }),
  bulkRename: (source: string, target: string) =>
    request("/api/transcript/speakers/bulk-rename", {
      method: "PUT",
      body: JSON.stringify({ source_speaker: source, target_speaker: target }),
    }),
  rename: (oldName: string, newName: string) =>
    request("/api/transcript/speakers/rename", {
      method: "PUT",
      body: JSON.stringify({ old_name: oldName, new_name: newName }),
    }),
  fixConsistency: () =>
    request("/api/transcript/fix-consistency", { method: "POST" }),
  replaceWords: (replacements: { find: string; replace: string }[]) =>
    request<{ message: string; total_replaced: number }>(
      "/api/transcript/replace-words",
      { method: "POST", body: JSON.stringify({ replacements }) }
    ),
  save: (data: TranscriptData) =>
    request("/api/transcript/save", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ─── Clips ────────────────────────────────────────────────────────

export interface ClipData {
  clip_number: number;
  title: string;
  start_time: number;
  end_time: number;
  duration_seconds?: number;
  speakers?: string[];
  description?: string;
  viral_potential?: string;
  why_viral?: string;
  hook?: string;
}

export const clips = {
  get: () => request<{ clips: ClipData[]; exists: boolean }>("/api/clips"),
  update: (clipList: ClipData[]) =>
    request("/api/clips", {
      method: "PUT",
      body: JSON.stringify({ clips: clipList }),
    }),
  delete: (index: number) =>
    request(`/api/clips/${index}`, { method: "DELETE" }),
  generate: (config: {
    provider: string;
    api_key: string;
    model: string;
    prompt_type?: string;
  }) =>
    request<{ clips?: ClipData[]; hooks?: unknown[] }>("/api/clips/generate", {
      method: "POST",
      body: JSON.stringify({ config }),
    }),
  /** Get prompt template text for external LLM use */
  getPrompt: async (promptType: string): Promise<string> => {
    const res = await fetch(`${API_BASE}/api/clips/prompt/${promptType}`);
    if (!res.ok) throw new Error(await res.text());
    return res.text();
  },
  /** URL to download the detailed transcript file */
  transcriptDownloadUrl: () => `${API_BASE}/api/clips/transcript-download`,
  /** Parse raw LLM response into structured clips */
  parseResponse: (llmResponse: string) =>
    request<{ clips: ClipData[] }>("/api/clips/parse-response", {
      method: "POST",
      body: JSON.stringify({ llm_response: llmResponse }),
    }),
};

// ─── Media ────────────────────────────────────────────────────────

export interface FileInfo {
  name: string;
  size: number;
  width?: number;
  height?: number;
  duration?: number;
  codec?: string;
}

export const media = {
  upload: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/media/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  listFiles: (stage: string) => request<FileInfo[]>(`/api/media/list/${stage}`),
  inputInfo: () => request<FileInfo & { exists: boolean }>("/api/media/input-info"),
  fileUrl: (stage: string, filename: string) => `${API_BASE}/api/media/file/${stage}/${filename}`,
  thumbnailUrl: (stage: string, filename: string) => `${API_BASE}/api/media/thumbnail/${stage}/${filename}`,
};

// ─── Tools ────────────────────────────────────────────────────────

// ─── Editor / Composition types ───────────────────────────────────

export interface CropRegion {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type ContentLayout = "fullscreen" | "split_top" | "split_bottom";

export interface ContentSegment {
  start: number;
  end: number;
  content_region: CropRegion;
  speaker_region?: CropRegion | null;
  layout: ContentLayout;
}

export interface EditorRenderRequest {
  video_path: string;
  segments: ContentSegment[];
  default_speaker_region: CropRegion;
  output_name?: string;
  output_width?: number;
  output_height?: number;
}

export interface EditorVideoInfo {
  name: string;
  path: string;
  width: number;
  height: number;
  duration: number;
  codec: string;
  size: number;
}

export interface EditorComposition {
  video_path: string;
  segments: ContentSegment[];
  default_speaker_region?: CropRegion | null;
  output_width?: number;
  output_height?: number;
}

export const tools = {
  cutVideo: (params: { video_path: string; start_time: number; end_time: number; output_name?: string; output_to_input?: boolean }) =>
    request("/api/tools/cut-video", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  addMusic: (params: {
    video_path: string;
    music_path: string;
    output_name?: string;
    music_db?: number;
    fade_in?: number;
    start_delay_seconds?: number;
    output_to_input?: boolean;
  }) =>
    request("/api/tools/add-music", {
      method: "POST",
      body: JSON.stringify(params),
    }),
  cleanOutput: () =>
    request("/api/tools/clean-output", { method: "POST" }),
  uploadMusic: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/tools/upload-music`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // ── Editor ────────────────────────────────────────────────────────
  editorVideoInfo: (videoPath: string) =>
    request<EditorVideoInfo>(
      `/api/tools/editor/video-info?video_path=${encodeURIComponent(videoPath)}`
    ),
  editorFrameUrl: (videoPath: string, timeSec: number) =>
    `${API_BASE}/api/tools/editor/frame?video_path=${encodeURIComponent(videoPath)}&time_sec=${timeSec}`,
  editorRender: (req: EditorRenderRequest) =>
    request<{ status: string; video: string }>("/api/tools/editor/render", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  editorSave: (composition: EditorComposition) =>
    request<{ status: string; file: string }>("/api/tools/editor/save", {
      method: "POST",
      body: JSON.stringify(composition),
    }),
  editorLoad: (videoPath: string) =>
    request<{ exists: boolean; composition: EditorComposition | null }>(
      `/api/tools/editor/load?video_path=${encodeURIComponent(videoPath)}`
    ),
};

// ─── Config ───────────────────────────────────────────────────────

export const config = {
  get: () => request<Record<string, unknown>>("/api/config"),
  update: (data: Record<string, unknown>) =>
    request("/api/config", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

// ─── Health ───────────────────────────────────────────────────────

export const health = () =>
  request<{ status: string; ffmpeg: boolean; gpu: boolean; project_root: string }>("/api/health");
