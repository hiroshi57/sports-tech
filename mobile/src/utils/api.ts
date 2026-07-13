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
  method: "GET" | "POST" | "PATCH" | "DELETE",
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
  error_margin: number;
  reliability_level: "high" | "moderate" | "low";
  reliability_note: string;
  score_breakdown: ScoreFactor[];
  feedback: string | null;
  analyzed_at: string;
  is_reference_score: boolean;
}

export interface ScoreFactor {
  key: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
  contribution_pct: number;
}

export function fetchAnalysis(videoId: string): Promise<AnalysisResultResponse> {
  return request<AnalysisResultResponse>("GET", `/api/videos/${videoId}/analysis`);
}

// ── 活動記録（練習ログ）────────────────────────────────────────────

export type ActivityType = "practice" | "match" | "rest";

export interface ActivityLog {
  id: string;
  athlete_id: string;
  activity_date: string;
  activity_type: ActivityType;
  duration_min: number;
  fatigue_level: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivitySummary {
  total_count: number;
  total_duration_min: number;
  avg_fatigue_level: number | null;
  practice_count: number;
  match_count: number;
  rest_count: number;
}

export interface ActivityCreateInput {
  activity_date: string;
  activity_type: ActivityType;
  duration_min: number;
  fatigue_level: number;
  notes?: string;
}

export function listActivities(): Promise<ActivityLog[]> {
  return request<ActivityLog[]>("GET", "/api/activities");
}

export function createActivity(input: ActivityCreateInput): Promise<ActivityLog> {
  return request<ActivityLog>("POST", "/api/activities", input);
}

export function deleteActivity(activityId: string): Promise<void> {
  return request<void>("DELETE", `/api/activities/${activityId}`);
}

export function fetchActivitySummary(): Promise<ActivitySummary> {
  return request<ActivitySummary>("GET", "/api/activities/summary");
}

// ── 通知 ────────────────────────────────────────────────────────────

export type NotificationType =
  "analysis_completed" | "analysis_failed" | "scout_viewed" | "injury_risk_alert";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string | null;
  resource_id: string | null;
  is_read: boolean;
  created_at: string;
}

export function listNotifications(): Promise<Notification[]> {
  return request<Notification[]>("GET", "/api/notifications");
}

export function fetchUnreadCount(): Promise<{ unread_count: number }> {
  return request<{ unread_count: number }>("GET", "/api/notifications/unread-count");
}

export function markNotificationRead(id: string): Promise<Notification> {
  return request<Notification>("POST", `/api/notifications/${id}/read`);
}

export function markAllNotificationsRead(): Promise<{ unread_count: number }> {
  return request<{ unread_count: number }>("POST", "/api/notifications/read-all");
}

// ── セルフケア（怪我リスク）────────────────────────────────────────

export interface InjuryRisk {
  risk_score: number;
  risk_level: "low" | "moderate" | "high";
  factors: string[];
  acwr: number | null;
  is_reference_score: boolean;
}

export function fetchInjuryRisk(): Promise<InjuryRisk> {
  return request<InjuryRisk>("GET", "/api/selfcare/injury-risk");
}

// ── 練習メニュー ────────────────────────────────────────────────────

export interface Exercise {
  name: string;
  duration_min: number;
  description?: string | null;
  target_skill?: string | null;
}

export interface TrainingMenu {
  id: string;
  athlete_id: string;
  title: string;
  description: string | null;
  is_ai_generated: boolean;
  total_duration_min: number;
  difficulty: string;
  exercises: Exercise[];
  created_at: string;
}

export function listTrainingMenus(): Promise<TrainingMenu[]> {
  return request<TrainingMenu[]>("GET", "/api/training");
}

export function generateTrainingMenu(targetDurationMin = 60): Promise<TrainingMenu> {
  return request<TrainingMenu>("POST", "/api/training/generate", {
    target_duration_min: targetDurationMin,
  });
}

export function deleteTrainingMenu(menuId: string): Promise<void> {
  return request<void>("DELETE", `/api/training/${menuId}`);
}
