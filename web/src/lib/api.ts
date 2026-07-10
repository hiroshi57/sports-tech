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

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
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

export interface AthleteScores {
  id: string;
  name: string;
  position: string | null;
  sport: string;
  location: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  latest: ScoreSnapshot | null;
  history: ScoreSnapshot[];
  benchmark: MetricBenchmark | null;
  percentile: number | null;
  consistency: number | null;
  bmi: number | null;
  is_reference_score: boolean;
}

export function getAthleteScores(id: string): Promise<AthleteScores> {
  if (DEMO) return delay(demoScores(id));
  return request<AthleteScores>("GET", `/api/scouts/athletes/${id}/scores`);
}
