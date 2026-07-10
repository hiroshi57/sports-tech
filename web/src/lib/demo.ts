/**
 * デモモード用の組み込みデータ。
 *
 * NEXT_PUBLIC_DEMO === "1" のとき、API クライアントはバックエンドに接続せず
 * このデータを返す。公開バックエンドなしで Vercel 上のダッシュボードを
 * 体験してもらうための仕組み（スコアは架空の参考値）。
 */

import type { AthleteScores, AthleteSearchItem, ScoreSnapshot } from "./api";

interface DemoAthlete {
  id: string;
  name: string;
  position: string;
  location: string;
  height_cm: number;
  weight_kg: number;
  base: [number, number, number, number]; // sprint, ball, positioning, body
}

const ATHLETES: DemoAthlete[] = [
  {
    id: "d1",
    name: "三笘 次郎",
    position: "MF",
    location: "神奈川",
    height_cm: 170,
    weight_kg: 65,
    base: [90, 85, 80, 77],
  },
  {
    id: "d2",
    name: "南野 五郎",
    position: "FW",
    location: "大阪",
    height_cm: 174,
    weight_kg: 68,
    base: [88, 80, 76, 74],
  },
  {
    id: "d3",
    name: "久保 太郎",
    position: "FW",
    location: "東京",
    height_cm: 178,
    weight_kg: 70,
    base: [82, 74, 88, 79],
  },
  {
    id: "d4",
    name: "冨安 三郎",
    position: "DF",
    location: "大阪",
    height_cm: 188,
    weight_kg: 82,
    base: [70, 60, 85, 90],
  },
  {
    id: "d5",
    name: "遠藤 四郎",
    position: "MF",
    location: "福岡",
    height_cm: 178,
    weight_kg: 72,
    base: [65, 78, 72, 68],
  },
];

function total(b: [number, number, number, number]): number {
  return Math.round((b[0] * 0.3 + b[1] * 0.3 + b[2] * 0.2 + b[3] * 0.2) * 10) / 10;
}

export function demoSearch(): AthleteSearchItem[] {
  return ATHLETES.map((a) => ({
    id: a.id,
    name: a.name,
    position: a.position,
    sport: "football",
    location: a.location,
    height_cm: a.height_cm,
    weight_kg: a.weight_kg,
    latest_total_score: total(a.base),
    is_reference_score: true,
  })).sort((x, y) => (y.latest_total_score ?? 0) - (x.latest_total_score ?? 0));
}

export function demoScores(id: string): AthleteScores {
  const a = ATHLETES.find((x) => x.id === id) ?? ATHLETES[0];
  // 3 回分の履歴（0.9 → 0.95 → 1.0 で成長）
  const history: ScoreSnapshot[] = [0.9, 0.95, 1.0].map((f, i) => {
    const b = a.base.map((s) => Math.round(s * f * 10) / 10) as [number, number, number, number];
    return {
      sprint_score: b[0],
      ball_control_score: b[1],
      positioning_score: b[2],
      body_usage_score: b[3],
      total_score: total(b),
      analyzed_at: `2026-0${i + 4}-01T00:00:00Z`,
    };
  });
  return {
    id: a.id,
    name: a.name,
    position: a.position,
    sport: "football",
    location: a.location,
    height_cm: a.height_cm,
    weight_kg: a.weight_kg,
    latest: history[history.length - 1],
    history,
    is_reference_score: true,
  };
}
