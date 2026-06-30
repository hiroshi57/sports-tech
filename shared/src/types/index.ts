// ユーザーロール
export type UserRole = "athlete" | "scout" | "coach";

// 選手プロフィール
export interface AthleteProfile {
  id: string;
  userId: string;
  name: string;
  position: string;
  height?: number; // cm
  weight?: number; // kg
  location?: string;
  isPublic: boolean;
  createdAt: string;
  updatedAt: string;
}

// 動画ステータス
export type VideoStatus = "pending" | "processing" | "completed" | "failed";

// 動画情報
export interface Video {
  id: string;
  athleteId: string;
  s3Key: string;
  status: VideoStatus;
  durationSec?: number;
  uploadedAt: string;
}

// AI分析スコア (各項目 0-100)
export interface AnalysisScore {
  sprintScore: number;
  ballControlScore: number;
  positioningScore: number;
  bodyUsageScore: number;
  totalScore: number;
}

// 分析結果
export interface AnalysisResult {
  id: string;
  videoId: string;
  scores: AnalysisScore;
  feedback: string;
  analyzedAt: string;
}

// 活動記録
export interface ActivityLog {
  id: string;
  athleteId: string;
  date: string; // ISO 8601
  type: "practice" | "match" | "rest";
  durationMin: number;
  fatigueLevel: 1 | 2 | 3 | 4 | 5;
  notes?: string;
}

// API 共通レスポンス
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  error: string;
  detail?: string;
  statusCode: number;
}

// ページネーション
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}
