// 動画制限
export const VIDEO_MAX_DURATION_SEC = 180; // 3分
export const VIDEO_ALLOWED_MIME_TYPES = ["video/mp4", "video/quicktime"] as const;
export const VIDEO_MAX_SIZE_BYTES = 500 * 1024 * 1024; // 500MB

// スコア範囲
export const SCORE_MIN = 0;
export const SCORE_MAX = 100;

// スコア閾値（参考スコアとして表示）
export const SCORE_TIERS = {
  ELITE: 90,
  ADVANCED: 75,
  INTERMEDIATE: 55,
  BEGINNER: 0,
} as const;

// 分析結果通知の最大待ち時間
export const ANALYSIS_TIMEOUT_MIN = 10;

// ページネーション
export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

// 未成年者の年齢閾値
export const MINOR_AGE_THRESHOLD = 18;

// 比較可能な最大選手数
export const MAX_COMPARISON_ATHLETES = 4;
