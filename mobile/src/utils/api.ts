/**
 * バックエンド API クライアント。
 *
 * - JWT トークンはメモリ保持（Phase 2 で expo-secure-store に移行予定）
 * - エラーは ApiClientError として throw する
 */

const DEFAULT_BASE_URL = "http://localhost:8000";

let _baseUrl = process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_BASE_URL;
let _token: string | null = null;

export function setBaseUrl(url: string): void {
  _baseUrl = url;
}

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string
  ) {
    super(detail);
    this.name = "ApiClientError";
  }
}

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_token) {
    headers.Authorization = `Bearer ${_token}`;
  }

  const res = await fetch(`${_baseUrl}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      if (typeof json?.detail === "string") detail = json.detail;
    } catch {
      // JSON でないレスポンスはそのまま
    }
    throw new ApiClientError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ── 認証 ────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  id: string;
  email: string;
  role: "athlete" | "scout" | "coach";
  is_active: boolean;
}

export function login(email: string): Promise<TokenResponse> {
  return request<TokenResponse>("POST", "/api/auth/login", { email });
}

export function fetchMe(): Promise<MeResponse> {
  return request<MeResponse>("GET", "/api/auth/me");
}

// ── 動画 ────────────────────────────────────────────────────────────

export interface VideoResponse {
  id: string;
  athlete_id: string;
  s3_key: string;
  status: "pending" | "processing" | "completed" | "failed";
  duration_sec?: number | null;
  created_at?: string;
}

export interface VideoUploadResponse {
  video_id: string;
  presigned_url: string;
  s3_key: string;
}

export function listVideos(): Promise<VideoResponse[]> {
  return request<VideoResponse[]>("GET", "/api/videos");
}

export function initiateUpload(
  filename: string,
  contentType: string,
  fileSizeBytes?: number
): Promise<VideoUploadResponse> {
  return request<VideoUploadResponse>("POST", "/api/videos/upload-url", {
    filename,
    content_type: contentType,
    file_size_bytes: fileSizeBytes,
  });
}

export function completeUpload(videoId: string, durationSec?: number): Promise<VideoResponse> {
  return request<VideoResponse>("POST", `/api/videos/${videoId}/complete`, {
    duration_sec: durationSec,
  });
}

// ── 分析結果 ────────────────────────────────────────────────────────

export interface AnalysisResultResponse {
  id: string;
  video_id: string;
  sprint_score: number;
  ball_control_score: number;
  positioning_score: number;
  body_usage_score: number;
  total_score: number;
  confidence: number;
  feedback: string | null;
  analyzed_at: string;
  is_reference_score: boolean;
}

export function fetchAnalysis(videoId: string): Promise<AnalysisResultResponse> {
  return request<AnalysisResultResponse>("GET", `/api/videos/${videoId}/analysis`);
}
