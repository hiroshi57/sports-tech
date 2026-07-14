/**
 * バックエンド API クライアント（スカウトダッシュボード用）。
 *
 * JWT は localStorage に保持する（Phase 2 で httpOnly Cookie / Supabase に移行）。
 */

import { demoScores, demoSearch } from "./demo";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "sportstech_scout_token";

/** デモモード（バックエンド無しで動作） */
export const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(TOKEN_KEY);
  }
}

async function request<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, {
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
      // ignore non-JSON
    }
    throw new ApiError(res.status, detail);
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
  if (DEMO) return delay({ access_token: "demo-token", token_type: "bearer" });
  return request<TokenResponse>("POST", "/api/auth/login", { email });
}

export function fetchMe(): Promise<MeResponse> {
  if (DEMO) {
    return delay({ id: "demo", email: "demo-scout@example.com", role: "scout", is_active: true });
  }
  return request<MeResponse>("GET", "/api/auth/me");
}

// ── スカウト選手検索 ────────────────────────────────────────────────

export interface AthleteSearchItem {
  id: string;
  name: string;
  position: string | null;
  sport: string;
  location: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  latest_total_score: number | null;
  is_reference_score: boolean;
}

export interface SearchFilters {
  position?: string;
  sport?: string;
  location?: string;
  min_total_score?: number;
}

export function searchAthletes(filters: SearchFilters): Promise<AthleteSearchItem[]> {
  if (DEMO) {
    let items = demoSearch();
    if (filters.position) items = items.filter((a) => a.position === filters.position);
    if (filters.location)
      items = items.filter((a) => (a.location ?? "").includes(filters.location!));
    if (filters.min_total_score != null) {
      items = items.filter((a) => (a.latest_total_score ?? -1) >= filters.min_total_score!);
    }
    return delay(items);
  }
  const params = new URLSearchParams();
  if (filters.position) params.set("position", filters.position);
  if (filters.sport) params.set("sport", filters.sport);
  if (filters.location) params.set("location", filters.location);
  if (filters.min_total_score != null) {
    params.set("min_total_score", String(filters.min_total_score));
  }
  params.set("limit", "100");
  const qs = params.toString();
  return request<AthleteSearchItem[]>("GET", `/api/scouts/athletes?${qs}`);
}

export function getAthlete(id: string): Promise<AthleteSearchItem> {
  return request<AthleteSearchItem>("GET", `/api/scouts/athletes/${id}`);
}

export interface ScoreSnapshot {
  sprint_score: number;
  ball_control_score: number;
  positioning_score: number;
  body_usage_score: number;
  total_score: number;
  analyzed_at: string;
}

export interface MetricBenchmark {
  sprint_score: number;
  ball_control_score: number;
  positioning_score: number;
  body_usage_score: number;
  total_score: number;
  sample_size: number;
}

/** 詳細能力（多面評価） */
export interface Ability {
  category: "技術" | "フィジカル" | "メンタル" | "健康";
  name: string;
  value: number; // 0-100
  avg?: number; // 同ポジション平均（比較可能な項目のみ）
  note?: string;
}

/** 身体データの時系列 1 点 */
export interface PhysicalPoint {
  date: string; // YYYY-MM
  height_cm: number;
  weight_kg: number;
  body_fat_pct: number;
}

/** 栄養・食事データ */
export interface Nutrition {
  avg_calories: number;
  protein_g: number;
  adequacy: number; // 食事の充足度 0-100
  note: string;
}

/** 将来予測 */
export interface Prediction {
  horizon: string; // 例: "12ヶ月後"
  projected_total: number;
  projected_height_cm: number;
  projected_weight_kg: number;
  potential: number; // 伸びしろ 0-100
  comment: string;
}

/** 健康・可用性 */
export interface Health {
  injury_risk: number; // 0-100（高いほど危険）
  availability_pct: number; // 稼働可能率
  note: string;
}

/** 海外適性 */
export interface OverseasReadiness {
  score: number; // 0-100
  factors: string[];
}

export interface AthleteScores {
  id: string;
  name: string;
  position: string | null;
  sport: string;
  location: string | null;
  age?: number | null;
  height_cm: number | null;
  weight_kg: number | null;
  latest: ScoreSnapshot | null;
  history: ScoreSnapshot[];
  benchmark: MetricBenchmark | null;
  percentile: number | null;
  consistency: number | null;
  bmi: number | null;
  // ── 拡張アナリティクス（demo/将来のbackend） ──
  abilities?: Ability[];
  physical_history?: PhysicalPoint[];
  nutrition?: Nutrition | null;
  prediction?: Prediction | null;
  health?: Health | null;
  overseas?: OverseasReadiness | null;
  is_reference_score: boolean;
}

export function getAthleteScores(id: string): Promise<AthleteScores> {
  if (DEMO) return delay(demoScores(id));
  return request<AthleteScores>("GET", `/api/scouts/athletes/${id}/scores`);
}

// ── ウォッチリスト(C#22) ────────────────────────────────────────────

export interface WatchlistItem {
  id: string;
  athlete_id: string;
  name: string;
  position: string | null;
  sport: string;
  location: string | null;
  latest_total_score: number | null;
  note: string | null;
  tags: string | null;
  created_at: string;
  is_reference_score: boolean;
}

const DEMO_WATCH_KEY = "sportstech_demo_watchlist";

function demoReadWatch(): WatchlistItem[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(DEMO_WATCH_KEY) ?? "[]") as WatchlistItem[];
  } catch {
    return [];
  }
}

function demoWriteWatch(items: WatchlistItem[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(DEMO_WATCH_KEY, JSON.stringify(items));
}

export function listWatchlist(): Promise<WatchlistItem[]> {
  if (DEMO) return delay(demoReadWatch());
  return request<WatchlistItem[]>("GET", "/api/scouts/watchlist");
}

export async function addWatchlist(
  athleteId: string,
  note?: string,
  tags?: string
): Promise<WatchlistItem> {
  if (DEMO) {
    const items = demoReadWatch();
    const found = await getAthlete(athleteId);
    const existing = items.find((i) => i.athlete_id === athleteId);
    if (existing) {
      if (note !== undefined) existing.note = note;
      if (tags !== undefined) existing.tags = tags;
      demoWriteWatch(items);
      return delay(existing);
    }
    const item: WatchlistItem = {
      id: `w-${athleteId}`,
      athlete_id: athleteId,
      name: found.name,
      position: found.position,
      sport: found.sport,
      location: found.location,
      latest_total_score: found.latest_total_score,
      note: note ?? null,
      tags: tags ?? null,
      created_at: new Date().toISOString(),
      is_reference_score: true,
    };
    demoWriteWatch([item, ...items]);
    return delay(item);
  }
  return request<WatchlistItem>("POST", "/api/scouts/watchlist", {
    athlete_id: athleteId,
    note,
    tags,
  });
}

export function removeWatchlist(itemId: string): Promise<void> {
  if (DEMO) {
    demoWriteWatch(demoReadWatch().filter((i) => i.id !== itemId));
    return delay(undefined);
  }
  return request<void>("DELETE", `/api/scouts/watchlist/${itemId}`);
}
